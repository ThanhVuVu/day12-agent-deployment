"""
BASIC — Health Check + Graceful Shutdown

Hai tính năng tối thiểu cần có trước khi deploy:
  1. GET /health  — liveness: "agent có còn sống không?"
  2. GET /ready   — readiness: "agent có sẵn sàng nhận request chưa?"
  3. Graceful shutdown: hoàn thành request hiện tại trước khi tắt

Chạy:
    python app.py

Test health check:
    curl http://localhost:8000/health
    curl http://localhost:8000/ready

Simulate shutdown:
    # Trong terminal khác
    kill -SIGTERM <pid>
    # Xem agent log graceful shutdown message
"""
import os
import time
import asyncio
import redis
import signal
import logging
from contextlib import asynccontextmanager


from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from utils.mock_llm import ask

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_in_flight_requests = 0  # đếm số request đang xử lý
r = redis.Redis()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready

    # ── Startup ──
    logger.info("Agent starting up...")
    logger.info("Loading model and checking dependencies...")
    await asyncio.sleep(0.2)  # simulate startup time
    _is_ready = True
    logger.info("✅ Agent is ready!")

    yield

    # ── Shutdown ──
    _is_ready = False
    logger.info("🔄 Graceful shutdown initiated...")

    # Chờ request đang xử lý hoàn thành (tối đa 30 giây)
    timeout = 30
    elapsed = 0
    while _in_flight_requests > 0 and elapsed < timeout:
        logger.info(f"Waiting for {_in_flight_requests} in-flight requests...")
        await asyncio.sleep(1)
        elapsed += 1

    logger.info("✅ Shutdown complete")


app = FastAPI(title="Agent — Health Check Demo", lifespan=lifespan)


@app.middleware("http")
async def track_requests(request, call_next):
    """Theo dõi số request đang xử lý."""
    global _in_flight_requests
    _in_flight_requests += 1
    try:
        response = await call_next(request)
        return response
    finally:
        _in_flight_requests -= 1


# ──────────────────────────────────────────────────────────
# Business Logic
# ──────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "AI Agent with health checks!"}


@app.post("/ask")
async def ask_agent(question: str):
    if not _is_ready:
        raise HTTPException(503, "Agent not ready")
    return {"answer": ask(question)}


# ──────────────────────────────────────────────────────────
# HEALTH CHECKS — Phần quan trọng nhất của file này
# ──────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready():
    try:
        if not _is_ready:
            raise RuntimeError("startup not complete")

        # Check Redis (nếu Redis chưa chạy → trả 503 để platform chưa route traffic)
        r.ping()
        return {"status": "ready"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "not ready", "reason": str(e)})


# ──────────────────────────────────────────────────────────
# GRACEFUL SHUTDOWN
# ──────────────────────────────────────────────────────────

def handle_sigterm(signum, frame):
    """
    SIGTERM là signal platform gửi khi muốn dừng container.
    Khác với SIGKILL (không thể catch được).

    uvicorn bắt SIGTERM tự động và gọi lifespan shutdown.
    Hàm này để log thêm thông tin.
    """
    logger.info(f"Received signal {signum} — uvicorn will handle graceful shutdown")


signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigterm)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting agent on port {port}")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        # ✅ Cho phép graceful shutdown
        timeout_graceful_shutdown=30,
    )
