"""
Journal domain entities.
Business objects that encapsulate domain logic.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from dataclasses import dataclass, field


@dataclass
class JournalEntry:
    """Design class: Journal - Domain entity."""
    
    id: UUID
    user_id: UUID
    entry_index: int
    is_text_saved: bool = False
    surface_text: Optional[str] = None
    inner_reaction_text: Optional[str] = None
    meaning_text: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Computed fields
    has_analysis: bool = False
    seed_insights: List[dict] = field(default_factory=list)
    
    @classmethod
    def create(cls, user_id: UUID, save_text: bool, **kwargs) -> "JournalEntry":
        """Factory method to create a new journal entry."""
        return cls(
            id=uuid4(),
            user_id=user_id,
            entry_index=0,  # Will be set by service
            is_text_saved=save_text,
            surface_text=kwargs.get("surface_text") if save_text else None,
            inner_reaction_text=kwargs.get("inner_reaction_text") if save_text else None,
            meaning_text=kwargs.get("meaning_text") if save_text else None,
        )
    
    def get_full_text(self) -> str:
        """Combine all text fields for analysis."""
        parts = []
        if self.surface_text:
            parts.append(f"Surface: {self.surface_text}")
        if self.inner_reaction_text:
            parts.append(f"Inner: {self.inner_reaction_text}")
        if self.meaning_text:
            parts.append(f"Meaning: {self.meaning_text}")
        return "\n".join(parts)


@dataclass
class JournalStep:
    """Design class: ReflectionPrompt - Step in journal process."""
    
    id: UUID
    journal_id: UUID
    action_type: str
    surface_text: Optional[str] = None
    surface_at: Optional[datetime] = None
    inner_text: Optional[str] = None
    inner_at: Optional[datetime] = None
    meaning_text: Optional[str] = None
    meaning_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
