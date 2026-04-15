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

# ── Response schema ────────────────────────────────────────────────────────────

class EmotionStatRow(BaseModel):
    emotion:    str
    score_sum:  float
    count:      int
    percentage: float


def _db() -> Client:
    return get_admin_client()


def _get_journal_service() -> JournalService:
    return JournalService(get_admin_client())


# ── Helpers ────────────────────────────────────────────────────────────────────

def _resolve_hawkins_band(db: Client, score: float | None) -> dict | None:
    """EWMA score-оос Hawkins label + band мэдээлэл авна."""
    if score is None:
        return None

    level = round(score * 1000)  # 0–1 → 0–1000

    row = (
        db.table("ref_hawkins")
        .select("level,view_of_life,transcend_key,what_we_experience,state_of_consciousness, label_en, label_mn, band_code, ref_hawkins_bands(label_mn, color_hex, level_min, level_max)")
        .lte("level", level)
        .order("level", desc=True)
        .limit(1)
        .execute()
    ).data

    if not row:
        return None

    r = row[0]
    band = r.get("ref_hawkins_bands") or {}
    return {
        "level":      r["level"],
        "label_en":   r["label_en"],
        "label_mn":   r["label_mn"],
        "band_code":  r["band_code"],
        "band_label": band.get("label_mn"),
        "color_hex":  band.get("color_hex"),
        "band_min":   band.get("level_min"),
        "band_max":   band.get("level_max"),
    }


def _next_hawkins_target(db: Client, current_level: int) -> dict | None:
    """Дараагийн band-н хамгийн доод level-г зорилт болгоно."""
    if current_level is None:
        return None

    # Одоогийн band авна
    current_band_row = (
        db.table("ref_hawkins")
        .select("band_code, ref_hawkins_bands(level_max)")
        .lte("level", current_level)
        .order("level", desc=True)
        .limit(1)
        .execute()
    ).data

    if not current_band_row:
        return None

    current_band_max = (current_band_row[0].get("ref_hawkins_bands") or {}).get("level_max")
    if current_band_max is None:
        return None

    # Дараагийн band-н хамгийн доод level
    next_row = (
        db.table("ref_hawkins")
        .select("level, label_en, label_mn, band_code, ref_hawkins_bands(label_mn, color_hex)")
        .gt("level", current_band_max)
        .order("level", asc=True)
        .limit(1)
        .execute()
    ).data

    if not next_row:
        return None

    r = next_row[0]
    band = r.get("ref_hawkins_bands") or {}
    return {
        "level":      r["level"],
        "label_en":   r["label_en"],
        "label_mn":   r["label_mn"],
        "band_label": band.get("label_mn"),
        "color_hex":  band.get("color_hex"),
        "gap":        r["level"] - current_level,
    }


def _get_dyad(db: Client, emotion_a: str, emotion_b: str) -> dict | None:
    """Хоёр primary emotion-н dyad нэр авна."""
    rows = (
        db.table("ref_plutchik_dyads")
        .select("dyad_name_en, dyad_name_mn")
        .or_(
            f"and(emotion_a.eq.{emotion_a},emotion_b.eq.{emotion_b}),"
            f"and(emotion_a.eq.{emotion_b},emotion_b.eq.{emotion_a})"
        )
        .limit(1)
        .execute()
    ).data

    if not rows:
        return None

    return {
        "name_en": rows[0]["dyad_name_en"],
        "name_mn": rows[0]["dyad_name_mn"],
    }


# ── Endpoints ──────────────────────────────────────────────────────────────────

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
    """
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

    rows = (
        db.table("journal_analyses")
        .select("plutchik_primary, plutchik_intensity")
        .in_("entry_id", entry_ids)
        .not_.is_("plutchik_primary", "null")
        .execute()
    ).data or []

    if not rows:
        return []

    totals: dict[str, dict] = {}
    for r in rows:
        key = r["plutchik_primary"]
        score = float(r.get("plutchik_intensity") or 0.5)
        if key not in totals:
            totals[key] = {"score_sum": 0.0, "count": 0}
        totals[key]["score_sum"] += score
        totals[key]["count"]     += 1

    total_score = sum(v["score_sum"] for v in totals.values()) or 1.0

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
      hawkins_current    — EWMA-с тооцсон одоогийн Hawkins төлөв (label, band, color)
      hawkins_target     — дараагийн band-н хамгийн доод level (зорилт + gap)
      entry_count        — нийт тэмдэглэлийн тоо
      unread_patterns    — acknowledged=false байгаа patterns (strength-оор эрэмбэлсэн)
      last_human_insight — хамгийн сүүлийн human insight (pattern-г үгээр тайлбарласан)
      dominant_emotions  — хамгийн хүчтэй 2 сэтгэл хөдлөл + тэдгээрийн dyad
    """
    user_id = user["id"]

    # 1. EWMA + Hawkins одоогийн болон зорилтот төлөв
    ewma = journal.get_user_ewma(user_id)
    count = journal.count_user_entries(user_id)

    hawkins_current = _resolve_hawkins_band(db, ewma)
    hawkins_target = (
        _next_hawkins_target(db, hawkins_current["level"])
        if hawkins_current else None
    )

    # 2. Уншаагүй patterns (acknowledged=false) — strength-оор

    all_unread = (
        db.table("detected_patterns")
        .select("id, pattern_type, pattern_data, strength_score, detected_at")
        .eq("user_id", user_id)
        .order("strength_score", desc=True)
        .execute()
    ).data or []

    # pattern_type тус бүрээс хамгийн хүчтэй 1-г авна
    seen_types: set[str] = set()
    unread_patterns = []
    for p in all_unread:
        pt = p["pattern_type"]
        if pt not in seen_types:
            seen_types.add(pt)
            unread_patterns.append(p)

    # 3. Хамгийн сүүлийн human insight (pattern-г үгээр тайлбарласан)
    last_human = (
        db.table("human_insights")
        .select("insight_text, highlight_type, strength_score, generated_at")
        .eq("user_id", user_id)
        .order("generated_at", desc=True)
        .limit(1)
        .execute()
    ).data or []

    # 4. Top 2 dominant emotion + dyad (journal_analyses-с шууд)
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

    dominant_emotions = []
    dyad = None

    if recent_analyses:
        # Score нийлбэр тооцно
        totals: dict[str, float] = {}
        for r in recent_analyses:
            k = r["plutchik_primary"]
            totals[k] = totals.get(k, 0) + float(r.get("plutchik_intensity") or 0.5)

        # Top 2 авна
        sorted_emotions = sorted(totals.items(), key=lambda x: x[1], reverse=True)
        top_2 = sorted_emotions[:2]

        # ref_plutchik-с emoji авна
        if top_2:
            emotion_keys = [e[0] for e in top_2]
            ref_rows = (
                db.table("ref_plutchik")
                .select("emotion_key, label_mn, emoji")
                .in_("emotion_key", emotion_keys)
                .execute()
            ).data or []
            ref_map = {r["emotion_key"]: r for r in ref_rows}

            total_score = sum(totals.values()) or 1.0
            for emotion_key, score in top_2:
                ref = ref_map.get(emotion_key, {})
                dominant_emotions.append({
                    "emotion":    emotion_key,
                    "label_mn":   ref.get("label_mn"),
                    "emoji":      ref.get("emoji"),
                    "score":      round(score, 3),
                    "percentage": round(score / total_score * 100, 1),
                })

        # Хоёр emotion байвал dyad хайна
        if len(top_2) == 2:
            dyad = _get_dyad(db, top_2[0][0], top_2[1][0])

    return {
        "hawkins_current":    hawkins_current,
        "hawkins_target":     hawkins_target,
        "entry_count":        count,
        "unread_patterns":    unread_patterns,
        "last_human_insight": last_human[0] if last_human else None,
        "dominant_emotions":  dominant_emotions,
        "dominant_dyad":      dyad,
    }