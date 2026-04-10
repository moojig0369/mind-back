"""
Journal Domain Entities - Pure Business Logic Objects
These are NOT Pydantic models, they are plain dataclasses/objects.
No validation logic, no serialization - pure domain concepts.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from dataclasses import dataclass, field


@dataclass
class JournalEntry:
    """
    Design Class: Journal
    Тэмдэглэлийн үндсэн domain entity
    """
    user_id: UUID
    entry_index: int = 0
    is_text_saved: bool = True
    surface_text: Optional[str] = None
    inner_reaction_text: Optional[str] = None
    meaning_text: Optional[str] = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Computed fields (DB-ээс ирэхгүй, зөвхөн logic-д ашиглана)
    has_analysis: bool = False
    status: str = "pending_analysis"  # pending_analysis, analyzed, failed
    
    @classmethod
    def create(cls, user_id: UUID, save_text: bool, **kwargs) -> "JournalEntry":
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


@dataclass
class JournalStep:
    """
    Design Class: ReflectionPrompt
    Journal steps (surface → inner → meaning)
    """
    journal_id: UUID
    action_type: str  # quick_action_type enum
    id: UUID = field(default_factory=uuid4)
    surface_text: Optional[str] = None
    surface_at: Optional[datetime] = None
    inner_text: Optional[str] = None
    inner_at: Optional[datetime] = None
    meaning_text: Optional[str] = None
    meaning_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SeedInsight:
    """
    Design Class: Insight (seed level)
    GPT-ээс шууд ирэх анхны insight
    """
    mirror: str = ""
    reframe: str = ""
    relief: str = ""
    summary: str = ""
    id: Optional[UUID] = None
    journal_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_empty(self) -> bool:
        """Хоосон insight эсэхийг шалгах"""
        return not (self.mirror or self.reframe or self.relief)


@dataclass
class AnalysisResult:
    """Шинжилгээний үр дүн (Domain concept)."""
    hawkins_level: int
    hawkins_label_en: str
    hawkins_label_mn: str
    plutchik_primary: str
    plutchik_dyad: Optional[str]
    maslow_categories: List[str]
    crisis_flag: bool
    confidence: float
    reasoning: str
    ewma_score: float
    trend: str
    raw_response: dict
