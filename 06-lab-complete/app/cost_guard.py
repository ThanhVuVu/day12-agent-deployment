from datetime import datetime, timezone

from fastapi import HTTPException
import redis

from app.config import settings


_redis = redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None

PRICE_PER_1K_INPUT_TOKENS = 0.00015
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006


def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1000) * PRICE_PER_1K_INPUT_TOKENS + (output_tokens / 1000) * PRICE_PER_1K_OUTPUT_TOKENS


def check_and_record_monthly_budget(user_id: str, estimated_cost_usd: float) -> None:
    """
    Monthly budget ($10/month per user) backed by Redis.
    Raise 402 when exceeded.
    """
    if not _redis:
        raise HTTPException(503, "Redis not configured. Set REDIS_URL.")

    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    raw = _redis.get(key)
    used = float(raw) if raw else 0.0
    limit = float(settings.monthly_budget_usd)

    if used + float(estimated_cost_usd) > limit:
        raise HTTPException(status_code=402, detail="Budget exceeded")

    _redis.incrbyfloat(key, float(estimated_cost_usd))
    _redis.expire(key, 32 * 24 * 3600)


def get_budget(user_id: str) -> dict:
    if not _redis:
        raise HTTPException(503, "Redis not configured. Set REDIS_URL.")

    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    raw = _redis.get(key)
    used = float(raw) if raw else 0.0
    return {"month": month_key, "used_usd": round(used, 6), "limit_usd": settings.monthly_budget_usd}

