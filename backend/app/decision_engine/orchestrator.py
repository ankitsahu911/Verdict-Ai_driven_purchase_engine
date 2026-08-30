from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session

from app.decision_engine.schema import AxisScore, BuyScoreResult, DecisionAxis
from app.decision_engine.scorers import (
    score_budget_impact,
    score_occasion_coverage,
    score_redundancy,
    score_seasonal_relevance,
    score_style_alignment,
    score_versatility,
)
from app.models import Decision, DecisionLog, WardrobeItem

logger = logging.getLogger(__name__)

DEFAULT_AXIS_WEIGHTS: dict[DecisionAxis, float] = {
    DecisionAxis.VERSATILITY: 1.0 / 6.0,
    DecisionAxis.REDUNDANCY: 1.0 / 6.0,
    DecisionAxis.SEASONAL_RELEVANCE: 1.0 / 6.0,
    DecisionAxis.BUDGET_IMPACT: 1.0 / 6.0,
    DecisionAxis.STYLE_ALIGNMENT: 1.0 / 6.0,
    DecisionAxis.OCCASION_COVERAGE: 1.0 / 6.0,
}

BUY_THRESHOLD: float = 70.0
CONSIDER_THRESHOLD: float = 45.0


def map_score_to_verdict(score: float) -> str:
    if score >= BUY_THRESHOLD:
        return Decision.BUY.value
    if score >= CONSIDER_THRESHOLD:
        return Decision.CONSIDER.value
    return Decision.SKIP.value


def build_headline_reason(
    verdict: str,
    axes: list[AxisScore],
) -> str:
    if not axes:
        return f"{verdict.upper()}: Baseline evaluation complete."

    best_axis = max(axes, key=lambda a: a.score)
    worst_axis = min(axes, key=lambda a: a.score)
    verdict_label = verdict.upper()

    if worst_axis.score < 40.0 and worst_axis.axis != best_axis.axis:
        return f"{verdict_label}: {best_axis.reason} (Though note: {worst_axis.reason})"

    return f"{verdict_label}: {best_axis.reason}"


def synthesize_buy_score(
    candidate_item_id: int,
    db: Session,
    weights: dict[DecisionAxis, float] | None = None,
    persist: bool = True,
) -> BuyScoreResult:
    active_weights = weights or DEFAULT_AXIS_WEIGHTS

    axes: list[AxisScore] = [
        score_versatility(candidate_item_id, db),
        score_redundancy(candidate_item_id, db),
        score_seasonal_relevance(candidate_item_id, db),
        score_budget_impact(candidate_item_id, db),
        score_style_alignment(candidate_item_id, db),
        score_occasion_coverage(candidate_item_id, db),
    ]

    total_weight = sum(active_weights.get(a.axis, 0.0) for a in axes)
    if total_weight <= 0:
        total_weight = 1.0

    raw_weighted_score = sum(
        active_weights.get(a.axis, 0.0) * a.score for a in axes
    ) / total_weight

    overall_score = round(max(0.0, min(100.0, raw_weighted_score)), 1)
    verdict = map_score_to_verdict(overall_score)
    headline = build_headline_reason(verdict, axes)

    weights_used = {
        (a.value if hasattr(a, "value") else str(a)): round(w, 4)
        for a, w in active_weights.items()
    }

    now_iso = datetime.now(timezone.utc).isoformat()
    decision_log_id: int | None = None

    if persist:
        candidate = db.query(WardrobeItem).filter(WardrobeItem.id == candidate_item_id).first()
        if candidate:
            try:
                raw_payload = {
                    "candidate_id": candidate_item_id,
                    "overall_score": overall_score,
                    "verdict": verdict,
                    "headline_reason": headline,
                    "axes": [a.model_dump() for a in axes],
                    "weights_used": weights_used,
                }
                decision_enum = Decision(verdict)
                log_entry = DecisionLog(
                    user_id=candidate.user_id,
                    wardrobe_item_id=candidate.id,
                    decision=decision_enum,
                    buy_score=overall_score,
                    raw_payload=raw_payload,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(log_entry)
                db.commit()
                db.refresh(log_entry)
                decision_log_id = log_entry.id
            except Exception as e:
                logger.warning("Failed to persist DecisionLog for candidate %s: %s", candidate_item_id, e)

    return BuyScoreResult(
        candidate_id=candidate_item_id,
        verdict=verdict,
        overall_score=overall_score,
        headline_reason=headline,
        axes=axes,
        weights_used=weights_used,
        decision_log_id=decision_log_id,
        created_at=now_iso,
    )
