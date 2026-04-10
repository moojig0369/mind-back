"""
Pydantic schemas for Graph API responses.
Optimized for frontend visualization.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID


class ValueNodeSchema(BaseModel):
    """Value Node for visualization."""
    id: str
    value: str
    weight: float
    avg_hawkins: Optional[float] = None
    mention_count: int = 0
    maslow_code: Optional[str] = None
    dominant_primary: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ValueEdgeSchema(BaseModel):
    """Value Edge for visualization."""
    id: str
    source_node_id: str
    target_node_id: str
    weight: float
    created_at: datetime
    
    class Config:
        from_attributes = True


class PatternSchema(BaseModel):
    """Detected behavioral pattern."""
    id: str
    pattern_type: str
    description: str
    strength: float
    detected_at: datetime
    
    class Config:
        from_attributes = True


class RecommendationSchema(BaseModel):
    """Actionable recommendation."""
    id: str
    insight_text: str
    recommendations: List[str]
    is_actioned: bool = False
    generated_at: datetime
    
    class Config:
        from_attributes = True


class GraphSummarySchema(BaseModel):
    """Complete graph summary for visualization."""
    user_id: str
    total_nodes: int
    total_edges: int
    nodes: List[ValueNodeSchema]
    edges: List[ValueEdgeSchema]
    patterns: List[PatternSchema]
    recommendations: List[RecommendationSchema]
    dominant_values: List[str]
    emotional_trend: str
    hawkins_average: float
    maslow_distribution: Dict[str, int]
    
    class Config:
        from_attributes = True


class GraphVisualizationSchema(BaseModel):
    """Frontend-ready graph data structure."""
    nodes: List[Dict[str, Any]]
    links: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    
    class Config:
        from_attributes = True
