import time

from fastapi import HTTPException
import redis

from app.config import settings


_redis = redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None


def check_rate_limit(user_id: str) -> None:
    """
    Sliding window rate limit per user, backed by Redis.
    - Keep timestamps in a sorted set for last 60 seconds.
    - Enforce settings.rate_limit_per_minute (default 10).
    """
    if not _redis:
        raise HTTPException(503, "Redis not configured. Set REDIS_URL.")

    now_ms = int(time.time() * 1000)
    window_ms = 60_000
    cutoff = now_ms - window_ms
    key = f"rl:{user_id}"

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

