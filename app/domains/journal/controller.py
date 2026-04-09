"""
Journal domain controller (API routes).
Thin controller that delegates to service layer.
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_db
from app.domains.journal.service import JournalService
from app.domains.journal.schemas import (
    JournalCreateRequest,
    JournalResponse,
    JournalListResponse,
)
from app.domains.journal.entities import JournalEntry


router = APIRouter(prefix="/journal", tags=["Journal"])


def get_journal_service(db: AsyncSession) -> JournalService:
    """Dependency to get journal service."""
    return JournalService(db)


@router.post("/", response_model=JournalResponse)
async def create_journal_entry(
    body: JournalCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    service: JournalService = Depends(get_journal_service),
    # user: dict = Depends(get_current_user),  # TODO: Add auth
) -> JournalEntry:
    """Create a new journal entry."""
    # TODO: Extract user_id from auth
    user_id = UUID("00000000-0000-0000-0000-000000000000")
    
    entry = await service.create_entry(user_id, body)
    
    # TODO: Trigger async analysis in background
    # background_tasks.add_task(trigger_analysis, entry.id)
    
    return entry


@router.get("/", response_model=JournalListResponse)
async def list_journal_entries(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    service: JournalService = Depends(get_journal_service),
    # user: dict = Depends(get_current_user),
) -> dict:
    """List journal entries with pagination."""
    # TODO: Extract user_id from auth
    user_id = UUID("00000000-0000-0000-0000-000000000000")
    
    result = await service.list_entries(
        user_id=user_id,
        page=page,
        page_size=page_size,
        search=search,
    )
    
    return result


@router.get("/{entry_id}", response_model=JournalResponse)
async def get_journal_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    service: JournalService = Depends(get_journal_service),
    # user: dict = Depends(get_current_user),
) -> JournalEntry:
    """Get a specific journal entry."""
    # TODO: Extract user_id from auth
    user_id = UUID("00000000-0000-0000-0000-000000000000")
    
    return await service.get_entry(entry_id, user_id)


@router.delete("/{entry_id}")
async def delete_journal_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    service: JournalService = Depends(get_journal_service),
    # user: dict = Depends(get_current_user),
) -> dict:
    """Delete a journal entry."""
    # TODO: Extract user_id from auth
    user_id = UUID("00000000-0000-0000-0000-000000000000")
    
    success = await service.delete_entry(entry_id, user_id)
    
    return {"success": success, "id": str(entry_id)}
