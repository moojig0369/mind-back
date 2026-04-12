"""
Rate limiting middleware.
Нэг хэрэглэгч минутанд хэдэн POST хүсэлт
илгээж болохыг Redis sliding window-р хянана.
"""

import time
from fastapi import Request, HTTPException, status
from app.db.redis_client import get_redis_connection
from app.core.settings import get_settings

_settings = get_settings()
_WINDOW_SECONDS = 60


async def apply_rate_limit(request: Request, call_next):
    if _should_skip(request):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return await call_next(request)

    key = _build_key(request.client.host, auth_header)
    count = _increment_request_count(key)

    if count > _settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Минутанд "
                f"{_settings.rate_limit_per_minute}-аас "
                f"дээш хүсэлт илгээх боломжгүй"
            ),
            headers={"Retry-After": str(_WINDOW_SECONDS)},
        )

    return await call_next(request)


def _should_skip(request: Request) -> bool:
    """WebSocket болон health endpoint-ийг хасна."""
    path = request.url.path
    is_write = request.method == "POST"
    is_entry = "/entries" in path
    return not (is_write and is_entry)


def _build_key(ip: str, auth: str) -> str:
    token_hash = hash(auth) % 1_000_000
    return f"rate:{ip}:{token_hash}"


def _increment_request_count(key: str) -> int:
    """Sliding window тоолуур. Тухайн цонхны хүсэлтийн тоог буцаана."""
    redis = get_redis_connection()
    now = int(time.time())
    cutoff = now - _WINDOW_SECONDS

    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, cutoff)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, _WINDOW_SECONDS)
    results = pipe.execute()

    return results[2]
