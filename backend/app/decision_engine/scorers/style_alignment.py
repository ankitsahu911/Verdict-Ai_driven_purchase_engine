"""
Style Alignment Axis Scorer (MILESTONE 22).

Evaluates how well a candidate garment aligns with the user's established personal
style by checking the representation percentage of that style in their current wardrobe.

Source Agent: style_analysis
"""

import logging
from sqlalchemy.orm import Session

from app.decision_engine.schema import AxisScore, DecisionAxis
from app.decision_engine.scorers.style_distribution import get_wardrobe_style_distribution
from app.models import WardrobeItem

logger = logging.getLogger(__name__)


def score_style_alignment(candidate_item_id: int, db: Session) -> AxisScore:
    """Evaluate style alignment score for a candidate wardrobe item.

    Args:
        candidate_item_id: Database primary key of candidate WardrobeItem.
        db: Active SQLAlchemy database session.

    Returns:
        AxisScore conforming to the Milestone 19 schema.
    """
    candidate = db.query(WardrobeItem).filter(WardrobeItem.id == candidate_item_id).first()
    if candidate is None:
        return AxisScore(
            axis=DecisionAxis.STYLE_ALIGNMENT,
            score=50.0,
            reason="Candidate item not found.",
            source_agent="style_analysis",
            raw_evidence={"candidate_style": None},
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
            axis=DecisionAxis.STYLE_ALIGNMENT,
            score=50.0,
            reason="No existing wardrobe items to compare style distribution — default baseline alignment.",
            source_agent="style_analysis",
            raw_evidence={
                "candidate_style": raw_style,
                "wardrobe_style_percentage": None,
                "distribution": {},
            },
        )

    style_pct = distribution.get(raw_style, 0.0)
    score = round(max(0.0, min(100.0, style_pct)), 1)

    if style_pct >= 40.0:
        reason = f"{style_pct:.1f}% of your wardrobe is already {raw_style} — this fits your established personal style."
    elif style_pct > 0.0:
        reason = f"{style_pct:.1f}% of your wardrobe is {raw_style} — moderately aligns with your current style."
    else:
        reason = f"None of your current wardrobe is {raw_style} — low alignment with your established style."

    return AxisScore(
        axis=DecisionAxis.STYLE_ALIGNMENT,
        score=score,
        reason=reason,
        source_agent="style_analysis",
        raw_evidence={
            "candidate_style": raw_style,
            "wardrobe_style_percentage": style_pct,
            "distribution": distribution,
        },
    )
