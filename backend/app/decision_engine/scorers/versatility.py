import logging
from sqlalchemy.orm import Session

from app.decision_engine.schema import AxisScore, DecisionAxis
from app.models import WardrobeItem
from app.services.outfit_service import build_ranked_outfit_combinations

logger = logging.getLogger(__name__)

MAX_VERSATILITY_CAP = 5.0


def score_versatility(candidate_item_id: int, db: Session) -> AxisScore:
    candidate = db.query(WardrobeItem).filter(WardrobeItem.id == candidate_item_id).first()
    if candidate is None:
        return AxisScore(
            axis=DecisionAxis.VERSATILITY,
            score=0.0,
            reason="Candidate item not found.",
            source_agent="outfit_composition",
            raw_evidence={"combinations_count": 0},
        )

    attrs = candidate.attributes
    candidate_dict = {
        "wardrobe_item_id": candidate.id,
        "cloudinary_url": candidate.cloudinary_url,
        "attributes": (
            {
                "category": attrs.category,
                "color": attrs.color,
                "pattern": attrs.pattern,
                "style": attrs.style,
                "season": attrs.season,
                "material": attrs.material,
            }
            if attrs
            else {}
        ),
    }

    existing_items = (
        db.query(WardrobeItem)
        .filter(
            WardrobeItem.user_id == candidate.user_id,
            WardrobeItem.is_candidate == False,
            WardrobeItem.id != candidate_item_id,
        )
        .all()
    )

    combinations = build_ranked_outfit_combinations(
        candidate_item=candidate_dict,
        wardrobe_items=existing_items,
        top_n=5,
    )

    count = len(combinations)
    norm_score = round(min(100.0, (count / MAX_VERSATILITY_CAP) * 100.0), 1)

    if count == 0:
        if not existing_items:
            reason = "Does not pair into complete outfits — no compatible items found yet — upload some wardrobe items first."
        else:
            reason = "Does not pair into complete outfits with your current wardrobe items."
    elif count == 1:
        reason = "Pairs into 1 complete outfit with items you already own."
    else:
        reason = f"Pairs into {count} complete outfits with items you already own."

    return AxisScore(
        axis=DecisionAxis.VERSATILITY,
        score=norm_score,
        reason=reason,
        source_agent="outfit_composition",
        raw_evidence={
            "combinations_count": count,
            "max_cap_used": MAX_VERSATILITY_CAP,
            "top_outfit_score": combinations[0]["total_score"] if combinations else None,
        },
    )
