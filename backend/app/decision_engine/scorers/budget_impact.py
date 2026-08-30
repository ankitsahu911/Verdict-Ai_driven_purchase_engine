import logging
from sqlalchemy.orm import Session

from app.decision_engine.schema import AxisScore, DecisionAxis
from app.models import WardrobeItem
from app.services.economics_service import (
    calculate_cost_per_wear,
    calculate_return_risk,
    load_wear_baselines,
    normalize_category_key,
)

logger = logging.getLogger(__name__)

CPW_WEIGHT: float = 0.60
RETURN_RISK_WEIGHT: float = 0.40


def score_budget_impact(candidate_item_id: int, db: Session) -> AxisScore:
    candidate = db.query(WardrobeItem).filter(WardrobeItem.id == candidate_item_id).first()
    if candidate is None:
        return AxisScore(
            axis=DecisionAxis.BUDGET_IMPACT,
            score=50.0,
            reason="Candidate item not found.",
            source_agent="economics_agent",
            raw_evidence={"price": None},
        )

    raw_category = candidate.attributes.category if candidate.attributes else None
    cat_key = normalize_category_key(raw_category)
    baselines = load_wear_baselines()
    cat_data = baselines.get(cat_key, baselines.get("top", {}))
    cpw_ceiling = float(cat_data.get("typical_cost_per_wear_ceiling", 3.50))

    price = candidate.price
    if price is None or price <= 0:
        return AxisScore(
            axis=DecisionAxis.BUDGET_IMPACT,
            score=50.0,
            reason="Price not set for candidate item — baseline budget impact estimate.",
            source_agent="economics_agent",
            raw_evidence={
                "price": None,
                "category": cat_key,
                "cpw_ceiling": cpw_ceiling,
            },
        )

    cpw_result = calculate_cost_per_wear(category=raw_category, price=price)
    cpw = cpw_result["cost_per_wear"]
    baseline_wears = cpw_result["baseline_wears_used"]

    if cpw <= cpw_ceiling:
        cpw_score = 100.0
    else:
        overage_ratio = (cpw - cpw_ceiling) / cpw_ceiling
        cpw_score = max(0.0, round(100.0 - (overage_ratio * 100.0), 1))

    rr_result = calculate_return_risk(category=raw_category, fit_tightness=candidate.fit_tightness)
    return_risk_score = rr_result["return_risk_score"]
    inverted_return_risk = max(0.0, min(100.0, 100.0 - float(return_risk_score)))

    blended_score = round(
        (CPW_WEIGHT * cpw_score) + (RETURN_RISK_WEIGHT * inverted_return_risk),
        1,
    )
    final_score = max(0.0, min(100.0, blended_score))

    if cpw <= cpw_ceiling and return_risk_score <= 30:
        reason = (
            f"Efficient cost-per-wear (${cpw:.2f}/wear vs ${cpw_ceiling:.2f} ceiling) "
            f"for a {cat_key}, with low predicted return risk ({return_risk_score}%)."
        )
    elif cpw <= cpw_ceiling and return_risk_score > 30:
        reason = (
            f"Favorable cost-per-wear (${cpw:.2f}/wear) for a {cat_key}, "
            f"with moderate return risk ({return_risk_score}%)."
        )
    elif cpw > cpw_ceiling and return_risk_score <= 30:
        reason = (
            f"Elevated cost-per-wear (${cpw:.2f}/wear vs ${cpw_ceiling:.2f} ceiling) "
            f"for a {cat_key}, offset by low predicted return risk ({return_risk_score}%)."
        )
    else:
        reason = (
            f"High cost-per-wear (${cpw:.2f}/wear vs ${cpw_ceiling:.2f} ceiling) "
            f"for a {cat_key}, coupled with elevated return risk ({return_risk_score}%)."
        )

    return AxisScore(
        axis=DecisionAxis.BUDGET_IMPACT,
        score=final_score,
        reason=reason,
        source_agent="economics_agent",
        raw_evidence={
            "price": price,
            "cost_per_wear": cpw,
            "cpw_ceiling": cpw_ceiling,
            "cpw_score": cpw_score,
            "baseline_wears_used": baseline_wears,
            "return_risk_score": return_risk_score,
            "inverted_return_risk": inverted_return_risk,
            "cpw_weight": CPW_WEIGHT,
            "return_risk_weight": RETURN_RISK_WEIGHT,
        },
    )
