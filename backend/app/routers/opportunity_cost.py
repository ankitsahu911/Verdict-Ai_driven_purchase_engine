import logging
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.decision_engine.orchestrator import synthesize_buy_score
from app.decision_engine.schema import BuyScoreResult, DecisionAxis
from app.decision_engine.subset_evaluator import evaluate_subset
from app.models import WardrobeItem
from app.routers.wardrobe import get_or_create_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/opportunity-cost", tags=["opportunity-cost"])


class OpportunityCostCompareRequest(BaseModel):
    candidate_item_id: int = Field(
        ...,
        description="The primary candidate item ID being evaluated",
    )
    alternative_item_ids: List[int] = Field(
        ...,
        description="List of 2 alternative candidate item IDs to form the comparison bundle",
    )


class OpportunityCostCompareResponse(BaseModel):
    candidate: BuyScoreResult
    alternative_bundle: Any
    candidate_versatility: float
    alternative_bundle_versatility: float
    versatility_delta: float
    candidate_outfit_count: int
    alternative_bundle_outfit_count: int
    outfit_count_delta: int
    candidate_name: str
    alternative_names: List[str]


def _format_item_name(item: WardrobeItem | None, default_id: int) -> str:
    if not item:
        return f"Item #{default_id}"
    if item.attributes:
        color = item.attributes.color or ""
        category = item.attributes.category or "garment"
        name = f"{color} {category}".strip()
        return name.title() if name else f"Item #{item.id}"
    return f"Item #{item.id}"


@router.post("/compare", response_model=OpportunityCostCompareResponse)
async def compare_opportunity_cost(
    payload: OpportunityCostCompareRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owner = get_or_create_user(db, user["uid"], user["email"])
    candidate_id = payload.candidate_item_id
    alt_ids = payload.alternative_item_ids

    # Deduplicate alternative IDs
    unique_alt_ids: list[int] = []
    for i in alt_ids:
        if i not in unique_alt_ids:
            unique_alt_ids.append(i)

    if len(unique_alt_ids) != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Opportunity Cost comparison requires exactly 2 unique alternative candidate items.",
        )

    all_ids = [candidate_id] + unique_alt_ids

    # Ownership check: verify all requested items exist and belong to the authenticated caller
    items = (
        db.query(WardrobeItem)
        .filter(WardrobeItem.id.in_(all_ids))
        .all()
    )
    found_ids = {item.id for item in items}
    missing_ids = set(all_ids) - found_ids
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item(s) not found: {sorted(list(missing_ids))}",
        )

    for item in items:
        if item.user_id != owner.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have access to item #{item.id}",
            )

    items_map = {item.id: item for item in items}
    candidate_item = items_map.get(candidate_id)
    alt_items = [items_map.get(aid) for aid in unique_alt_ids]

    candidate_name = _format_item_name(candidate_item, candidate_id)
    alternative_names = [
        _format_item_name(aitem, aid)
        for aitem, aid in zip(alt_items, unique_alt_ids)
    ]

    # 1. Compute single candidate Buy Score via M23 orchestrator
    candidate_buy_score = synthesize_buy_score(
        candidate_item_id=candidate_id,
        db=db,
        persist=False,
    )

    # 2. Compute alternative bundle score via M26 set evaluator
    alternative_bundle_score = evaluate_subset(
        subset_item_ids=unique_alt_ids,
        db=db,
    )

    # 3. Extract versatility scores and raw outfit combination counts
    candidate_versatility = 0.0
    candidate_outfit_count = 0
    for ax in candidate_buy_score.axes:
        if ax.axis == DecisionAxis.VERSATILITY or str(ax.axis) == "versatility":
            candidate_versatility = ax.score
            if ax.raw_evidence and isinstance(ax.raw_evidence, dict):
                candidate_outfit_count = int(ax.raw_evidence.get("combinations_count", 0))
            break

    alt_versatility = 0.0
    alternative_bundle_outfit_count = 0
    for ax in alternative_bundle_score.get("axes", []):
        if ax.get("axis") == "versatility" or ax.get("axis") == DecisionAxis.VERSATILITY:
            alt_versatility = float(ax.get("score", 0.0))
            raw_ev = ax.get("raw_evidence", {})
            if isinstance(raw_ev, dict):
                alternative_bundle_outfit_count = int(raw_ev.get("total_outfits_count", 0))
            break

    # 4. Compute versatility and outfit count deltas
    versatility_delta = round(alt_versatility - candidate_versatility, 1)
    outfit_count_delta = alternative_bundle_outfit_count - candidate_outfit_count

    logger.info(
        "Opportunity Cost comparison for user_id=%s: Candidate '%s' (#%d: score=%.1f, vers=%.1f, outfits=%d) vs Alternative Bundle %s (#%s: score=%.1f, vers=%.1f, outfits=%d) -> Versatility Delta=%.1f, Outfit Delta=%d",
        owner.id,
        candidate_name,
        candidate_id,
        candidate_buy_score.overall_score,
        candidate_versatility,
        candidate_outfit_count,
        alternative_names,
        unique_alt_ids,
        alternative_bundle_score.get("overall_score", 0.0),
        alt_versatility,
        alternative_bundle_outfit_count,
        versatility_delta,
        outfit_count_delta,
    )

    return OpportunityCostCompareResponse(
        candidate=candidate_buy_score,
        alternative_bundle=alternative_bundle_score,
        candidate_versatility=candidate_versatility,
        alternative_bundle_versatility=alt_versatility,
        versatility_delta=versatility_delta,
        candidate_outfit_count=candidate_outfit_count,
        alternative_bundle_outfit_count=alternative_bundle_outfit_count,
        outfit_count_delta=outfit_count_delta,
        candidate_name=candidate_name,
        alternative_names=alternative_names,
    )
