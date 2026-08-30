import calendar
from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session

from app.decision_engine.schema import AxisScore, DecisionAxis
from app.models import WardrobeItem

logger = logging.getLogger(__name__)

SEASON_MONTHS: dict[str, set[int]] = {
    "spring": {3, 4, 5},
    "summer": {6, 7, 8},
    "fall": {9, 10, 11},
    "autumn": {9, 10, 11},
    "winter": {12, 1, 2},
    "all-season": set(range(1, 13)),
    "all season": set(range(1, 13)),
    "year-round": set(range(1, 13)),
}


def calculate_month_distance(current_month: int, target_months: set[int]) -> int:
    if current_month in target_months:
        return 0

    min_dist = 12
    for tm in target_months:
        direct = abs(current_month - tm)
        circular = 12 - direct
        dist = min(direct, circular)
        if dist < min_dist:
            min_dist = dist
    return min_dist


def score_seasonal_relevance(
    candidate_item_id: int,
    db: Session,
    current_month: int | None = None,
) -> AxisScore:
    candidate = db.query(WardrobeItem).filter(WardrobeItem.id == candidate_item_id).first()
    if candidate is None:
        return AxisScore(
            axis=DecisionAxis.SEASONAL_RELEVANCE,
            score=50.0,
            reason="Candidate item not found.",
            source_agent="vision_agent",
            raw_evidence={"season": None},
        )

    ref_month = current_month or datetime.now(timezone.utc).month
    month_name = calendar.month_name[ref_month]

    raw_season = (
        candidate.attributes.season.strip().lower()
        if candidate.attributes and candidate.attributes.season
        else None
    )

    if not raw_season or raw_season in {"all-season", "all season", "year-round", "any"}:
        return AxisScore(
            axis=DecisionAxis.SEASONAL_RELEVANCE,
            score=95.0,
            reason="All-season versatile item — wearable year-round regardless of calendar.",
            source_agent="vision_agent",
            raw_evidence={
                "season": raw_season or "all-season",
                "current_month": ref_month,
                "current_month_name": month_name,
                "month_distance": 0,
            },
        )

    target_months = SEASON_MONTHS.get(raw_season)
    if not target_months:
        return AxisScore(
            axis=DecisionAxis.SEASONAL_RELEVANCE,
            score=70.0,
            reason=f"Season tagged as '{raw_season}' — moderate baseline seasonal relevance.",
            source_agent="vision_agent",
            raw_evidence={"season": raw_season, "current_month": ref_month},
        )

    dist = calculate_month_distance(ref_month, target_months)
    cap_season = raw_season.capitalize()

    if dist == 0:
        score = 100.0
        reason = f"{cap_season} item, currently in season ({month_name}) — immediately wearable."
    elif dist == 1:
        score = 80.0
        reason = f"{cap_season} item, currently {month_name} (1 month away) — ready for the upcoming season."
    elif dist == 2:
        score = 60.0
        reason = f"{cap_season} item, and it's currently {month_name} (2 months away) — useful within the next couple months."
    elif dist == 3:
        score = 40.0
        reason = f"{cap_season} item, currently {month_name} (3 months away) — approaching season."
    else:
        score = 20.0
        reason = f"{cap_season} item, and it's currently {month_name} ({dist} months away) — off-season, you'd be waiting months to wear it."

    return AxisScore(
        axis=DecisionAxis.SEASONAL_RELEVANCE,
        score=score,
        reason=reason,
        source_agent="vision_agent",
        raw_evidence={
            "season": raw_season,
            "current_month": ref_month,
            "current_month_name": month_name,
            "month_distance": dist,
        },
    )
