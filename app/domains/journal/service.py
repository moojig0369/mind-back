"""
Journal Domain Service - Business Logic Layer
Orchestrates repository operations and domain rules.
Uses repository interfaces for flexibility and testability.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from uuid import UUID

from app.domains.journal.entities import JournalEntry, SeedInsight, AnalysisResult
from app.domains.journal.dto import JournalCreateDTO
from app.domains.journal.repository_interface import (
    JournalRepositoryInterface,
    AnalysisRepositoryInterface,
)
from app.infrastructure.ai.client import LLMClient
import asyncio


class JournalService:
    """
    Journal domain service.
    Handles business logic for journal entries.
    Depends on repository interfaces, not concrete implementations.
    """
    
    def __init__(
        self, 
        repo: JournalRepositoryInterface, 
        llm_client: Optional[LLMClient] = None,
        analysis_repo: Optional[AnalysisRepositoryInterface] = None
    ):
        self._repo = repo
        self._llm = llm_client
        self._analysis_repo = analysis_repo
    
    # ── Entry Operations ───────────────────────────────────────────────────────
    
    def create_entry(
        self, 
        user_id: str, 
        data: JournalCreateDTO
    ) -> Dict[str, Any]:
        """Create new journal entry."""
        index = self._repo.count_by_user(UUID(user_id)) + 1
        
        payload = {
            "user_id": user_id,
            "entry_index": index,
            "is_text_saved": data.save_text,
        }
        
        if data.save_text:
            payload.update({
                "surface_text": data.surface_text,
                "inner_reaction_text": data.inner_reaction_text,
                "meaning_text": data.meaning_text,
            })
        
        return self._repo.insert(payload)
    
    def get_entries(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated entries for user."""
        return self._repo.find_by_user(
            UUID(user_id), 
            page, 
            page_size, 
            search
        )
    
    def get_entry(self, entry_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get single entry with related data."""
        return self._repo.find_by_id(UUID(entry_id), UUID(user_id))
    
    def delete_entry(self, entry_id: str, user_id: str) -> bool:
        """Delete entry (CASCADE handles related data)."""
        return self._repo.delete(UUID(entry_id), UUID(user_id))
    
    # ── Seed Insight Operations ───────────────────────────────────────────────
    
    async def generate_seed_insight(
        self,
        surface: str,
        inner: str,
        meaning: str,
    ) -> SeedInsight:
        """Generate seed insight using LLM."""
        if not self._llm:
            raise ValueError("LLM client not configured")
        
        result = await self._llm.generate_seed_insight(
            surface=surface,
            inner=inner,
            meaning=meaning,
        )
        
        return SeedInsight(
            journal_id=None,  # Will be set by caller
            mirror=result.mirror,
            reframe=result.reframe,
            relief=result.relief,
            summary=result.summary or "",
        )
    
    def save_seed_insight(
        self, 
        entry_id: str, 
        insight: SeedInsight
    ) -> Dict[str, Any]:
        """Save seed insight to database."""
        return self._repo.save_seed_insight(
            UUID(entry_id), 
            insight.__dict__
        )
    
    # ── Psychometric Analysis Operations ──────────────────────────────────────
    
    async def run_analysis(
        self,
        surface: str,
        inner: str,
        meaning: str,
        ewma_previous: Optional[float] = None,
        entry_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AnalysisResult:
        """
        Гүн шинжилгээ хийх: Hawkins + Plutchik + Maslow.
        LLM-ээр шинжилгээ хийж, EWMA тооцоолно.
        """
        if not self._llm:
            raise ValueError("LLM client not configured")
        
        # LLM шинжилгээ
        raw = await self._llm.analyze_psychometrics(
            surface=surface,
            inner=inner,
            meaning=meaning,
            ewma_previous=ewma_previous,
        )
        
        # EWMA тооцоолол (α = 0.3)
        alpha = 0.3
        hawkins_level = raw.get("hawkins_level", 200)
        
        if ewma_previous is None:
            ewma_score = float(hawkins_level)
        else:
            ewma_score = alpha * hawkins_level + (1 - alpha) * ewma_previous
        
        # Trend тодорхойлох
        if ewma_previous is None:
            trend = "stable"
        elif ewma_score > ewma_previous * 1.1:
            trend = "improving"
        elif ewma_score < ewma_previous * 0.9:
            trend = "declining"
        else:
            trend = "stable"
        
        return AnalysisResult(
            hawkins_level=hawkins_level,
            hawkins_label_en=raw.get("hawkins_label_en", "Unknown"),
            hawkins_label_mn=raw.get("hawkins_label_mn", "Тодорхойгүй"),
            plutchik_primary=raw.get("plutchik_primary", "joy"),
            plutchik_dyad=raw.get("plutchik_dyad"),
            maslow_categories=raw.get("maslow_categories", ["social"]),
            crisis_flag=raw.get("crisis_flag", False),
            confidence=raw.get("confidence", 0.5),
            reasoning=raw.get("reasoning", ""),
            ewma_score=ewma_score,
            trend=trend,
            raw_response=raw,
        )
    
    def save_analysis(
        self,
        entry_id: str,
        result: AnalysisResult,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Шинжилгээний үр дүнг database-д хадгална."""
        if not self._analysis_repo:
            raise ValueError("AnalysisRepository not configured")
        
        from app.infrastructure.supabase_client import get_admin_client
        
        db = get_admin_client()
        # Use asyncio.run for proper async execution in sync context
        analysis = asyncio.run(
            self._analysis_repo.create_analysis(
                user_id=user_id or "",
                entry_id=entry_id,
                hawkins_level=result.hawkins_level,
                hawkins_label_en=result.hawkins_label_en,
                hawkins_label_mn=result.hawkins_label_mn,
                plutchik_emotions=[result.plutchik_primary],
                maslow_categories=result.maslow_categories,
                ewma_score=result.ewma_score,
                trend=result.trend,
                raw_response=str(result.raw_response),
            )
        )
        return {"id": analysis.id, "status": "saved"}
    
    def mark_analysis_processed(self, entry_id: str):
        """Шинжилгээг 'processed' төлөвт шилжүүлнэ."""
        if not self._analysis_repo:
            raise ValueError("AnalysisRepository not configured")
        
        # Use asyncio.run for proper async execution in sync context
        asyncio.run(
            self._analysis_repo.mark_as_processed(entry_id)
        )
    
    def get_user_ewma(self, user_id: str) -> Optional[float]:
        """Хэрэглэгчийн сүүлийн EWMA утгыг авна."""
        if not self._analysis_repo:
            return None
        
        # Use asyncio.run for proper async execution in sync context
        return asyncio.run(
            self._analysis_repo.get_user_ewma(user_id)
        )
    
    def count_user_entries(self, user_id: str) -> int:
        """Хэрэглэгчийн нийт бичлэгийн тоог авна."""
        if not self._analysis_repo:
            return 0
        
        # Use asyncio.run for proper async execution in sync context
        return asyncio.run(
            self._analysis_repo.count_user_entries(user_id)
        )
    
    def update_value_nodes(
        self,
        user_id: str,
        result: AnalysisResult,
        entry_id: str,
    ):
        """ValueNode-уудыг Maslow code-оор шинэчилнэ."""
        if not self._analysis_repo:
            raise ValueError("AnalysisRepository not configured")
        
        # Эхний Maslow category-г гол болгож ашиглана
        if result.maslow_categories:
            primary_maslow = result.maslow_categories[0]
            
            # ValueNode олох (entry_id-ээр)
            # Энэ нь journal_repo-оос хамаарна
            nodes = self._repo.find_value_nodes_by_entry(UUID(entry_id))
            
            for node in nodes:
                # Use asyncio.run for proper async execution in sync context
                asyncio.run(
                    self._analysis_repo.update_value_node_maslow(
                        node_id=node["id"],
                        maslow_code=primary_maslow,
                    )
                )
                
                # Tracker үүсгэх
                asyncio.run(
                    self._analysis_repo.create_maslow_tracker(
                        node_id=node["id"],
                        maslow_code=primary_maslow,
                        confidence=result.confidence,
                    )
                )
    
    # ── Deep Insight Operations ───────────────────────────────────────────────
    
    def build_graph_summary(self, user_id: str) -> Dict[str, Any]:
        """ValueGraph-ийн товчлолыг үүсгэнэ."""
        # TODO: Value graph-ээс өгөгдөл цуглуулах
        return {
            "user_id": user_id,
            "total_nodes": 0,
            "dominant_themes": [],
            "emotional_pattern": "unknown",
        }
    
    async def generate_deep_insight(
        self,
        summary: Dict[str, Any],
        entry_count: int,
    ) -> Dict[str, Any]:
        """Гүн шинжилгээний insight үүсгэнэ."""
        if not self._llm:
            raise ValueError("LLM client not configured")
        
        prompt = f"""
Хэрэглэгчийн {entry_count} бичлэгийн дүн шинжилгээ:
{summary}

Дараах форматтай гүн шинжилгээний insight үүсгэ:
{{
  "insight_text": "<гурван өгүүлбэртэй гүн утга учир>",
  "recommendations": ["<зөвлөгөө 1>", "<зөвлөгөө 2>", "<зөвлөгөө 3>"]
}}
"""
        
        return await self._llm.generate_json(prompt)
    
    # ── Business Rules ─────────────────────────────────────────────────────────
    
    def should_trigger_deep_insight(self, entry_count: int) -> bool:
        """
        Determine if deep insight should be triggered.
        Rule: Every 5th entry after 10 entries.
        """
        return entry_count >= 10 and entry_count % 5 == 0
