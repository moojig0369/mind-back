"""
WebSocket endpoint.
Redis Pub/Sub-аас мэдэгдэл хүлээн аваад frontend руу дамжуулна.

Channels:
  entry:{entry_id}              — Seed Insight боловсруулалтын явц
  user:{user_id}:notifications  — Deep Insight бэлэн болсон мэдэгдэл
"""

import asyncio
import json
import logging
import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.settings import get_settings

_log = logging.getLogger(__name__)
_settings = get_settings()
_TIMEOUT_SECONDS = 180
_DONE_TYPES = {"done", "error", "crisis"}

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/{channel}")
async def handle_websocket(websocket: WebSocket, channel: str):
    await websocket.accept()
    _log.info(f"WS холбогдлоо: {channel}")

    redis = aioredis.from_url(_settings.redis_url)
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)

    try:
        await _listen(websocket, pubsub)
    except WebSocketDisconnect:
        _log.info(f"WS салгагдлаа: {channel}")
    except Exception as exc:
        _log.error(f"WS алдаа: {exc}")
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await redis.aclose()


async def _listen(websocket: WebSocket, pubsub) -> None:
    """Мэдэгдэл ирэх эсвэл timeout болтол сонсно."""
    elapsed = 0.0
    while elapsed < _TIMEOUT_SECONDS:
        message = await pubsub.get_message(
            ignore_subscribe_messages=True, timeout=1.0
        )
        if message and message["type"] == "message":
            text = _decode(message["data"])
            await websocket.send_text(text)
            if _is_terminal(text):
                return

        await asyncio.sleep(0.1)
        elapsed += 0.1

    await websocket.send_text(
        json.dumps({"type": "timeout", "message": "Холболтын хугацаа дууслаа"})
    )


def _decode(data) -> str:
    return data.decode("utf-8") if isinstance(data, bytes) else data


def _is_terminal(text: str) -> bool:
    try:
        return json.loads(text).get("type") in _DONE_TYPES
    except Exception:
        return False
