"""
Journal Domain Service - Business Logic Layer
Orchestrates repository operations and domain rules.
"""

from typing import List, Dict, Any, Optional
from app.domains.journal.entities import JournalEntry, SeedInsight
from app.domains.journal.schemas import JournalCreateRequest
from app.infrastructure.repositories.journal_repo import JournalRepository
from app.infrastructure.ai.client import LLMClient


class JournalService:
    """
    Journal domain service.
    Handles business logic for journal entries.
    """
    
    def __init__(self, repo: JournalRepository, llm_client: Optional[LLMClient] = None):
        self._repo = repo
        self._llm = llm_client
    
    # ── Entry Operations ───────────────────────────────────────────────────────
    
    def create_entry(
        self, 
        user_id: str, 
        data: JournalCreateRequest
    ) -> Dict[str, Any]:
        """Create new journal entry."""
        index = self._repo.count_by_user(user_id) + 1
        
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
        return self._repo.find_by_user(user_id, page, page_size, search)
    
    def get_entry(self, entry_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get single entry with related data."""
        return self._repo.find_by_id(entry_id, user_id)
    
    def delete_entry(self, entry_id: str, user_id: str) -> bool:
        """Delete entry (CASCADE handles related data)."""
        return self._repo.delete(entry_id, user_id)
    
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
        return self._repo.save_seed_insight(entry_id, insight.model_dump())
    
    # ── Business Rules ─────────────────────────────────────────────────────────
    
    def should_trigger_deep_insight(self, entry_count: int) -> bool:
        """
        Determine if deep insight should be triggered.
        Rule: Every 5th entry after 10 entries.
        """
        return entry_count >= 10 and entry_count % 5 == 0
