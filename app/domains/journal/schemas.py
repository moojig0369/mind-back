"""
Journal domain schemas for API requests/responses.
Pydantic models for validation.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


class JournalCreateRequest(BaseModel):
    """Request to create a new journal entry."""
    
    save_text: bool = Field(..., description="Whether to save the text content")
    surface_text: Optional[str] = Field(None, max_length=5000)
    inner_reaction_text: Optional[str] = Field(None, max_length=5000)
    meaning_text: Optional[str] = Field(None, max_length=5000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "save_text": True,
                "surface_text": "Today I felt overwhelmed...",
                "inner_reaction_text": "I noticed tension in my chest...",
                "meaning_text": "This reminds me of my need for control..."
            }
        }


class JournalResponse(BaseModel):
    """Journal entry response."""
    
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
    """Paginated list of journal entries."""
    
    items: List[JournalResponse]
    total: int
    page: int
    page_size: int
    
    class Config:
        from_attributes = True


class SeedInsightRequest(BaseModel):
    """Request for seed insight generation."""
    
    surface_text: str
    inner_text: str
    meaning_text: str


class SeedInsightResponse(BaseModel):
    """Seed insight response."""
    
    mirror: str
    reframe: str
    relief: str
    summary: str
