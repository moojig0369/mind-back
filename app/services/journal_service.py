"""
JournalService — тэмдэглэлийн CRUD болон
analysis хадгалалтын бизнес логик.

ValueGraph болон EWMA тооцоолол нь тусдаа
модульд (graph_builder.py, ewma.py) хуваарилагдсан.
"""

from supabase import Client
from app.schemas.analysis import LlmAnalysisResult
from app.schemas.entry import EntryCreateRequest
from app.services.ewma import calculate as calculate_ewma
from app.services.graph_builder import GraphBuilder

_DEEP_INSIGHT_THRESHOLD = 10


def _snap_hawkins_level(level: int) -> int:
    """LLM-н буцаасан дурын утгыг хамгийн ойр ref_hawkins утга руу тааруулна."""
    return min(_HAWKINS_VALID_LEVELS, key=lambda v: abs(v - level))


class JournalService:
    """Тэмдэглэлийн CRUD болон шинжилгээ хадгалалт."""

    def __init__(self, db: Client) -> None:
        self._db = db
        self._graph = GraphBuilder(db)

    # ── Entry ────────────────────────────────────────────────────────────────

    def count_user_entries(self, user_id: str) -> int:
        result = (
            self._db.table("journal_entries")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        return result.count or 0

    def fetch_entries(
        self,
        user_id: str,
        page: int,
        page_size: int,
        search: str | None,
    ) -> dict:
        query = (
            self._db.table("journal_entries")
            .select("*", count="exact")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range((page - 1) * page_size, page * page_size - 1)
        )
        if search:
            query = query.or_(
                f"surface_text.ilike.%{search}%,"
                f"inner_reaction_text.ilike.%{search}%,"
                f"meaning_text.ilike.%{search}%"
            )
        result = query.execute()
        return {
            "items": result.data,
            "total": result.count,
            "page": page,
            "page_size": page_size,
        }

    def fetch_entry(self, entry_id: str, user_id: str) -> dict | None:
        result = (
            self._db.table("journal_entries")
            .select("*, seed_insights(*), journal_analyses(*)")
            .eq("id", entry_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        return result.data

    def create_entry(self, user_id: str, data: EntryCreateRequest) -> dict:
        index = self.count_user_entries(user_id) + 1
        payload: dict = {
            "user_id": user_id,
            "entry_index": index,
            "is_text_saved": data.save_text,
        }
        if data.save_text:
            payload.update(
                {
                    "surface_text": data.surface_text,
                    "inner_reaction_text": data.inner_reaction_text,
                    "meaning_text": data.meaning_text,
                }
            )
        return self._db.table("journal_entries").insert(payload).execute().data[0]

    def delete_entry(self, entry_id: str, user_id: str) -> bool:
        result = (
            self._db.table("journal_entries")
            .delete()
            .eq("id", entry_id)
            .eq("user_id", user_id)
            .execute()
        )
        return len(result.data) > 0

    # ── Analysis ─────────────────────────────────────────────────────────────

    def save_seed_insight(self, entry_id: str, insight: dict) -> dict:
        keys = ("mirror", "reframe", "relief", "summary")
        payload = {"entry_id": entry_id, **{k: insight[k] for k in keys}}
        return self._db.table("seed_insights").insert(payload).execute().data[0]

    def save_analysis(self, entry_id: str, result: LlmAnalysisResult) -> dict:
        p, h = result.plutchik, result.hawkins
        payload = {
            "entry_id": entry_id,
            "maslow": result.maslow,
            "plutchik_primary": p.primary,
            "plutchik_dyad": p.dyad,
            "plutchik_intensity": p.primary_score,
            "hawkins_label": h.emotion.lower(),
            "hawkins_level": h.level,
            "hawkins_score": h.score,
        }
        return (
            self._db.table("journal_analyses").upsert(payload).execute().data[0]
        )

    def mark_analysis_processed(self, entry_id: str) -> None:
        self._db.table("journal_analyses").update(
            {"processed_at": "now()"}
        ).eq("entry_id", entry_id).execute()

    # ── EWMA ─────────────────────────────────────────────────────────────────

    def get_user_ewma(self, user_id: str) -> float | None:
        """Хэрэглэгчийн сүүлийн 10 тэмдэглэлийн Хокинсын EWMA дундаж."""
        rows = (
            self._db.table("journal_analyses")
            .select(
                "hawkins_level,"
                "journal_entries!inner(user_id)"
            )
            .eq("journal_entries.user_id", user_id)
            .order("processed_at", desc=True)  # ← засвар
            .limit(10)
            .execute()
        ).data or []

        levels = [r["hawkins_level"] for r in rows if r.get("hawkins_level")]
        return calculate_ewma(levels)

    # ── ValueGraph (delegate) ─────────────────────────────────────────────────

    def update_value_nodes(
        self,
        user_id: str,
        analysis: LlmAnalysisResult,
        entry_id: str,
    ) -> None:
        self._graph.update_graph(user_id, analysis, entry_id)

    def fetch_value_graph(self, user_id: str) -> dict:
        return self._graph.fetch_graph(user_id)

    def build_graph_summary(self, user_id: str) -> dict:
        summary = self._graph.build_summary(user_id)
        summary["ewma_avg"] = self.get_user_ewma(user_id)
        return summary

    def should_trigger_deep_insight(self, count: int) -> bool:
        return count >= _DEEP_INSIGHT_THRESHOLD and count % 5 == 0
