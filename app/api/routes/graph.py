"""
/api/graph — үнэт зүйлсийн граф болон insight endpoint-ууд.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from supabase import Client
from app.services.auth_service import get_current_user
from app.services.journal_service import JournalService
from app.db.supabase import get_admin_client
from pydantic import BaseModel, Field

router = APIRouter(tags=["Граф ба Insight"])

# ── Response schema нэмэлт ────────────────────────────────────────────────────

class EmotionStatRow(BaseModel):
    emotion:    str
    score_sum:  float
    count:      int
    percentage: float


def _db() -> Client:
    return get_admin_client()


def _get_journal_service() -> JournalService:
    return JournalService(get_admin_client())


@router.get("/graph")
async def get_value_graph(
    user: dict = Depends(get_current_user),
    journal: JournalService = Depends(_get_journal_service),
):
    """React Flow-д зориулсан үнэт зүйлсийн граф."""
    graph = journal.fetch_value_graph(user["id"])
    if not graph["nodes"]:
        return {
            "nodes": [],
            "edges": [],
            "message": "Мэдээлэл одоогоор хангалтгүй байна",
        }
    return graph

@router.get("/stats/emotions", response_model=list[EmotionStatRow])
async def get_emotion_stats(
    entries: int = Query(10, ge=1, le=50, description="Сүүлийн хэдэн тэмдэглэл"),
    user: dict = Depends(get_current_user),
    db: Client = Depends(_db),
):
    """
    Плутчикийн сэтгэл хөдлөлийн хэв маяг — сүүлийн N тэмдэглэл.

    Хоногоор бус тэмдэглэлийн тоогоор хайрлана.
    Утга нь зүгээр count биш — primary_score-ийн нийлбэр
    (confidence-weighted) тул бага ч гэсэн хүчтэй emotion дийлнэ.

    Response:
        emotion      — Plutchik primary нэр
        score_sum    — weighted score нийлбэр
        count        — тохиолдсон тоо
        percentage   — нийт score-н эзлэх хувь (0–100)
    """
    # 1. Хэрэглэгчийн сүүлийн N entry_id авна
    entry_rows = (
        db.table("journal_entries")
        .select("id")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .limit(entries)
        .execute()
    ).data or []

    if not entry_rows:
        return []

    entry_ids = [r["id"] for r in entry_rows]

    # 2. Тэдгээр entry-н analysis авна
    rows = (
        db.table("journal_analyses")
        .select("plutchik_primary, plutchik_intensity")
        .in_("entry_id", entry_ids)
        .not_.is_("plutchik_primary", "null")
        .execute()
    ).data or []

    if not rows:
        return []

    # 3. Emotion-ээр нэгтгэнэ — score нийлбэр + count
    totals: dict[str, dict] = {}
    for r in rows:
        key = r["plutchik_primary"]
        score = float(r.get("plutchik_intensity") or 0.5)
        if key not in totals:
            totals[key] = {"score_sum": 0.0, "count": 0}
        totals[key]["score_sum"] += score
        totals[key]["count"]     += 1

    total_score = sum(v["score_sum"] for v in totals.values()) or 1.0

    # 4. Бүх 8 Plutchik emotion-г оруулна (0 утгатай байсан ч)
    ALL_EMOTIONS = [
        "joy", "trust", "fear", "surprise",
        "sadness", "disgust", "anger", "anticipation",
    ]

    result = []
    for emotion in ALL_EMOTIONS:
        data = totals.get(emotion, {"score_sum": 0.0, "count": 0})
        result.append({
            "emotion":    emotion,
            "score_sum":  round(data["score_sum"], 3),
            "count":      data["count"],
            "percentage": round(data["score_sum"] / total_score * 100, 1),
        })

    # Score-оор буурах дарааллаар
    return sorted(result, key=lambda x: x["score_sum"], reverse=True)

@router.get("/insights/deep")
async def list_deep_insights(
    user: dict = Depends(get_current_user),
    db: Client = Depends(_db),
):
    """Хэрэглэгчийн Deep Insight жагсаалт."""
    result = (
        db.table("deep_insights")
        .select("*")
        .eq("user_id", user["id"])
        .order("generated_at", desc=True)
        .limit(10)
        .execute()
    )
    return result.data


@router.get("/insights/seed/{entry_id}")
async def get_seed_insight(
    entry_id: str,
    user: dict = Depends(get_current_user),
    db: Client = Depends(_db),
):
    """Тэмдэглэлийн Seed Insight (mirror, reframe, relief, summary)."""
    entry = (
        db.table("journal_entries")
        .select("id")
        .eq("id", entry_id)
        .eq("user_id", user["id"])
        .execute()
    )
    if not entry.data:
        raise HTTPException(status_code=404, detail="Тэмдэглэл олдсонгүй")

    insight = (
        db.table("seed_insights")
        .select("*")
        .eq("entry_id", entry_id)
        .single()
        .execute()
    )
    if not insight.data:
        raise HTTPException(
            status_code=404, detail="Seed Insight бэлэн болоогүй байна"
        )
    return insight.data


@router.get("/today")
async def get_today_snapshot(
    user: dict = Depends(get_current_user),
    journal: JournalService = Depends(_get_journal_service),
    db: Client = Depends(_db),
):
    """
    Dashboard-н нэгдсэн snapshot — нэг л API хүсэлтэд бүх мэдээлэл.

    Агуулга:
      ewma          — сүүлийн Хокинсын EWMA дундаж
      entry_count   — нийт тэмдэглэлийн тоо
      top_patterns  — сүүлийн run-н хамгийн хүчтэй 3 pattern
      last_seed     — хамгийн сүүлийн seed insight
      last_human_insight — хамгийн сүүлийн human insight (байгаа бол)
      dominant_emotion   — хамгийн давамгай emotion (сүүлийн 10 entry)
    """
    user_id = user["id"]

    # 1. EWMA + entry count
    ewma = journal.get_user_ewma(user_id)
    count = journal.count_user_entries(user_id)

    # 2. Сүүлийн run-н top patterns (strength_score-оор)
    top_patterns = (
        db.table("detected_patterns")
        .select("pattern_type, pattern_data, strength_score, detected_at")
        .eq("user_id", user_id)
        .order("detected_at", desc=True)
        .order("strength_score", desc=True)
        .limit(3)
        .execute()
    ).data or []

    # 3. Хамгийн сүүлийн seed insight
    last_entry = (
        db.table("journal_entries")
        .select("id")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    ).data or []

    last_seed = None
    if last_entry:
        seed_rows = (
            db.table("seed_insights")
            .select("mirror, reframe, relief, summary, created_at")
            .eq("entry_id", last_entry[0]["id"])
            .execute()
        ).data or []
        last_seed = seed_rows[0] if seed_rows else None

    # 4. Хамгийн сүүлийн human insight
    last_human = (
        db.table("human_insights")
        .select("insight_text, highlight_type, strength_score, generated_at")
        .eq("user_id", user_id)
        .order("generated_at", desc=True)
        .limit(1)
        .execute()
    ).data or []

    # 5. Dominant emotion (journal_analyses-с шууд)
    recent_analyses = (
        db.table("journal_analyses")
        .select(
            "plutchik_primary, plutchik_intensity, "
            "journal_entries!inner(user_id)"
        )
        .eq("journal_entries.user_id", user_id)
        .not_.is_("plutchik_primary", "null")
        .order("processed_at", desc=True)
        .limit(10)
        .execute()
    ).data or []

    dominant_emotion = None
    if recent_analyses:
        totals: dict[str, float] = {}
        for r in recent_analyses:
            k = r["plutchik_primary"]
            totals[k] = totals.get(k, 0) + float(r.get("plutchik_intensity") or 0.5)
        dominant_emotion = max(totals, key=totals.__getitem__)

    return {
        "ewma":              ewma,
        "entry_count":       count,
        "top_patterns":      top_patterns,
        "last_seed_insight": last_seed,
        "last_human_insight": last_human[0] if last_human else None,
        "dominant_emotion":  dominant_emotion,
    }