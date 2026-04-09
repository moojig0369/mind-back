"""
Journal API Routes - Controller Layer
Thin controllers that delegate to domain services.
"""

from fastapi import APIRouter, Depends, BackgroundTasks, Query, status, HTTPException
from typing import Optional
from uuid import UUID

from app.domains.journal.service import JournalService
from app.domains.journal.schemas import (
    JournalCreateRequest,
    JournalResponse,
    JournalListResponse,
    JournalCreateResponse,
    SeedInsightResponse,
)
from app.api.v1.deps import get_journal_service, get_current_user


router = APIRouter(prefix="/entries", tags=["Тэмдэглэл"])


def _get_journal_service() -> JournalService:
    """Dependency factory for journal service."""
    return get_journal_service()


@router.get("/", response_model=JournalListResponse)
async def list_entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    service: JournalService = Depends(_get_journal_service),
):
    """Get paginated journal entries with optional search."""
    result = service.get_entries(
        user_id=user["id"],
        page=page,
        page_size=page_size,
        search=search,
    )
    return result


@router.get("/{entry_id}", response_model=JournalResponse)
async def get_entry(
    entry_id: str,
    user: dict = Depends(get_current_user),
    service: JournalService = Depends(_get_journal_service),
):
    """Get single journal entry with related data."""
    entry = service.get_entry(entry_id, user["id"])
    if not entry:
        raise HTTPException(status_code=404, detail="Тэмдэглэл олдсонгүй")
    return entry


@router.post("/", response_model=JournalCreateResponse, status_code=201)
async def create_entry(
    data: JournalCreateRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    service: JournalService = Depends(_get_journal_service),
):
    """
    Create new journal entry.
    - Seed Insight: returned immediately (sync)
    - Full Analysis: queued for background processing (async)
    """
    from app.infrastructure.ai.client import LLMClient
    from app.db.redis_client import get_analysis_queue
    
    # 1. Create entry
    entry = service.create_entry(user["id"], data)
    entry_id = entry["id"]
    
    # 2. Generate seed insight (sync)
    llm = LLMClient()
    seed_insight = await service.generate_seed_insight(
        surface=data.surface_text,
        inner=data.inner_reaction_text,
        meaning=data.meaning_text,
    )
    
    # Save seed insight if not empty
    if not seed_insight.is_empty():
        service.save_seed_insight(entry_id, seed_insight)
    
    # 3. Queue full analysis (async)
    if data.save_text:
        background_tasks.add_task(
            _enqueue_analysis,
            entry_id=entry_id,
            user_id=user["id"],
            entry_text={
                "surface": data.surface_text,
                "inner": data.inner_reaction_text,
                "meaning": data.meaning_text,
            },
        )
    
    return JournalCreateResponse(
        entry_id=UUID(entry_id),
        seed_insight=SeedInsightResponse(
            mirror=seed_insight.mirror,
            reframe=seed_insight.reframe,
            relief=seed_insight.relief,
            summary=seed_insight.summary,
        ),
        analysis_channel=f"entry:{entry_id}",
    )


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: str,
    user: dict = Depends(get_current_user),
    service: JournalService = Depends(_get_journal_service),
):
    """Delete journal entry (CASCADE handles related data)."""
    if not service.delete_entry(entry_id, user["id"]):
        raise HTTPException(status_code=404, detail="Тэмдэглэл олдсонгүй")


# ── Private Helpers ───────────────────────────────────────────────────────────

def _enqueue_analysis(entry_id: str, user_id: str, entry_text: dict) -> None:
    """Enqueue psychometric analysis job."""
    get_analysis_queue().enqueue(
        "app.workers.jobs.run_analysis_job",
        entry_id=entry_id,
        user_id=user_id,
        entry_text=entry_text,
        job_timeout=120,
    )
