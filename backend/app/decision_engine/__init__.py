"""
Verdict Decision Engine Package.

Provides shared schema contracts, polarity normalization rules, and protocol
interfaces for all decision axis scorers.
"""

from app.decision_engine.interface import AxisScorer
from app.decision_engine.orchestrator import (
    BUY_THRESHOLD,
    CONSIDER_THRESHOLD,
    DEFAULT_AXIS_WEIGHTS,
    synthesize_buy_score,
)
from app.decision_engine.schema import (
    AxisScore,
    BuyScoreResult,
    CandidateDecisionPayload,
    DecisionAxis,
)

__all__ = [
    "DecisionAxis",
    "AxisScore",
    "CandidateDecisionPayload",
    "BuyScoreResult",
    "AxisScorer",
    "synthesize_buy_score",
    "DEFAULT_AXIS_WEIGHTS",
    "BUY_THRESHOLD",
    "CONSIDER_THRESHOLD",
]

