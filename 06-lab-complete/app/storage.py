import json
from datetime import datetime, timezone

from fastapi import HTTPException
import redis

from app.config import settings


_redis = redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None


def redis_ping() -> None:
    if not _redis:
        raise HTTPException(503, "Redis not configured. Set REDIS_URL.")
    _redis.ping()


def _history_key(user_id: str) -> str:
    return f"hist:{user_id}"


def append_history(user_id: str, role: str, content: str, max_items: int = 30) -> None:
    if not _redis:
        raise HTTPException(503, "Redis not configured. Set REDIS_URL.")
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
    if not _redis:
        raise HTTPException(503, "Redis not configured. Set REDIS_URL.")
    key = _history_key(user_id)
    items = _redis.lrange(key, 0, -1) or []
    out: list[dict] = []
    for it in items:
        try:
            out.append(json.loads(it))
        except Exception:
            continue
    return out

