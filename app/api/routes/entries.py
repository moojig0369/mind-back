"""
/api/entries — тэмдэглэлийн CRUD endpoint-ууд.

Урсгал (POST /):
  1. Тэмдэглэл DB-д хадгална
  2. Seed Insight → шууд LLM дуудаж хариу буцаана  (sync)
  3. Analysis     → Redis Queue-д илгээнэ           (async)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.schemas.entry import (
    EntryCreateRequest,
    EntryResponse,
    PaginatedEntryResponse,
)
from app.schemas.analysis import SeedInsightData
from app.services.auth_service import get_current_user
from app.services.journal_service import JournalService
from app.services.llm_service import get_llm_service
from app.db.supabase import get_admin_client
from app.db.redis_client import get_analysis_queue, get_deep_insight_queue
from pydantic import BaseModel

router = APIRouter(prefix="/entries", tags=["Тэмдэглэл"])


class EntryCreateResponse(BaseModel):
    entry_id: str
    seed_insight: SeedInsightData   # шууд буцаана
    analysis_channel: str           # WS channel — analysis дуусахад мэдэгдэнэ


def _journal() -> JournalService:
    return JournalService(get_admin_client())


# ── CRUD ─────────────────────────────────────────────────────────────────────

@router.get("/", response_model=PaginatedEntryResponse)
async def list_entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    user: dict = Depends(get_current_user),
    journal: JournalService = Depends(_journal),
):
    """Тэмдэглэлийн жагсаалт. Хайлт хийх боломжтой."""
    return journal.fetch_entries(user["id"], page, page_size, search)


@router.get("/{entry_id}", response_model=EntryResponse)
async def get_entry(
    entry_id: str,
    user: dict = Depends(get_current_user),
    journal: JournalService = Depends(_journal),
):
    """Тэмдэглэлийн дэлгэрэнгүй (Seed Insight + Analysis хамт)."""
    entry = journal.fetch_entry(entry_id, user["id"])
    if not entry:
        raise HTTPException(status_code=404, detail="Тэмдэглэл олдсонгүй")
    return entry


@router.post("/", response_model=EntryCreateResponse, status_code=201)
async def create_entry(
    data: EntryCreateRequest,
    user: dict = Depends(get_current_user),
    journal: JournalService = Depends(_journal),
):
    """
    Тэмдэглэл үүсгэнэ.
    - Seed Insight: шууд буцаана (sync)
    - Analysis: queue-д илгээнэ, WS-аар мэдэгдэл авна (async)
    """
    user_id = user["id"]
    llm = get_llm_service()

    # 1. Тэмдэглэл хадгална
    entry = journal.create_entry(user_id, data)
    entry_id = entry["id"]

    # 2. Seed Insight — шууд
    seed = await llm.generate_seed_insight(
        surface=data.surface_text,
        inner=data.inner_reaction_text,
        meaning=data.meaning_text,
    )

    if seed.mirror != '':
        journal.save_seed_insight(entry_id, seed.model_dump())
            # 3. Analysis — queue
        _enqueue_analysis(entry_id, user_id, data)

    # 4. Deep Insight — 10+ тэмдэглэлийн дараа trigger
    count = journal.count_user_entries(user_id)
    if journal.should_trigger_deep_insight(count):
        get_deep_insight_queue().enqueue(
            "app.workers.jobs.process_deep_insight",
            user_id=user_id,
            job_timeout=180,
        )

    return EntryCreateResponse(
        entry_id=entry_id,
        seed_insight=seed,
        analysis_channel=f"entry:{entry_id}",
    )


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: str,
    user: dict = Depends(get_current_user),
    journal: JournalService = Depends(_journal),
):
    """Тэмдэглэл устгана (CASCADE: analysis, insight хамт устна)."""
    if not journal.delete_entry(entry_id, user["id"]):
        raise HTTPException(status_code=404, detail="Тэмдэглэл олдсонгүй")


# ── Private ───────────────────────────────────────────────────────────────────

def _enqueue_analysis(
    entry_id: str, user_id: str, data: EntryCreateRequest
) -> None:
    get_analysis_queue().enqueue(
        "app.workers.jobs.run_analysis_job",
        entry_id=entry_id,
        user_id=user_id,
        entry_text={
            "surface": data.surface_text,
            "inner": data.inner_reaction_text,
            "meaning": data.meaning_text,
        },
        job_timeout=120,
    )