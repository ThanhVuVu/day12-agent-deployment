"""
Production AI Agent — Day 12 Part 6 (Final Project)

Đề tài: AI agent giúp học sinh học lịch sử (History Tutor).

Checklist:
  ✅ Config từ environment (12-factor)
  ✅ Structured JSON logging
  ✅ API Key authentication
  ✅ Rate limiting (Redis sliding window)
  ✅ Cost guard ($/month per user in Redis)
  ✅ Conversation history in Redis (stateless)
  ✅ Input validation (Pydantic)
  ✅ Health check + Readiness probe
  ✅ Graceful shutdown
  ✅ Security headers
  ✅ CORS
"""
import os
import time
import signal
import logging
import json
import asyncio
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Security, Depends, Request, Response
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from app.config import settings

# Mock LLM — history tutor
from utils.mock_llm import ask as llm_ask

# Redis
import redis

# ─────────────────────────────────────────────────────────
# Logging — JSON structured
# ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0
_error_count = 0
INSTANCE_ID = os.getenv("INSTANCE_ID", f"agent-{uuid.uuid4().hex[:6]}")

# ─────────────────────────────────────────────────────────
# Redis clients
# ─────────────────────────────────────────────────────────
_redis = redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None

def _redis_required():
    if not _redis:
        raise HTTPException(503, "Redis not configured. Set REDIS_URL.")


def check_rate_limit(user_id: str):
    """
    Sliding window per user.
    Store request timestamps in a sorted set for last 60 seconds.
    """
    _redis_required()

    now_ms = int(time.time() * 1000)
    key = f"rl:{user_id}"
    window_ms = 60_000
    cutoff = now_ms - window_ms

    pipe = _redis.pipeline()
    pipe.zremrangebyscore(key, 0, cutoff)
    pipe.zadd(key, {str(now_ms): now_ms})
    pipe.zcard(key)
    pipe.pexpire(key, window_ms + 5_000)
    _, _, count, _ = pipe.execute()

    if int(count) > settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
            headers={"Retry-After": "60"},
        )

# ─────────────────────────────────────────────────────────
# Cost guard — monthly budget per user (Redis)
# ─────────────────────────────────────────────────────────
PRICE_PER_1K_INPUT_TOKENS = 0.00015
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006


def _estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1000) * PRICE_PER_1K_INPUT_TOKENS + (output_tokens / 1000) * PRICE_PER_1K_OUTPUT_TOKENS


def check_and_record_monthly_budget(user_id: str, estimated_cost_usd: float):
    _redis_required()

    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"

    raw_current = _redis.get(key)
    current = float(raw_current) if raw_current else 0.0
    limit = settings.monthly_budget_usd

    if current + estimated_cost_usd > limit:
        raise HTTPException(status_code=402, detail="Budget exceeded")

    _redis.incrbyfloat(key, float(estimated_cost_usd))
    _redis.expire(key, 32 * 24 * 3600)


def get_budget(user_id: str) -> dict:
    _redis_required()
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    raw_current = _redis.get(key)
    used = float(raw_current) if raw_current else 0.0
    return {"month": month_key, "used_usd": round(used, 6), "limit_usd": settings.monthly_budget_usd}


def _history_key(user_id: str) -> str:
    return f"hist:{user_id}"


def append_history(user_id: str, role: str, content: str, max_items: int = 30):
    _redis_required()
    item = json.dumps(
        {"role": role, "content": content, "ts": datetime.now(timezone.utc).isoformat()},
        ensure_ascii=False,
    )
    key = _history_key(user_id)
    pipe = _redis.pipeline()
    pipe.rpush(key, item)
    pipe.ltrim(key, -max_items, -1)
    pipe.expire(key, 7 * 24 * 3600)
    pipe.execute()


def load_history(user_id: str) -> list[dict]:
    _redis_required()
    key = _history_key(user_id)
    items = _redis.lrange(key, 0, -1) or []
    out: list[dict] = []
    for it in items:
        try:
            out.append(json.loads(it))
        except Exception:
            continue
    return out

# ─────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if not api_key or api_key != settings.agent_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Include header: X-API-Key: <key>",
        )
    # Use API key as user_id for simplicity (stateless). In real product, map to user.
    return api_key

# ─────────────────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "instance_id": INSTANCE_ID,
    }))
    # Validate redis connectivity early for readiness
    if _redis:
        try:
            _redis.ping()
        except Exception as e:
            logger.error(json.dumps({"event": "redis_unavailable", "error": str(e)}))
    await asyncio.sleep(0.05)
    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))

    yield

    _is_ready = False
    logger.info(json.dumps({"event": "shutdown"}))

# ─────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count
    start = time.time()
    _request_count += 1
    try:
        response: Response = await call_next(request)
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if "server" in response.headers:
            del response.headers["server"]
        duration = round((time.time() - start) * 1000, 1)
        logger.info(json.dumps({
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": duration,
        }))
        return response
    except Exception as e:
        _error_count += 1
        raise

# ─────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000,
                          description="Your question for the agent")
    # Optional: keep separate user_id if you want to group students. For this lab, API key is user_id.
    student_id: str | None = Field(default=None, max_length=64)

class AskResponse(BaseModel):
    question: str
    answer: str
    model: str
    timestamp: str
    served_by: str
    history_count: int

# ─────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
        },
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    request: Request,
    _key: str = Depends(verify_api_key),
):
    """
    Send a question to the AI agent.

    **Authentication:** Include header `X-API-Key: <your-key>`
    """
    user_id = body.student_id or _key[:16]

    # Rate limit per user
    check_rate_limit(user_id)

    # Budget check (monthly)
    input_tokens = len(body.question.split()) * 2
    est_cost_in = _estimate_cost_usd(input_tokens, 0)
    check_and_record_monthly_budget(user_id, est_cost_in)

    logger.info(json.dumps({
        "event": "agent_call",
        "q_len": len(body.question),
        "client": str(request.client.host) if request.client else "unknown",
        "user_id": user_id,
    }))

    # Conversation history (stateless via Redis)
    append_history(user_id, "user", body.question)
    answer = llm_ask(body.question)
    append_history(user_id, "assistant", answer)

    output_tokens = len(answer.split()) * 2
    est_cost_out = _estimate_cost_usd(0, output_tokens)
    check_and_record_monthly_budget(user_id, est_cost_out)

    return AskResponse(
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        timestamp=datetime.now(timezone.utc).isoformat(),
        served_by=INSTANCE_ID,
        history_count=len(load_history(user_id)),
    )


@app.get("/health", tags=["Operations"])
def health():
    """Liveness probe. Platform restarts container if this fails."""
    status = "ok"
    redis_ok = None
    if _redis:
        try:
            _redis.ping()
            redis_ok = True
        except Exception:
            redis_ok = False
    checks = {
        "llm": "mock" if not settings.openai_api_key else "openai",
        "redis": redis_ok if _redis else "not_configured",
    }
    return {
        "status": status,
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "checks": checks,
        "instance_id": INSTANCE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    """Readiness probe. Load balancer stops routing here if not ready."""
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    if _redis:
        try:
            _redis.ping()
        except Exception:
            raise HTTPException(503, "Redis not ready")
    return {"ready": True}

@app.get("/me/budget", tags=["Operations"])
def my_budget(_key: str = Depends(verify_api_key)):
    user_id = _key[:16]
    return get_budget(user_id)


@app.get("/me/history", tags=["Operations"])
def my_history(_key: str = Depends(verify_api_key)):
    user_id = _key[:16]
    return {"user_id": user_id, "messages": load_history(user_id)}


@app.get("/metrics", tags=["Operations"])
def metrics(_key: str = Depends(verify_api_key)):
    """Basic metrics (protected)."""
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "instance_id": INSTANCE_ID,
    }


# ─────────────────────────────────────────────────────────
# Graceful Shutdown
# ─────────────────────────────────────────────────────────
def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))

signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    logger.info(f"API Key: {settings.agent_api_key[:4]}****")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
