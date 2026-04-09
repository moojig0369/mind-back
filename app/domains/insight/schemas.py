"""
Insight domain schemas for API requests/responses.
Pydantic models for validation.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class MaslowItem(BaseModel):
    """Maslow category with values."""
    
    category: str
    values: Dict[str, float]


class PsychometricAnalysisRequest(BaseModel):
    """Request for psychometric analysis."""
    
    surface_text: str
    inner_text: str
    meaning_text: str
    ewma_previous: Optional[float] = None


class PsychometricAnalysisResponse(BaseModel):
    """Psychometric analysis result."""
    
    id: UUID
    journal_id: UUID
    maslow_categories: List[str]
    plutchik_primary: Optional[str]
    plutchik_dyad: Optional[str]
    hawkins_level: Optional[int]
    hawkins_label: Optional[str]
    hawkins_confidence: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AnalysisLogResponse(BaseModel):
    """Analysis performance log."""
    
    id: UUID
    analysis_id: UUID
    model_name: Optional[str]
    duration: Optional[float]
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    error: Optional[str]
    processed_at: datetime
    
    class Config:
        from_attributes = True


class RecommendationInsightResponse(BaseModel):
    """Recommendation insight response."""
    
    id: UUID
    user_id: UUID
    insight_text: str
    recommendations: Optional[Dict[str, Any]]
    is_actioned: bool
    generated_at: datetime
    
    class Config:
        from_attributes = True


class DeepInsightRequest(BaseModel):
    """Request for deep insight generation."""
    
    graph_summary: Dict[str, Any]
    entry_count: int


class DeepInsightResponse(BaseModel):
    """Deep insight result."""
    
    insight_text: str
    recommendations: List[str]
    patterns: List[str]
