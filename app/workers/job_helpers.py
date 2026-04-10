"""
Worker helper функцүүд.
jobs.py-с тусгаарласан (SRP + мөрийн хязгаар).
"""

import asyncio
import json


def run_async(coro):
    """Sync контекстод async coroutine ажиллуулна."""
    try:
        # Try to get the current running loop (if we're already in async context)
        loop = asyncio.get_running_loop()
        # If we're in an async context, we can't use run_until_complete
        # This should not happen in RQ workers, but handle it gracefully
        raise RuntimeError("Cannot run async code in existing event loop")
    except RuntimeError:
        # No running loop exists, safe to create a new one
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def publish(
    redis,
    channel: str,
    msg_type: str,
    message: str | None = None,
    payload: dict | None = None,
) -> None:
    """Redis Pub/Sub-аар WS мэдэгдэл илгээнэ."""
    data: dict = {"type": msg_type}
    if message:
        data["message"] = message
    if payload:
        data["data"] = payload
    redis.publish(channel, json.dumps(data, ensure_ascii=False))

def _to_float(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def top_maslow_categories(maslow: list, limit: int = 2) -> list[str]:
    """Хамгийн өндөр confidence-тай N Maslow category буцаана."""
    scored = [
        (
            item.get("category", ""),
            sum(
                _to_float(v)
                for d in item.get("values", [])
                for v in d.values()
            ),
        )
        for item in maslow
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in scored[:limit]]
