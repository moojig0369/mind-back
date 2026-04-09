"""
Journal domain service.
Business logic for journal operations.
"""

from typing import Optional, Dict, Any, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.repositories.journal_repo import JournalRepository
from app.domains.journal.entities import JournalEntry
from app.domains.journal.schemas import JournalCreateRequest
from app.core.exceptions import NotFoundException


class JournalService:
    """Service for journal business logic."""
    
    def __init__(self, session: AsyncSession):
        self.repo = JournalRepository(session)
    
    async def create_entry(
        self,
        user_id: UUID,
        data: JournalCreateRequest,
    ) -> JournalEntry:
        """Create a new journal entry."""
        # Get next entry index
        count = await self.repo.count_by_user(user_id)
        
        # Create entity
        entry = JournalEntry.create(
            user_id=user_id,
            save_text=data.save_text,
            surface_text=data.surface_text,
            inner_reaction_text=data.inner_reaction_text,
            meaning_text=data.meaning_text,
        )
        entry.entry_index = count + 1
        
        # Save to DB
        return await self.repo.create(entry)
    
    async def get_entry(
        self,
        entry_id: UUID,
        user_id: UUID,
    ) -> JournalEntry:
        """Get a journal entry by ID."""
        entry = await self.repo.get_by_id(entry_id, user_id)
        if not entry:
            raise NotFoundException("Journal entry", str(entry_id))
        return entry
    
    async def list_entries(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List journal entries with pagination."""
        return await self.repo.list_by_user(
            user_id=user_id,
            page=page,
            page_size=page_size,
            search=search,
        )
    
    async def delete_entry(
        self,
        entry_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Delete a journal entry."""
        return await self.repo.delete(entry_id, user_id)
    
    async def get_entry_count(self, user_id: UUID) -> int:
        """Get total count of journal entries for a user."""
        return await self.repo.count_by_user(user_id)
