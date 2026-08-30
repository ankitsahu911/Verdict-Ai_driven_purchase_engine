"""
Shared Decision Axes Schema (MILESTONE 19).

Defines the typed Pydantic models for the 6 decision axes in Verdict:
- versatility
- redundancy
- seasonal_relevance
- budget_impact
- style_alignment
- occasion_coverage

==============================================================================
NORTH STAR POLARITY RULE:
==============================================================================
Every axis score MUST be normalized to a float scale between 0.0 and 100.0
where HIGHER = MORE FAVORABLE TO BUYING (100 = Strongest Buy Signal, 0 = Skip Signal).

Polarity Mapping per Axis:
1. versatility:
   - 100.0 = Highly versatile (pairs with many existing wardrobe items).
   - 0.0   = Not versatile (pairs with zero existing items).

2. redundancy (phrased internally as Uniqueness):
   - 100.0 = Very unique / No duplicate owned in wardrobe.
   - 0.0   = Near-exact duplicate already owned in wardrobe.

3. seasonal_relevance:
   - 100.0 = Highly relevant for current or upcoming season.
   - 0.0   = Out of season / Off-season purchase.

4. budget_impact:
   - 100.0 = Low cost-per-wear / Great economic value for budget.
   - 0.0   = Extremely high cost-per-wear / Unfavorable budget impact.

5. style_alignment:
   - 100.0 = Perfectly aligns with user's aesthetic & personal style.
   - 0.0   = Complete style mismatch.

6. occasion_coverage:
   - 100.0 = Fills a major missing gap in user's occasion coverage.
   - 0.0   = Over-represented occasion / No coverage benefit.
==============================================================================
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DecisionAxis(str, Enum):
    """Enumeration of the 6 core decision axes in Verdict."""

    VERSATILITY = "versatility"
    REDUNDANCY = "redundancy"
    SEASONAL_RELEVANCE = "seasonal_relevance"
    BUDGET_IMPACT = "budget_impact"
    STYLE_ALIGNMENT = "style_alignment"
    OCCASION_COVERAGE = "occasion_coverage"


class AxisScore(BaseModel):
    """Typed Pydantic model representing a single decision axis score.

    Consumed by Buy Score Engine, What-If Lab, and Opportunity Cost components.
    """

    axis: DecisionAxis = Field(
        ...,
        description="The decision axis key.",
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Normalized score 0.0-100.0 where HIGHER = MORE FAVORABLE TO BUYING.",
    )
    reason: str = Field(
        ...,
        description="Plain-English one-liner explanation generated from real evidence.",
    )
    source_agent: str = Field(
        ...,
        description="Name of the agent or service that produced this score for traceability.",
    )
    raw_evidence: dict[str, Any] | None = Field(
        default=None,
        description="Optional dictionary containing supporting empirical evidence.",
    )


class CandidateDecisionPayload(BaseModel):
    """Aggregated decision payload containing scores across decision axes."""

    candidate_id: int = Field(..., description="ID of the candidate wardrobe item.")
    scores: dict[DecisionAxis, AxisScore] = Field(
        default_factory=dict,
        description="Dictionary mapping each DecisionAxis to its evaluated AxisScore.",
    )
    overall_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Optional aggregated overall Buy Score (0-100).",
    )


class BuyScoreResult(BaseModel):
    """Complete synthesized Buy Score and verdict result (Milestone 23)."""

    candidate_id: int = Field(..., description="ID of the candidate wardrobe item.")
    verdict: str = Field(..., description="Actionable verdict: 'buy', 'consider', or 'skip'.")
    overall_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Weighted average Buy Score (0-100).",
    )
    headline_reason: str = Field(
        ...,
        description="Plain-English headline summary sentence built deterministically from axis reasons.",
    )
    axes: list[AxisScore] = Field(
        ...,
        description="Full breakdown of the 6 evaluated decision axes.",
    )
    weights_used: dict[str, float] = Field(
        ...,
        description="Dictionary mapping axis names to weights used in synthesis.",
    )
    decision_log_id: int | None = Field(
        default=None,
        description="Database primary key of the created DecisionLog record, if persisted.",
    )
    created_at: str = Field(
        ...,
        description="ISO 8601 UTC timestamp of verdict synthesis.",
    )

