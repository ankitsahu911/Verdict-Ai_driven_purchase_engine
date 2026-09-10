from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class DecisionAxis(str, Enum):
    VERSATILITY = "versatility"
    REDUNDANCY = "redundancy"
    SEASONAL_RELEVANCE = "seasonal_relevance"
    BUDGET_IMPACT = "budget_impact"
    STYLE_ALIGNMENT = "style_alignment"
    OCCASION_COVERAGE = "occasion_coverage"


class AxisScore(BaseModel):
    axis: DecisionAxis = Field(..., description="Decision axis identifier")
    score: float = Field(..., ge=0.0, le=100.0, description="Score normalized 0-100")
    reason: str = Field(..., description="Explanation string")
    source_agent: str = Field(..., description="Agent or module source")
    raw_evidence: dict[str, Any] | None = Field(default=None, description="Supporting metrics")


class CandidateDecisionPayload(BaseModel):
    candidate_id: int
    scores: dict[DecisionAxis, AxisScore] = Field(default_factory=dict)
    overall_score: float | None = Field(default=None, ge=0.0, le=100.0)


class ConfidenceResult(BaseModel):
    level: str = Field(..., description="'high' | 'medium' | 'low'")
    reasoning: str = Field(..., description="Explanation naming the contributing signals")
    signals: dict[str, Any] | None = Field(default=None, description="Supporting numerical metrics")


class BuyScoreResult(BaseModel):
    candidate_id: int
    verdict: str
    overall_score: float = Field(..., ge=0.0, le=100.0)
    headline_reason: str
    axes: list[AxisScore]
    weights_used: dict[str, float]
    decision_log_id: int | None = None
    confidence: ConfidenceResult | None = None
    summary_panel: dict[str, Any] | None = None
    tryon_degraded: bool = False
    created_at: str
