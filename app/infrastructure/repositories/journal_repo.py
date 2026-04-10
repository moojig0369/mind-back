"""
Journal Repository - Database Access Layer
Handles all direct database operations for Journal domain.
Uses Supabase client for database access.
"""

from typing import Optional, List, Dict, Any
from supabase import Client


class JournalRepository:
    """Repository for JournalEntry and related entities."""
    
    def __init__(self, db: Client):
        self._db = db
    
    # ── CRUD Operations ───────────────────────────────────────────────────────
    
    def count_by_user(self, user_id: str) -> int:
        """Count total entries for a user."""
        result = (
            self._db.table("journal_entries")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        return result.count or 0
    
    def find_by_id(self, entry_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Find single entry by ID with related data."""
        result = (
            self._db.table("journal_entries")
            .select("*, seed_insights(*), journal_steps(*)")
            .eq("id", entry_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        return result.data
    
    def find_by_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Find entries by user with pagination and search."""
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
            "items": result.data or [],
            "total": result.count or 0,
            "page": page,
            "page_size": page_size,
            "has_more": ((page - 1) * page_size + len(result.data or [])) < (result.count or 0)
        }
    
    def insert(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Insert new journal entry."""
        result = self._db.table("journal_entries").insert(payload).execute()
        return result.data[0]
    
    def delete(self, entry_id: str, user_id: str) -> bool:
        """Delete entry by ID (CASCADE will handle related data)."""
        result = (
            self._db.table("journal_entries")
            .delete()
            .eq("id", entry_id)
            .eq("user_id", user_id)
            .execute()
        )
        return len(result.data) > 0
    
    # ── Seed Insights ─────────────────────────────────────────────────────────
    
    def save_seed_insight(self, entry_id: str, insight: Dict[str, Any]) -> Dict[str, Any]:
        """Save seed insight for an entry."""
        keys = ("mirror", "reframe", "relief", "summary")
        payload = {"entry_id": entry_id, **{k: insight[k] for k in keys if k in insight}}
        result = self._db.table("seed_insights").insert(payload).execute()
        return result.data[0]
    
    # ── Journal Steps ─────────────────────────────────────────────────────────
    
    def save_journal_step(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save journal step (surface → inner → meaning)."""
        result = self._db.table("journal_steps").insert(step_data).execute()
        return result.data[0]
    
    def find_steps_by_journal(self, journal_id: str) -> List[Dict[str, Any]]:
        """Find all steps for a journal entry."""
        result = (
            self._db.table("journal_steps")
            .select("*")
            .eq("journal_id", journal_id)
            .execute()
        )
        return result.data or []
    
    # ── Value Nodes ────────────────────────────────────────────────────────────
    
    def find_value_nodes_by_entry(self, entry_id: str) -> List[Dict[str, Any]]:
        """Find value nodes created from a journal entry."""
        result = (
            self._db.table("value_nodes")
            .select("*")
            .eq("source_entry_id", entry_id)
            .execute()
        )
        return result.data or []
