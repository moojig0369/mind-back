"""
LLM шинжилгээний дотоод болон гадагш Pydantic загварууд.
Design class: PsychometricAnalysis, Insight-тай нийцүүлсэн.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional


# ── Maslow Category Enum ──────────────────────────────────────────────────────

class MaslowCategory(str):
    PHYSIOLOGICAL = "physiological"
    SAFETY = "safety"
    SOCIAL = "social"
    ESTEEM = "esteem"
    SELF_ACTUALIZATION = "self_actualization"


# ── Plutchik ─────────────────────────────────────────────────────────────────

class PlutchikResult(BaseModel):
    primary: str
    primary_score: float = Field(ge=0, le=1)
    secondary: Optional[str] = None
    secondary_score: Optional[float] = Field(default=None, ge=0, le=1)
    dyad: Optional[str] = None
    dyad_score: Optional[float] = Field(default=None, ge=0, le=1)
    conflict_flag: bool = False
    intensity: str = "medium"  # low | medium | high


# ── Hawkins ──────────────────────────────────────────────────────────────────

class HawkinsResult(BaseModel):
    emotion: str
    level: int = Field(ge=20, le=1000)
    score: float = Field(ge=0, le=1)
    zone: str           # below_200 | above_200
    crisis_flag: bool = False
    ewma_previous: Optional[float] = None
    ewma_updated: Optional[float] = None


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


# ── Psychometric Analysis (Design class) ─────────────────────────────────────

class MaslowItem(BaseModel):
    category: str
    values: list[dict[str, float]]


class PsychometricAnalysisResult(BaseModel):
    """Design class: PsychometricAnalysis-тай тохирох LLM гаралт."""
    maslow: list[MaslowItem]
    plutchik_primary: str
    plutchik_dyad: Optional[str] = None
    hawkins_level: int
    hawkins_label: str
    hawkins_confidence: float = Field(ge=0, le=1)
    plutchik: Optional[PlutchikResult] = None  # Backward compatibility
    hawkins: Optional[HawkinsResult] = None    # Backward compatibility


# ── LLM нэгдсэн гаралт (дотоод) ─────────────────────────────────────────────

class LlmAnalysisResult(BaseModel):
    """Backward compatibility wrapper."""
    maslow: list[dict]
    plutchik: PlutchikResult
    hawkins: HawkinsResult
    
    def to_psychometric(self) -> PsychometricAnalysisResult:
        """PsychometricAnalysisResult руу хөрвүүлнэ."""
        return PsychometricAnalysisResult(
            maslow=[MaslowItem(**item) for item in self.maslow],
            plutchik_primary=self.plutchik.primary,
            plutchik_dyad=self.plutchik.dyad,
            hawkins_level=self.hawkins.level,
            hawkins_label=self.hawkins.emotion,
            hawkins_confidence=self.hawkins.score,
            plutchik=self.plutchik,
            hawkins=self.hawkins,
        )


# ── Deep Insight ─────────────────────────────────────────────────────────────

class DeepInsightResponse(BaseModel):
    id: UUID
    insight_text: str
    recommendations: list[str]
    generated_at: datetime


# ── Recommendation Insight (Design class) ────────────────────────────────────

class RecommendationInsightResponse(BaseModel):
    id: UUID
    user_id: UUID
    insight_text: str
    recommendations: dict
    is_actioned: bool
    generated_at: datetime
