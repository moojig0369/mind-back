"""
JournalService — тэмдэглэлийн CRUD болон
analysis хадгалалтын бизнес логик.

ValueGraph болон EWMA тооцоолол нь тусдаа
модульд (graph_builder.py, ewma.py) хуваарилагдсан.

Design class-тай нийцүүлсэн:
  - PsychometricAnalysis → psychometric_analyses хүснэгт
  - AnalysisLog → analysis_logs хүснэгт
  - ValueGraph → value_graphs хүснэгт
"""

from supabase import Client
from app.schemas.analysis import LlmAnalysisResult, PsychometricAnalysisResult
from app.schemas.entry import EntryCreateRequest
from app.services.ewma import calculate as calculate_ewma
from app.services.graph_builder import GraphBuilder
import time
from datetime import datetime, timezone

_DEEP_INSIGHT_THRESHOLD = 10


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
            .select("*, seed_insights(*), journal_steps(*)")
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

    # ── Analysis (Design class: PsychometricAnalysis) ────────────────────────

    def save_seed_insight(self, entry_id: str, insight: dict) -> dict:
        keys = ("mirror", "reframe", "relief", "summary")
        payload = {"entry_id": entry_id, **{k: insight[k] for k in keys}}
        return self._db.table("seed_insights").insert(payload).execute().data[0]

    def save_psychometric_analysis(
        self, 
        entry_id: str, 
        result: PsychometricAnalysisResult,
        llm_duration: float = 0.0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model_name: str = "",
        error: str | None = None,
    ) -> dict:
        """
        Design class: PsychometricAnalysis-тай тохирох шинэчлэл.
        1. psychometric_analyses хүснэгтэд шинжилгээ хадгална
        2. analysis_logs хүснэгтэд performance log нэмнэ
        """
        # 1. Psychometric Analysis
        p_result = result.model_dump()
        payload = {
            "journal_id": entry_id,
            "maslow_categories": [item["category"] for item in p_result.get("maslow", [])],
            "plutchik_primary": p_result.get("plutchik_primary"),
            "plutchik_dyad": p_result.get("plutchik_dyad"),
            "hawkins_level": p_result.get("hawkins_level"),
            "hawkins_label": p_result.get("hawkins_label"),
            "hawkins_confidence": p_result.get("hawkins_confidence"),
        }
        
        analysis_result = (
            self._db.table("psychometric_analyses")
            .upsert(payload)
            .execute()
        ).data[0]
        
        analysis_id = analysis_result["id"]
        
        # 2. Analysis Log (Design class: AnalysisLog)
        if llm_duration > 0 or prompt_tokens > 0 or completion_tokens > 0:
            self._db.table("analysis_logs").insert({
                "analysis_id": analysis_id,
                "model_name": model_name,
                "duration": llm_duration,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "error": error,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
        
        return analysis_result

    def save_analysis(self, entry_id: str, result: LlmAnalysisResult) -> dict:
        """Backward compatibility wrapper."""
        psych_result = result.to_psychometric()
        return self.save_psychometric_analysis(entry_id, psych_result)

    def mark_analysis_processed(self, entry_id: str) -> None:
        """Backward compatibility - одоо processed_at автоматаар хадгалагдана."""
        pass

    # ── EWMA ─────────────────────────────────────────────────────────────────

    def get_user_ewma(self, user_id: str) -> float | None:
        """Хэрэглэгчийн сүүлийн 10 тэмдэглэлийн Хокинсын EWMA дундаж."""
        rows = (
            self._db.table("psychometric_analyses")
            .select(
                "hawkins_level,"
                "journal_entries!inner(user_id)"
            )
            .eq("journal_entries.user_id", user_id)
            .order("created_at", desc=True)
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
