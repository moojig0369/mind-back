"""
Journal API Routes - Controller Layer
Thin controllers that delegate to domain services.
Demo mode - no authentication required.
"""

from fastapi import APIRouter, Depends, BackgroundTasks, Query, status, HTTPException
from typing import Optional
from uuid import UUID

from app.domains.journal.service import JournalService
from app.api.v1.schemas import (
    JournalCreateRequest,
    JournalResponse,
    JournalListResponse,
    JournalCreateResponse,
    SeedInsightResponse,
)
from app.api.v1.deps import get_journal_service
from app.domains.journal.dto import JournalCreateDTO
from app.infrastructure.ai.client import LLMClient
from app.workers.tasks import run_psychometric_analysis


router = APIRouter(prefix="/entries", tags=["Тэмдэглэл"])


def _get_journal_service() -> JournalService:
    """Dependency factory for journal service."""
    return get_journal_service()


@router.get("/", response_model=JournalListResponse)
async def list_entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    service: JournalService = Depends(_get_journal_service),
):
    """Get paginated journal entries with optional search."""
    # Demo mode: use a fixed demo user ID
    demo_user_id = "demo-user-0000-0000-0000-000000000000"
    result = service.get_entries(
        user_id=demo_user_id,
        page=page,
        page_size=page_size,
        search=search,
    )
    return result


@router.get("/{entry_id}", response_model=JournalResponse)
async def get_entry(
    entry_id: str,
    service: JournalService = Depends(_get_journal_service),
):
    """Get single journal entry with related data."""
    demo_user_id = "demo-user-0000-0000-0000-000000000000"
    entry = service.get_entry(entry_id, demo_user_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Тэмдэглэл олдсонгүй")
    return entry


@router.post("/", response_model=JournalCreateResponse, status_code=201)
async def create_entry(
    data: JournalCreateRequest,
    background_tasks: BackgroundTasks,
    service: JournalService = Depends(_get_journal_service),
):
    """
    Create new journal entry.
    - Seed Insight: returned immediately (sync)
    - Full Analysis: queued for background processing (async)
    """
    demo_user_id = "demo-user-0000-0000-0000-000000000000"
    
    # Convert API schema to domain DTO
    domain_data = JournalCreateDTO(
        surface_text=data.surface_text,
        inner_reaction_text=data.inner_reaction_text,
        meaning_text=data.meaning_text,
        save_text=data.save_text,
    )
    
    # 1. Create entry
    entry = service.create_entry(demo_user_id, domain_data)
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
            user_id=demo_user_id,
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


@router.post("/demo", response_model=JournalCreateResponse, status_code=201)
async def create_demo_entry(
    background_tasks: BackgroundTasks,
    service: JournalService = Depends(_get_journal_service),
):
    """
    Create demo journal entry with predefined content for testing.
    - Seed Insight: returned immediately (sync)
    - Full Analysis: queued for background processing (async)
    """
    demo_user_id = "demo-user-0000-0000-0000-000000000000"
    
    # Predefined demo content
    demo_data = JournalCreateDTO(
        surface_text="Өнөөдөр ажлын хурал дээр шинэ санаа гаргасан. Багийнхан маань сонирхолтой гэж хариулсан.",
        inner_reaction_text="Эхлээд жаахан эмээсэн ч, дараа нь бахархалтай болсон. Миний бодол үнэ цэнэтэй гэдгийг ойлголоо.",
        meaning_text="Би өөрийн гэсэн үзэл бодолтой, түүнийгээ илэрхийлэх эр зоригтой хүн юм байна.",
        save_text=True,
    )
    
    # 1. Create entry
    entry = service.create_entry(demo_user_id, demo_data)
    entry_id = entry["id"]
    
    # 2. Generate seed insight (sync)
    llm = LLMClient()
    seed_insight = await service.generate_seed_insight(
        surface=demo_data.surface_text,
        inner=demo_data.inner_reaction_text,
        meaning=demo_data.meaning_text,
    )
    
    # Save seed insight if not empty
    if not seed_insight.is_empty():
        service.save_seed_insight(entry_id, seed_insight)
    
    # 3. Queue full analysis (async)
    background_tasks.add_task(
        _enqueue_analysis,
        entry_id=entry_id,
        user_id=demo_user_id,
        entry_text={
            "surface": demo_data.surface_text,
            "inner": demo_data.inner_reaction_text,
            "meaning": demo_data.meaning_text,
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
    service: JournalService = Depends(_get_journal_service),
):
    """Delete journal entry (CASCADE handles related data)."""
    demo_user_id = "demo-user-0000-0000-0000-000000000000"
    if not service.delete_entry(entry_id, demo_user_id):
        raise HTTPException(status_code=404, detail="Тэмдэглэл олдсонгүй")


# ── Private Helpers ───────────────────────────────────────────────────────────

def _enqueue_analysis(entry_id: str, user_id: str, entry_text: dict) -> None:
    """Enqueue psychometric analysis job to RQ worker."""
    from app.workers.tasks import run_psychometric_analysis
    
    # Use RQ queue directly
    from rq import Queue
    from redis import Redis
    from app.core.settings import settings

    redis_client = Redis.from_url(settings.redis_url)
    queue = Queue("analysis", connection=redis_client)
    queue.enqueue(
        run_psychometric_analysis,
        entry_id=entry_id,
        user_id=user_id,
        entry_text=entry_text,
        job_timeout=120,
    )
    
    # After analysis completes, check if Deep Insight should be scheduled
    queue.enqueue(
        "app.workers.tasks.schedule_deep_insight",
        user_id=user_id,
        depends_on=None,  # Will run after this job
    )
