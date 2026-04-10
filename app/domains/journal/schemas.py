"""
Journal API Schemas - Request/Response Models for API Layer
These are Pydantic models used ONLY for API validation and serialization.
Domain logic should NOT depend on these.
"""

from datetime import datetime
from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel, Field


# ── Request Schemas ────────────────────────────────────────────────────────────

class JournalCreateRequest(BaseModel):
    """Тэмдэглэл үүсгэх хүсэлт."""
    surface_text: str = Field(..., min_length=1, max_length=5000)
    inner_reaction_text: str = Field(..., min_length=1, max_length=5000)
    meaning_text: str = Field(..., min_length=1, max_length=5000)
    save_text: bool = True


class JournalUpdateRequest(BaseModel):
    """Тэмдэглэл шинэчлэх хүсэлт."""
    surface_text: Optional[str] = Field(None, max_length=5000)
    inner_reaction_text: Optional[str] = Field(None, max_length=5000)
    meaning_text: Optional[str] = Field(None, max_length=5000)


# ── Response Schemas ───────────────────────────────────────────────────────────

class JournalResponse(BaseModel):
    """Тэмдэглэлийн хариу."""
    id: UUID
    user_id: UUID
    entry_index: int
    is_text_saved: bool
    surface_text: Optional[str] = None
    inner_reaction_text: Optional[str] = None
    meaning_text: Optional[str] = None
    created_at: datetime
    has_analysis: bool = False
    
    class Config:
        from_attributes = True


class JournalListResponse(BaseModel):
    """Тэмдэглэлийн жагсаалт."""
    items: List[JournalResponse]
    total: int
    page: int
    page_size: int


class SeedInsightResponse(BaseModel):
    """Seed Insight хариу."""
    mirror: str
    reframe: str
    relief: str
    summary: str


class JournalCreateResponse(BaseModel):
    """Тэмдэглэл үүсгэх хариу."""
    entry_id: UUID
    seed_insight: SeedInsightResponse
    analysis_channel: str
