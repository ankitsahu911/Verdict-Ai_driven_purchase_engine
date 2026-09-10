import logging
import math
from typing import Any, List, Sequence

from app.decision_engine.schema import AxisScore, ConfidenceResult

logger = logging.getLogger(__name__)

# Named decision thresholds (reused from M23)
BUY_THRESHOLD = 70.0
CONSIDER_THRESHOLD = 45.0

# Named proximity boundaries
PROXIMITY_MARGIN = 8.0
HIGH_PROXIMITY_MARGIN = 4.0

# Named axis variance boundaries
HIGH_VARIANCE_RANGE = 45.0
MODERATE_VARIANCE_RANGE = 30.0

# Named config list of commonly ambiguous styles/categories
AMBIGUOUS_STYLES = {
    "smart-casual",
    "smart casual",
    "business casual",
    "athleisure",
    "semi-formal",
}

# Confidence levels
CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"


def evaluate_threshold_proximity(overall_score: float) -> tuple[int, str | None, dict[str, Any]]:
    dist_to_buy = abs(overall_score - BUY_THRESHOLD)
    dist_to_consider = abs(overall_score - CONSIDER_THRESHOLD)

    if dist_to_buy <= dist_to_consider:
        nearest_threshold = "Buy"
        nearest_val = BUY_THRESHOLD
        min_dist = dist_to_buy
    else:
        nearest_threshold = "Skip"
        nearest_val = CONSIDER_THRESHOLD
        min_dist = dist_to_consider

    if min_dist <= HIGH_PROXIMITY_MARGIN:
        penalty = 2
        reason = (
            f"Overall score ({overall_score:.1f}) sits very close ({min_dist:.1f} points) "
            f"to the {nearest_threshold} threshold ({nearest_val:.0f})"
        )
    elif min_dist <= PROXIMITY_MARGIN:
        penalty = 1
        reason = (
            f"Overall score ({overall_score:.1f}) is near ({min_dist:.1f} points) "
            f"the {nearest_threshold} threshold ({nearest_val:.0f})"
        )
    else:
        penalty = 0
        reason = None

    return penalty, reason, {
        "min_distance_to_threshold": round(min_dist, 1),
        "nearest_threshold": nearest_threshold,
        "nearest_threshold_value": nearest_val,
    }


def evaluate_axis_variance(axis_scores: Sequence[AxisScore | float]) -> tuple[int, str | None, dict[str, Any]]:
    raw_scores: list[float] = []
    for a in axis_scores:
        if isinstance(a, (int, float)):
            raw_scores.append(float(a))
        elif hasattr(a, "score"):
            raw_scores.append(float(a.score))

    if not raw_scores:
        return 0, None, {"score_range": 0.0, "std_dev": 0.0}

    score_range = max(raw_scores) - min(raw_scores)
    mean_val = sum(raw_scores) / len(raw_scores)
    variance = sum((s - mean_val) ** 2 for s in raw_scores) / len(raw_scores)
    std_dev = math.sqrt(variance)

    if score_range >= HIGH_VARIANCE_RANGE:
        penalty = 2
        reason = (
            f"Decision axes exhibit high disagreement with a {score_range:.0f}-point "
            f"spread between highest and lowest scoring criteria"
        )
    elif score_range >= MODERATE_VARIANCE_RANGE:
        penalty = 1
        reason = (
            f"Decision axes show moderate variance with a {score_range:.0f}-point "
            f"spread across criteria"
        )
    else:
        penalty = 0
        reason = None

    return penalty, reason, {
        "score_range": round(score_range, 1),
        "std_dev": round(std_dev, 1),
        "min_axis_score": round(min(raw_scores), 1),
        "max_axis_score": round(max(raw_scores), 1),
    }


def evaluate_category_ambiguity(style: str | None) -> tuple[int, str | None, dict[str, Any]]:
    if not style:
        return 0, None, {"style": None, "is_ambiguous": False}

    cleaned_style = style.strip().lower()
    is_ambiguous = cleaned_style in AMBIGUOUS_STYLES

    if is_ambiguous:
        penalty = 1
        reason = f"'{style}' is a commonly ambiguous category boundary"
    else:
        penalty = 0
        reason = None

    return penalty, reason, {
        "style": style,
        "is_ambiguous": is_ambiguous,
    }


def calculate_confidence(
    overall_score: float,
    axis_scores: Sequence[AxisScore | float],
    style: str | None,
) -> ConfidenceResult:
    prox_penalty, prox_reason, prox_data = evaluate_threshold_proximity(overall_score)
    var_penalty, var_reason, var_data = evaluate_axis_variance(axis_scores)
    cat_penalty, cat_reason, cat_data = evaluate_category_ambiguity(style)

    total_penalty = prox_penalty + var_penalty + cat_penalty

    # Determine confidence level
    if total_penalty >= 3:
        level = CONFIDENCE_LOW
    elif total_penalty >= 1:
        level = CONFIDENCE_MEDIUM
    else:
        level = CONFIDENCE_HIGH

    # Build templated reasoning from triggered signals
    triggered_reasons = [r for r in [prox_reason, var_reason, cat_reason] if r is not None]

    if not triggered_reasons:
        reasoning = (
            "High confidence: decisive overall score far from thresholds, "
            "strong consensus across decision axes, and unambiguous category classification."
        )
    else:
        joined_signals = ", and ".join(triggered_reasons)
        prefix = level.capitalize() + " confidence: "
        reasoning = prefix + joined_signals + "."

    signals_payload = {
        "proximity": prox_data,
        "variance": var_data,
        "category": cat_data,
        "total_penalty": total_penalty,
    }

    return ConfidenceResult(
        level=level,
        reasoning=reasoning,
        signals=signals_payload,
    )
