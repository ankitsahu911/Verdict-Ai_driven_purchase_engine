"""
Occasion Coverage Axis Scorer (MILESTONE 22).

Evaluates whether a candidate garment fills an occasion coverage gap in the user's
wardrobe by rewarding styles/occasions that are rare or underrepresented.

Source Agent: occasion_analysis
"""

import logging
from sqlalchemy.orm import Session

from app.decision_engine.schema import AxisScore, DecisionAxis
from app.decision_engine.scorers.style_distribution import get_wardrobe_style_distribution
from app.models import WardrobeItem

logger = logging.getLogger(__name__)


def score_occasion_coverage(candidate_item_id: int, db: Session) -> AxisScore:
    """Evaluate occasion coverage score for a candidate wardrobe item.

    Args:
        candidate_item_id: Database primary key of candidate WardrobeItem.
        db: Active SQLAlchemy database session.

    Returns:
        AxisScore conforming to the Milestone 19 schema.
    """
    candidate = db.query(WardrobeItem).filter(WardrobeItem.id == candidate_item_id).first()
    if candidate is None:
        return AxisScore(
            axis=DecisionAxis.OCCASION_COVERAGE,
            score=50.0,
            reason="Candidate item not found.",
            source_agent="occasion_analysis",
            raw_evidence={"candidate_style_occasion": None},
        )

    raw_style = (
        candidate.attributes.style.strip().lower()
        if candidate.attributes and candidate.attributes.style
        else "casual"
    )

    distribution = get_wardrobe_style_distribution(
        user_id=candidate.user_id,
        db=db,
        exclude_item_id=candidate_item_id,
    )

    # Empty wardrobe fallback: neutral score
    if not distribution:
        return AxisScore(
            axis=DecisionAxis.OCCASION_COVERAGE,
            score=50.0,
            reason="No existing wardrobe items to evaluate occasion coverage gaps — default baseline coverage.",
            source_agent="occasion_analysis",
            raw_evidence={
                "candidate_style_occasion": raw_style,
                "wardrobe_style_percentage": None,
                "distribution": {},
            },
        )

    style_pct = distribution.get(raw_style, 0.0)
    gap_score = round(max(0.0, min(100.0, 100.0 - style_pct)), 1)

    if style_pct <= 10.0:
        reason = f"Only {style_pct:.1f}% of your wardrobe is {raw_style} — this fills a real occasion coverage gap."
    elif style_pct <= 35.0:
        reason = f"{style_pct:.1f}% of your wardrobe is {raw_style} — expands your occasion coverage."
    else:
        reason = f"{style_pct:.1f}% of your wardrobe is already {raw_style} — adds little new occasion coverage."

    return AxisScore(
        axis=DecisionAxis.OCCASION_COVERAGE,
        score=gap_score,
        reason=reason,
        source_agent="occasion_analysis",
        raw_evidence={
            "candidate_style_occasion": raw_style,
            "wardrobe_style_percentage": style_pct,
            "gap_score": gap_score,
            "distribution": distribution,
        },
    )
