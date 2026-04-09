"""
/api/demo — нэвтрэлтгүй туршилтын endpoint.

Зөвхөн Seed Insight буцаана.
Хязгаар: өдөрт DEMO_DAILY_LIMIT удаа (IP-р).
DB-д юу ч хадгалдаггүй.

Лимитийг .env-д DEMO_DAILY_LIMIT=5 гэж тохируулна.
"""

import time
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from app.core.settings import get_settings
from app.services.llm_service import get_llm_service
from app.schemas.analysis import SeedInsightData
from app.db.redis_client import get_redis_connection

router = APIRouter(prefix="/demo", tags=["Demo"])

_WINDOW = 60 * 60 * 24  # 24 цаг (секундээр)


class DemoRequest(BaseModel):
    surface_text: str = Field(..., min_length=1, max_length=1000)
    inner_reaction_text: str = Field(..., min_length=1, max_length=1000)
    meaning_text: str = Field(..., min_length=1, max_length=1000)


class DemoResponse(BaseModel):
    seed_insight: SeedInsightData
    remaining: int
    note: str = "Demo хувилбар — өгөгдөл хадгалагдахгүй"


@router.post("/seed-insight", response_model=DemoResponse)
async def demo_seed_insight(data: DemoRequest, request: Request):
    """
    Нэвтрэлтгүйгээр Seed Insight туршиж үзнэ.
    Лимит: .env-д DEMO_DAILY_LIMIT (default: 5).
    """
    limit = get_settings().demo_daily_limit

    used = _increment_and_check(request.client.host, limit)
    used = 0


    llm = get_llm_service()
    seed = await llm.generate_seed_insight(
        surface=data.surface_text,
        inner=data.inner_reaction_text,
        meaning=data.meaning_text,
    )

    return DemoResponse(
        seed_insight=seed,
        remaining=max(0, limit - used),
    )


@router.get("/remaining", summary="Үлдсэн demo тоо")
async def get_remaining_count(request: Request):
    """Тухайн IP-ийн өдрийн үлдсэн demo тоог буцаана."""
    limit = get_settings().demo_daily_limit
    used = _get_used_count(request.client.host)
    return {
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
    }


# ── Private ───────────────────────────────────────────────────────────────────

def _make_key(ip: str) -> str:
    day = int(time.time()) // _WINDOW
    return f"demo:{ip}:{day}"


def _get_used_count(ip: str) -> int:
    val = get_redis_connection().get(_make_key(ip))
    return int(val) if val else 0


def _increment_and_check(ip: str, limit: int) -> int:
    """
    Тоолуурыг нэмэгдүүлнэ.
    Хэтэрсэн бол 429 буцаана, үгүй бол шинэ тоог буцаана.
    """
    redis = get_redis_connection()
    key = _make_key(ip)

    count = redis.incr(key)
    if count == 1:
        redis.expire(key, _WINDOW)

    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Өдөрт {limit} удаа турших боломжтой."
                " Маргааш дахин оролдоно уу."
            ),
            headers={"Retry-After": str(_WINDOW)},
        )

    return count
