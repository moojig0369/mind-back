"""
LLM шинжилгээний дотоод болон гадагш Pydantic загварууд.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


# ── Plutchik ─────────────────────────────────────────────────────────────────

class PlutchikResult(BaseModel):
    primary: str
    primary_score: float = Field(ge=0, le=1)
    secondary: str | None = None
    secondary_score: float | None = Field(default=None, ge=0, le=1)
    dyad: str | None = None
    dyad_score: float | None = Field(default=None, ge=0, le=1)
    conflict_flag: bool = False
    intensity: str = "medium"  # low | medium | high


# ── Hawkins ──────────────────────────────────────────────────────────────────

class HawkinsResult(BaseModel):
    emotion: str
    level: int = Field(ge=20, le=1000)
    score: float = Field(ge=0, le=1)
    zone: str           # below_200 | above_200
    crisis_flag: bool = False
    ewma_previous: float | None = None
    ewma_updated: float | None = None


# ── Seed Insight ─────────────────────────────────────────────────────────────

class SeedInsightData(BaseModel):
    mirror: str = ""
    reframe: str = ""
    relief: str = ""
    summary: str = ""


class SeedInsightResponse(SeedInsightData):
    id: UUID
    entry_id: UUID
    created_at: datetime


# ── LLM нэгдсэн гаралт (дотоод) ─────────────────────────────────────────────

class LlmAnalysisResult(BaseModel):
    maslow: list[dict]
    plutchik: PlutchikResult
    hawkins: HawkinsResult
    # seed_insight: SeedInsightData


# ── Deep Insight ─────────────────────────────────────────────────────────────

class DeepInsightResponse(BaseModel):
    id: UUID
    insight_text: str
    recommendations: list[str]
    generated_at: datetime
