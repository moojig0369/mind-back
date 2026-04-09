"""
Journal domain repository.
Data access layer for journal operations.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.infrastructure.models import JournalEntryDB, JournalStepDB
from app.domains.journal.entities import JournalEntry


class JournalRepository:
    """Repository for JournalEntry data access."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, entry_id: UUID, user_id: UUID) -> Optional[JournalEntry]:
        """Get journal entry by ID and user ID."""
        result = await self.session.execute(
            select(JournalEntryDB).where(
                JournalEntryDB.id == entry_id,
                JournalEntryDB.user_id == user_id
            )
        )
        db_model = result.scalar_one_or_none()
        if not db_model:
            return None
        
        return JournalEntry(
            id=db_model.id,
            user_id=db_model.user_id,
            entry_index=db_model.entry_index,
            is_text_saved=db_model.is_text_saved,
            surface_text=db_model.surface_text,
            inner_reaction_text=db_model.inner_reaction_text,
            meaning_text=db_model.meaning_text,
            created_at=db_model.created_at,
        )
    
    async def count_by_user(self, user_id: UUID) -> int:
        """Count journal entries for a user."""
        result = await self.session.execute(
            select(func.count()).where(JournalEntryDB.user_id == user_id)
        )
        return result.scalar() or 0
    
    async def list_by_user(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List journal entries with pagination and optional search."""
        query = select(JournalEntryDB).where(JournalEntryDB.user_id == user_id)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (JournalEntryDB.surface_text.ilike(search_pattern)) |
                (JournalEntryDB.inner_reaction_text.ilike(search_pattern)) |
                (JournalEntryDB.meaning_text.ilike(search_pattern))
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination
        query = query.order_by(JournalEntryDB.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.session.execute(query)
        db_models = result.scalars().all()
        
        items = [
            JournalEntry(
                id=m.id,
                user_id=m.user_id,
                entry_index=m.entry_index,
                is_text_saved=m.is_text_saved,
                surface_text=m.surface_text,
                inner_reaction_text=m.inner_reaction_text,
                meaning_text=m.meaning_text,
                created_at=m.created_at,
            )
            for m in db_models
        ]
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    
    async def create(self, entry: JournalEntry) -> JournalEntry:
        """Create a new journal entry."""
        db_model = JournalEntryDB(
            id=entry.id,
            user_id=entry.user_id,
            entry_index=entry.entry_index,
            is_text_saved=entry.is_text_saved,
            surface_text=entry.surface_text,
            inner_reaction_text=entry.inner_reaction_text,
            meaning_text=entry.meaning_text,
        )
        
        self.session.add(db_model)
        await self.session.flush()  # Get generated fields
        await self.session.refresh(db_model)
        
        # Update entity with DB values
        entry.entry_index = db_model.entry_index
        entry.created_at = db_model.created_at
        
        return entry
    
    async def delete(self, entry_id: UUID, user_id: UUID) -> bool:
        """Delete a journal entry."""
        result = await self.session.execute(
            select(JournalEntryDB).where(
                JournalEntryDB.id == entry_id,
                JournalEntryDB.user_id == user_id
            )
        )
        db_model = result.scalar_one_or_none()
        
        if not db_model:
            return False
        
        await self.session.delete(db_model)
        return True
