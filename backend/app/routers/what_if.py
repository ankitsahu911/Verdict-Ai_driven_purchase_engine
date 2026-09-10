import itertools
import logging
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.decision_engine.schema import ConfidenceResult
from app.decision_engine.subset_evaluator import evaluate_and_rank_subsets
from app.models import WardrobeItem
from app.routers.wardrobe import get_or_create_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/what-if", tags=["what-if"])

MIN_ITEMS = 3
MAX_ITEMS = 5


class EnumerateSubsetsRequest(BaseModel):
    item_ids: List[int] = Field(
        ...,
        description="List of 3 to 5 candidate wardrobe item IDs to enumerate",
    )


class SubsetRecord(BaseModel):
    subset_id: str
    size: int
    item_ids: List[int]


class EnumerateSubsetsResponse(BaseModel):
    total_items: int
    total_subsets: int
    subsets: List[SubsetRecord]


class AxisScoreRecord(BaseModel):
    axis: str
    score: float
    reason: str
    source_agent: str
    raw_evidence: Any | None = None


class ScoredSubsetRecord(BaseModel):
    subset_id: str
    rank: int
    size: int
    item_ids: List[int]
    verdict: str
    overall_score: float
    headline_reason: str
    axes: List[AxisScoreRecord]
    total_price: float = 0.0
    confidence: ConfidenceResult | None = None
    summary_panel: dict[str, Any] | None = None


class ScoreSubsetsResponse(BaseModel):
    total_items: int
    total_subsets: int
    top_recommendation: ScoredSubsetRecord
    subsets: List[ScoredSubsetRecord]


def enumerate_subsets(item_ids: list[int]) -> list[list[int]]:
    subsets: list[list[int]] = []
    n = len(item_ids)
    for r in range(n + 1):
        for combo in itertools.combinations(item_ids, r):
            subsets.append(list(combo))
    return subsets


@router.post("/enumerate", response_model=EnumerateSubsetsResponse)
async def enumerate_candidate_subsets(
    payload: EnumerateSubsetsRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owner = get_or_create_user(db, user["uid"], user["email"])
    raw_ids = payload.item_ids

    unique_ids: list[int] = []
    for item_id in raw_ids:
        if item_id not in unique_ids:
            unique_ids.append(item_id)

    num_items = len(unique_ids)
    if num_items == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Cart-level reasoning does not apply to a single item. "
                f"What-If enumeration requires between {MIN_ITEMS} and {MAX_ITEMS} items — "
                "please use the single-item Buy Score evaluation flow instead."
            ),
        )
    if num_items > MAX_ITEMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"What-If enumeration requires between {MIN_ITEMS} and {MAX_ITEMS} items. "
                f"You submitted {num_items} items — please select between {MIN_ITEMS} and {MAX_ITEMS} items to rank. "
                "Combinatorial search space grows exponentially (2^N subsets) and becomes too slow and cognitively overwhelming."
            ),
        )
    if num_items < MIN_ITEMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"What-If enumeration requires between {MIN_ITEMS} and {MAX_ITEMS} "
                f"items. Received {num_items} unique item(s)."
            ),
        )

    items = (
        db.query(WardrobeItem)
        .filter(WardrobeItem.id.in_(unique_ids))
        .all()
    )
    found_ids = {item.id for item in items}
    missing_ids = set(unique_ids) - found_ids
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate item(s) not found: {sorted(list(missing_ids))}",
        )

    for item in items:
        if item.user_id != owner.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have access to item #{item.id}",
            )

    raw_subsets = enumerate_subsets(unique_ids)
    total_subsets = len(raw_subsets)

    logger.info(
        "What-If Enumeration for user_id=%s: %d items -> %d subsets (2^%d)",
        owner.id,
        num_items,
        total_subsets,
        num_items,
    )

    records: list[SubsetRecord] = []
    for idx, subset in enumerate(raw_subsets, start=1):
        subset_id = f"subset_{idx}"
        size = len(subset)
        records.append(
            SubsetRecord(
                subset_id=subset_id,
                size=size,
                item_ids=subset,
            )
        )

    return EnumerateSubsetsResponse(
        total_items=num_items,
        total_subsets=total_subsets,
        subsets=records,
    )


@router.post("/score", response_model=ScoreSubsetsResponse)
async def score_candidate_subsets(
    payload: EnumerateSubsetsRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owner = get_or_create_user(db, user["uid"], user["email"])
    raw_ids = payload.item_ids

    unique_ids: list[int] = []
    for item_id in raw_ids:
        if item_id not in unique_ids:
            unique_ids.append(item_id)

    num_items = len(unique_ids)
    if num_items == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Cart-level reasoning does not apply to a single item. "
                f"What-If scoring requires between {MIN_ITEMS} and {MAX_ITEMS} items — "
                "please use the single-item Buy Score evaluation flow instead."
            ),
        )
    if num_items > MAX_ITEMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"What-If scoring requires between {MIN_ITEMS} and {MAX_ITEMS} items. "
                f"You submitted {num_items} items — please select between {MIN_ITEMS} and {MAX_ITEMS} items to rank. "
                "Combinatorial search space grows exponentially (2^N subsets) and becomes too slow and cognitively overwhelming."
            ),
        )
    if num_items < MIN_ITEMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"What-If scoring requires between {MIN_ITEMS} and {MAX_ITEMS} "
                f"items. Received {num_items} unique item(s)."
            ),
        )

    items = (
        db.query(WardrobeItem)
        .filter(WardrobeItem.id.in_(unique_ids))
        .all()
    )
    found_ids = {item.id for item in items}
    missing_ids = set(unique_ids) - found_ids
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate item(s) not found: {sorted(list(missing_ids))}",
        )

    for item in items:
        if item.user_id != owner.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have access to item #{item.id}",
            )

    ranked_subsets = evaluate_and_rank_subsets(unique_ids, db)
    total_subsets = len(ranked_subsets)

    top_subset = ranked_subsets[0]

    logger.info(
        "What-If Scoring completed for user_id=%s: %d items -> %d ranked subsets. Top recommendation: %s (score=%.1f, items=%s)",
        owner.id,
        num_items,
        total_subsets,
        top_subset["subset_id"],
        top_subset["overall_score"],
        top_subset["item_ids"],
    )

    return ScoreSubsetsResponse(
        total_items=num_items,
        total_subsets=total_subsets,
        top_recommendation=ScoredSubsetRecord(**top_subset),
        subsets=[ScoredSubsetRecord(**s) for s in ranked_subsets],
    )
