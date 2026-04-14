"""
Worker-д ашиглагдах туслах функцүүд.

  run_async()            — asyncio coroutine-г sync орчинд ажиллуулна
  publish()              — Redis pub/sub-аар WS мэдэгдэл илгээнэ
  top_maslow_categories()— Maslow шинжилгээнээс тэргүүлэх категориудыг авна
"""

import asyncio
import json
import logging
from typing import Any

_log = logging.getLogger(__name__)


def run_async(coro) -> Any:
    """
    RQ worker нь sync орчинд ажилладаг тул
    async функцийг шинэ event loop дотор ажиллуулна.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def publish(
    redis_conn,
    channel_key: str,
    event: str,
    message: str = "",
    payload: dict | None = None,
) -> None:
    """
    Redis pub/sub channel-д JSON мэдэгдэл илгээнэ.
    Channel: entry:<entry_id>  эсвэл  user:<user_id>:notifications
    """
    data = {"event": event, "message": message}
    if payload:
        data["payload"] = payload

    channel = f"entry:{channel_key}" if ":" not in channel_key else channel_key
    redis_conn.publish(channel, json.dumps(data, ensure_ascii=False))
    _log.debug(f"📡 publish → {channel}: {event}")


def top_maslow_categories(maslow, top_n: int = 3) -> list[str]:
    """
    LlmAnalysisResult.maslow-ээс score өндөртэй категориудын нэрийг буцаана.
    maslow нь dict эсвэл Pydantic model байж болно.
    """
    try:
        data = maslow if isinstance(maslow, dict) else maslow.model_dump()
        # score талбар байвал эрэмбэлнэ, байхгүй бол нэр л буцаана
        scored = [
            (k, v.get("score", 0) if isinstance(v, dict) else 0)
            for k, v in data.items()
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [k for k, _ in scored[:top_n]]
    except Exception:
        return []