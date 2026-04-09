from pydantic import BaseModel
from uuid import UUID

class ValueNodeResponse(BaseModel):
    id: UUID
    maslow_category: str
    maslow_value: str
    weight: float
    mention_count: int
    dominant_primary: str | None
    dominant_dyad: str | None


class ValueEdgeResponse(BaseModel):
    id: UUID
    from_node_id: UUID
    to_node_id: UUID
    hawkins_level_avg: float
    hawkins_score_avg: float
    interaction_count: int


class ValueGraphResponse(BaseModel):
    nodes: list[ValueNodeResponse]
    edges: list[ValueEdgeResponse]
