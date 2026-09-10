import logging
from sqlalchemy.orm import Session

from app.decision_engine.schema import AxisScore, DecisionAxis
from app.models import WardrobeItem

logger = logging.getLogger(__name__)


def score_redundancy(candidate_item_id: int, db: Session) -> AxisScore:
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
            reason="No close match in your current wardrobe (100/100 uniqueness — completely fresh addition).",
            source_agent="duplicate_detection",
            raw_evidence={
                "duplicate_similarity_pct": None,
                "duplicate_match_item_id": None,
            },
        )

    uniqueness_score = round(max(0.0, min(100.0, 100.0 - float(sim_pct))), 1)

    if sim_pct >= 85.0:
        reason = (
            f"{sim_pct:.1f}% similar to an item you already own — largely redundant "
            f"({uniqueness_score:.0f}/100 uniqueness, 100 minus duplicate overlap)."
        )
    elif sim_pct >= 45.0:
        reason = (
            f"{sim_pct:.1f}% similar to an item in your current wardrobe — moderate overlap "
            f"({uniqueness_score:.0f}/100 uniqueness)."
        )
    else:
        reason = (
            f"Low duplicate overlap ({sim_pct:.1f}%) with existing wardrobe items — "
            f"high uniqueness ({uniqueness_score:.0f}/100)."
        )

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
