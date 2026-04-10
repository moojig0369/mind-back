"""
Repository Interfaces - Abstract definitions for data access.
Domain layer depends on these interfaces, not concrete implementations.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Generic, TypeVar
from uuid import UUID

T = TypeVar('T')


class JournalRepositoryInterface(ABC):
    """Interface for Journal repository operations."""
    
    @abstractmethod
    def count_by_user(self, user_id: UUID) -> int:
        """Count total entries for a user."""
        pass
    
    @abstractmethod
    def find_by_id(self, entry_id: UUID, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Find single entry by ID with related data."""
        pass
    
    @abstractmethod
    def find_by_user(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Find entries by user with pagination and search."""
        pass
    
    @abstractmethod
    def insert(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Insert new journal entry."""
        pass
    
    @abstractmethod
    def delete(self, entry_id: UUID, user_id: UUID) -> bool:
        """Delete entry by ID (CASCADE will handle related data)."""
        pass
    
    @abstractmethod
    def save_seed_insight(self, entry_id: UUID, insight: Dict[str, Any]) -> Dict[str, Any]:
        """Save seed insight for an entry."""
        pass
    
    @abstractmethod
    def save_journal_step(self, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save journal step (surface → inner → meaning)."""
        pass
    
    @abstractmethod
    def find_steps_by_journal(self, journal_id: UUID) -> List[Dict[str, Any]]:
        """Find all steps for a journal entry."""
        pass
    
    @abstractmethod
    def find_value_nodes_by_entry(self, entry_id: UUID) -> List[Dict[str, Any]]:
        """Find value nodes created from a journal entry."""
        pass


class AnalysisRepositoryInterface(ABC):
    """Interface for Analysis repository operations."""
    
    @abstractmethod
    async def create_analysis(
        self,
        user_id: str,
        entry_id: str,
        hawkins_level: int,
        hawkins_label_en: str,
        hawkins_label_mn: str,
        plutchik_emotions: List[str],
        maslow_categories: List[str],
        ewma_score: float,
        trend: str,
        raw_response: str,
    ) -> Any:
        """Create new analysis record."""
        pass
    
    @abstractmethod
    async def mark_as_processed(self, entry_id: str) -> bool:
        """Mark analysis as processed."""
        pass
    
    @abstractmethod
    async def get_user_ewma(self, user_id: str) -> Optional[float]:
        """Get user's latest EWMA score."""
        pass
    
    @abstractmethod
    async def count_user_entries(self, user_id: str) -> int:
        """Count user's analyzed entries."""
        pass
    
    @abstractmethod
    async def update_value_node_maslow(self, node_id: str, maslow_code: str) -> bool:
        """Update value node with Maslow category."""
        pass
    
    @abstractmethod
    async def create_maslow_tracker(
        self,
        node_id: str,
        maslow_code: str,
        confidence: float,
    ) -> Any:
        """Create Maslow tracking record."""
        pass
