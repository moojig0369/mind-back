"""
Journal Domain Entities - Business Logic
Design Class: Journal, ReflectionPrompt, Insight
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class JournalEntry(BaseModel):
    """
    Design Class: Journal
    Тэмдэглэлийн үндсэн domain entity
    """
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    entry_index: int = 0
    is_text_saved: bool = True
    surface_text: Optional[str] = None
    inner_reaction_text: Optional[str] = None
    meaning_text: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Computed fields (DB-ээс ирэхгүй, зөвхөн logic-д ашиглана)
    has_analysis: bool = False
    status: str = "pending_analysis"  # pending_analysis, analyzed, failed
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
    
    @classmethod
    def create(cls, user_id: str, save_text: bool, **kwargs) -> "JournalEntry":
        """Factory method to create a new journal entry."""
        return cls(
            user_id=user_id,
            is_text_saved=save_text,
            surface_text=kwargs.get("surface_text") if save_text else None,
            inner_reaction_text=kwargs.get("inner_reaction_text") if save_text else None,
            meaning_text=kwargs.get("meaning_text") if save_text else None,
        )
    
    def get_full_text(self) -> str:
        """Combine all text fields for LLM analysis."""
        parts = []
        if self.surface_text:
            parts.append(f"Surface: {self.surface_text}")
        if self.inner_reaction_text:
            parts.append(f"Inner: {self.inner_reaction_text}")
        if self.meaning_text:
            parts.append(f"Meaning: {self.meaning_text}")
        return "\n".join(parts)
    
    def mark_analyzed(self) -> None:
        """Шинжилгээ амжилттай дууссан"""
        self.status = "analyzed"
        self.has_analysis = True
    
    def mark_failed(self) -> None:
        """Шинжилгээ бүтэлгүйтсэн"""
        self.status = "failed"


class JournalStep(BaseModel):
    """
    Design Class: ReflectionPrompt
    Journal steps (surface → inner → meaning)
    """
    id: Optional[UUID] = Field(default_factory=uuid4)
    journal_id: UUID
    action_type: str  # quick_action_type enum
    surface_text: Optional[str] = None
    surface_at: Optional[datetime] = None
    inner_text: Optional[str] = None
    inner_at: Optional[datetime] = None
    meaning_text: Optional[str] = None
    meaning_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


class SeedInsight(BaseModel):
    """
    Design Class: Insight (seed level)
    GPT-ээс шууд ирэх анхны insight
    """
    id: Optional[UUID] = None
    journal_id: UUID
    mirror: str = ""
    reframe: str = ""
    relief: str = ""
    summary: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
    
    def is_empty(self) -> bool:
        """Хоосон insight эсэхийг шалгах"""
        return not (self.mirror or self.reframe or self.relief)
