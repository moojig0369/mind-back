"""
Pattern domain schemas for API requests/responses.
Pydantic models for validation - Flow 3: Pattern Detection & Recommendation
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class PatternRuleResponse(BaseModel):
    """Pattern rule response."""
    
    id: UUID
    rule_name: str
    rule_type: str
    description: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class PatternResponse(BaseModel):
    """Detected pattern response."""
    
    id: UUID
    graph_id: UUID
    rule_id: Optional[UUID]
    pattern_type: str
    description: str
    strength: float
    detected_at: datetime
    
    class Config:
        from_attributes = True


class PatternDetectorRequest(BaseModel):
    """Request for pattern detection."""
    
    graph_id: UUID
    user_id: UUID


class PatternDetectionResponse(BaseModel):
    """Pattern detection result."""
    
    patterns: List[PatternResponse]
    trend_summary: Optional[str] = None


class RecommendationInsightCreate(BaseModel):
    """Create recommendation insight."""
    
    user_id: UUID
    insight_text: str
    recommendations: Dict[str, Any]
    pattern_id: Optional[UUID] = None


class RecommendationInsightResponse(BaseModel):
    """Recommendation insight response."""
    
    id: UUID
    user_id: UUID
    pattern_id: Optional[UUID]
    insight_text: str
    recommendations: Optional[Dict[str, Any]]
    is_actioned: bool
    generated_at: datetime
    
    class Config:
        from_attributes = True


class RecommendationActionRequest(BaseModel):
    """Request to mark recommendation as actioned."""
    
    is_actioned: bool = True
