"""
/api/patterns — Pattern CRUD болон Human Insight endpoint-ууд.

Бүх endpoint нь auth шаардана.

GET  /patterns              — Хэрэглэгчийн сүүлийн detected_patterns
GET  /patterns/summary      — Хамгийн хүчтэй pattern-уудын нэгдсэн хэлбэр
PATCH /patterns/{id}/ack    — acknowledged = true тэмдэглэх

POST /patterns/human-insight         — LLM-ээр human insight үүсгэж хадгална
GET  /patterns/human-insight         — Хадгалсан human insight жагсаалт
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from supabase import Client

from app.db.supabase import get_admin_client
from app.services.auth_service import get_current_user
from app.services.llm_service import get_llm_service

_log = logging.getLogger(__name__)

router = APIRouter(prefix="/patterns", tags=["Patterns & Insight"])


def _db() -> Client:
    return get_admin_client()


# ── Response models ───────────────────────────────────────────────────────────

class PatternOut(BaseModel):
    id: str
    pattern_type: str
    pattern_data: dict
    strength_score: float
    detected_at: str
    acknowledged: bool
    run_id: str | None = None
    related_node_ids: list[str] = []


class PatternSummary(BaseModel):
    dominant_need: dict | None = None
    dominant_emotion: dict | None = None
    low_state: dict | None = None
    emotion_trend: dict | None = None
    unmet_needs: list[dict] = []
    strong_connections: list[dict] = []
    high_intensity_emotions: list[dict] = []
    emotion_variance: dict | None = None
    latest_run_at: str | None = None


class HumanInsightOut(BaseModel):
    id: str
    insight_text: str
    highlight_type: str | None
    strength_score: float
    generated_at: str
    acknowledged: bool
    pattern_run_id: str | None = None
    pattern_type: str | None = None   # 🔥 шинэ


class HumanInsightRequest(BaseModel):
    pattern_run_id: str | None = None  # заавал биш — сүүлийн run-г ашиглана


# ── Pattern endpoints ─────────────────────────────────────────────────────────

@router.get("/", response_model=list[PatternOut])
async def list_patterns(
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    user: dict = Depends(get_current_user),
    db: Client = Depends(_db),
):
    """
    Хэрэглэгчийн сүүлийн detected_patterns.
    unread_only=true → acknowledged=false зөвхөн.
    """
    q = (
        db.table("detected_patterns")
        .select(
            "id, pattern_type, pattern_data, strength_score, "
            "detected_at, acknowledged, run_id, related_node_ids"
        )
        .eq("user_id", user["id"])
        .order("detected_at", desc=True)
        .limit(limit)
    )
    if unread_only:
        q = q.eq("acknowledged", False)

    return q.execute().data or []


@router.get("/summary", response_model=PatternSummary)
async def get_pattern_summary(
    user: dict = Depends(get_current_user),
    db: Client = Depends(_db),
):
    """
    Хамгийн сүүлийн pattern_run-н pattern-уудыг нэгдсэн байдлаар буцаана.
    Frontend dashboard-д нэг call хангалттай.
    """
    # Сүүлийн амжилттай run олно
    run_rows = (
        db.table("pattern_runs")
        .select("id, run_finished_at")
        .eq("user_id", user["id"])
        .eq("status", "completed")
        .order("run_finished_at", desc=True)
        .limit(1)
        .execute()
    ).data or []

    if not run_rows:
        return PatternSummary()

    run = run_rows[0]
    run_id = run["id"]

    rows = (
        db.table("detected_patterns")
        .select("pattern_type, pattern_data, strength_score")
        .eq("user_id", user["id"])
        .eq("run_id", run_id)
        .execute()
    ).data or []

    # pattern_type → dict lookup
    by_type: dict[str, dict] = {}
    for r in rows:
        by_type[r["pattern_type"]] = r

    def _data(key: str) -> dict | None:
        row = by_type.get(key)
        if not row:
            return None
        return {**row["pattern_data"], "strength_score": row["strength_score"]}

    def _list_data(key: str) -> list[dict]:
        row = by_type.get(key)
        if not row:
            return []
        inner = row["pattern_data"]
        # pattern_data нь жагсаалт агуулсан dict байна
        for v in inner.values():
            if isinstance(v, list):
                return v
        return [inner]

    return PatternSummary(
        dominant_need          = _data("dominant_need"),
        dominant_emotion       = _data("dominant_emotion"),
        low_state              = _data("low_state"),
        emotion_trend          = _data("emotion_trend"),
        unmet_needs            = _list_data("unmet_need"),
        strong_connections     = _list_data("strong_need_connection"),
        high_intensity_emotions= _list_data("high_intensity_emotion"),
        emotion_variance       = _data("emotion_variance"),
        latest_run_at          = run.get("run_finished_at"),
    )


@router.patch("/{pattern_id}/ack", status_code=204)
async def acknowledge_pattern(
    pattern_id: str,
    user: dict = Depends(get_current_user),
    db: Client = Depends(_db),
):
    """Pattern-ийг уншсан гэж тэмдэглэнэ."""
    result = (
        db.table("detected_patterns")
        .update({"acknowledged": True})
        .eq("id", pattern_id)
        .eq("user_id", user["id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Pattern олдсонгүй")

@router.get("/human-insight", response_model=list[HumanInsightOut])
async def list_human_insights(
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(get_current_user),
    db: Client = Depends(_db),
):
    """Хэрэглэгчийн хадгалагдсан human insight — pattern_type тус бүрээр хамгийн сүүлийнх."""
    rows = (
        db.table("human_insights")
        .select(
            "id, insight_text, highlight_type, strength_score, "
            "generated_at, acknowledged, pattern_run_id, pattern_type"
        )
        .eq("user_id", user["id"])
        .order("generated_at", desc=True)
        .execute()
    ).data or []

    # pattern_type тус бүрээр хамгийн сүүлийнхийг үлдээнэ
    seen: dict = {}
    for row in rows:
        pt = row.get("pattern_type")
        if pt not in seen:
            seen[pt] = row

    return list(seen.values())[:limit]

@router.patch("/human-insight/{insight_id}/ack", status_code=204)
async def acknowledge_human_insight(
    insight_id: str,
    user: dict = Depends(get_current_user),
    db: Client = Depends(_db),
):
    """Human insight-ийг уншсан гэж тэмдэглэнэ."""
    result = (
        db.table("human_insights")
        .update({"acknowledged": True})
        .eq("id", insight_id)
        .eq("user_id", user["id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Insight олдсонгүй")