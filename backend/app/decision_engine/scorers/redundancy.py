"""
Redundancy Axis Scorer (MILESTONE 20).

Calculates a 0-100 uniqueness score derived from the candidate's persisted
duplicate similarity percentage.

Inverted Polarity Rule (Milestone 19):
- Higher score = More unique / non-redundant (favorable to buying).
- Score = 100.0 - duplicate_similarity_pct.
- Null duplicate match = 100.0 (favorable / highly unique).

Source Agent: duplicate_detection
"""

import logging
from sqlalchemy.orm import Session

from app.decision_engine.schema import AxisScore, DecisionAxis
from app.models import WardrobeItem

logger = logging.getLogger(__name__)


def score_redundancy(candidate_item_id: int, db: Session) -> AxisScore:
    """Evaluate redundancy (uniqueness) score for a candidate item.

    Args:
        candidate_item_id: Primary key of candidate WardrobeItem.
        db: Active SQLAlchemy database session.

    Returns:
        AxisScore adhering to Milestone 19 contract.
    """
    candidate = db.query(WardrobeItem).filter(WardrobeItem.id == candidate_item_id).first()
    if candidate is None:
        return AxisScore(
            axis=DecisionAxis.REDUNDANCY,
            score=100.0,
            reason="Candidate item not found.",
            source_agent="duplicate_detection",
            raw_evidence={"duplicate_similarity_pct": None},
        )

    sim_pct = candidate.duplicate_similarity_pct

    if sim_pct is None or sim_pct <= 0:
        return AxisScore(
            axis=DecisionAxis.REDUNDANCY,
            score=100.0,
            reason="No close match in your current wardrobe.",
            source_agent="duplicate_detection",
            raw_evidence={
                "duplicate_similarity_pct": None,
                "duplicate_match_item_id": None,
            },
        )

    # Inverted polarity calculation: higher = more unique / less redundant
    uniqueness_score = round(max(0.0, min(100.0, 100.0 - float(sim_pct))), 1)

    if sim_pct >= 85.0:
        reason = f"{sim_pct}% similar to an item you already own — largely redundant."
    elif sim_pct >= 50.0:
        reason = f"{sim_pct}% similar to a item in your current wardrobe."
    else:
        reason = f"Low similarity ({sim_pct}%) to existing wardrobe items."

    return AxisScore(
        axis=DecisionAxis.REDUNDANCY,
        score=uniqueness_score,
        reason=reason,
        source_agent="duplicate_detection",
        raw_evidence={
            "duplicate_similarity_pct": float(sim_pct),
            "duplicate_match_item_id": candidate.duplicate_match_item_id,
        },
    )
