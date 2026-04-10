"""
Journal Domain DTOs - Data Transfer Objects for domain service input/output
These are simple dataclasses used to pass data between API and Domain layers.
Domain logic should NOT depend on Pydantic models.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class JournalCreateDTO:
    """Data transfer object for creating journal entry."""
    surface_text: str
    inner_reaction_text: str
    meaning_text: str
    save_text: bool = True
