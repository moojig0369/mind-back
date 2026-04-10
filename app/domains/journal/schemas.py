"""
Journal Domain Schemas - Pure Domain Data Structures
These are NOT Pydantic models, they are plain dataclasses.
No validation logic, no serialization - pure domain concepts.
Used ONLY within the domain layer.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from dataclasses import dataclass, field


@dataclass
class SeedInsightData:
    """
    Domain concept: Seed Insight data structure
    GPT-ээс шууд ирэх анхны insight
    """
    mirror: str = ""
    reframe: str = ""
    relief: str = ""
    summary: str = ""
    journal_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_empty(self) -> bool:
        """Хоосон insight эсэхийг шалгах"""
        return not (self.mirror or self.reframe or self.relief)


@dataclass
class AnalysisResultData:
    """Domain concept: Шинжилгээний үр дүн."""
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


@dataclass
class GraphSummaryData:
    """Domain concept: ValueGraph товчлол."""
    user_id: str
    total_nodes: int
    dominant_themes: List[str]
    emotional_pattern: str


@dataclass
class DeepInsightData:
    """Domain concept: Гүн шинжилгээний insight."""
    insight_text: str
    recommendations: List[str]
