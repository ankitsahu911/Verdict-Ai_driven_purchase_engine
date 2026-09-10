import itertools
import logging
from typing import Any, List
from sqlalchemy.orm import Session

from app.decision_engine.confidence import AMBIGUOUS_STYLES, calculate_confidence
from app.decision_engine.orchestrator import (
    DEFAULT_AXIS_WEIGHTS,
    build_headline_reason,
    map_score_to_verdict,
)
from app.decision_engine.schema import AxisScore, DecisionAxis
from app.decision_engine.scorers import (
    score_budget_impact,
    score_occasion_coverage,
    score_redundancy,
    score_seasonal_relevance,
    score_style_alignment,
    score_versatility,
)
from app.models import WardrobeItem
from app.services.chroma_service import get_wardrobe_collection
from app.services.dashboard_service import assemble_subset_summary_panel
from app.services.outfit_service import (
    are_items_pairwise_compatible,
    normalize_category,
)

logger = logging.getLogger(__name__)

EMPTY_SUBSET_SCORE = 50.0


def score_subset_versatility(subset_item_ids: list[int], db: Session) -> AxisScore:
    if not subset_item_ids:
        return AxisScore(
            axis=DecisionAxis.VERSATILITY,
            score=EMPTY_SUBSET_SCORE,
            reason="Skip all: No new outfit combinations unlocked.",
            source_agent="outfit_composition",
            raw_evidence={"outfits_count": 0, "is_empty_subset": True},
        )

    candidate_items = (
        db.query(WardrobeItem)
        .filter(WardrobeItem.id.in_(subset_item_ids))
        .all()
    )

    if not candidate_items:
        return AxisScore(
            axis=DecisionAxis.VERSATILITY,
            score=0.0,
            reason="Candidate items not found.",
            source_agent="outfit_composition",
            raw_evidence={"outfits_count": 0},
        )

    owner_id = candidate_items[0].user_id
    existing_wardrobe = (
        db.query(WardrobeItem)
        .filter(
            WardrobeItem.user_id == owner_id,
            WardrobeItem.is_candidate == False,
        )
        .all()
    )

    serialized_candidates = [
        {
            "wardrobe_item_id": item.id,
            "cloudinary_url": item.cloudinary_url,
            "is_candidate": True,
            "attributes": (
                {
                    "category": item.attributes.category,
                    "color": item.attributes.color,
                    "pattern": item.attributes.pattern,
                    "style": item.attributes.style,
                    "season": item.attributes.season,
                    "material": item.attributes.material,
                }
                if item.attributes
                else {}
            ),
        }
        for item in candidate_items
    ]

    serialized_wardrobe = [
        {
            "wardrobe_item_id": item.id,
            "cloudinary_url": item.cloudinary_url,
            "is_candidate": False,
            "attributes": (
                {
                    "category": item.attributes.category,
                    "color": item.attributes.color,
                    "pattern": item.attributes.pattern,
                    "style": item.attributes.style,
                    "season": item.attributes.season,
                    "material": item.attributes.material,
                }
                if item.attributes
                else {}
            ),
        }
        for item in existing_wardrobe
    ]

    all_items = serialized_candidates + serialized_wardrobe
    candidate_id_set = set(subset_item_ids)

    by_category: dict[str, list[dict]] = {}
    for itm in all_items:
        cat = normalize_category(itm["attributes"].get("category"))
        by_category.setdefault(cat, []).append(itm)

    slot_templates = [
        ["top", "bottom", "footwear"],
        ["top", "bottom", "footwear", "outerwear"],
        ["dress", "footwear"],
        ["dress", "footwear", "outerwear"],
    ]

    valid_outfits: list[list[int]] = []
    synergy_count = 0

    for template in slot_templates:
        if not all(slot in by_category and len(by_category[slot]) > 0 for slot in template):
            continue

        slot_item_lists = [by_category[slot] for slot in template]
        for combo in itertools.product(*slot_item_lists):
            item_ids = [it["wardrobe_item_id"] for it in combo]

            # Outfit must use at least 1 candidate item from this subset
            candidate_items_used = [it for it in combo if it["wardrobe_item_id"] in candidate_id_set]
            if not candidate_items_used:
                continue

            # Check if all pairs in the outfit are compatible
            all_ok = True
            for i in range(len(combo)):
                for j in range(i + 1, len(combo)):
                    is_ok, _, _ = are_items_pairwise_compatible(combo[i], combo[j])
                    if not is_ok:
                        all_ok = False
                        break
                if not all_ok:
                    break

            if all_ok:
                valid_outfits.append(item_ids)
                if len(candidate_items_used) >= 2:
                    synergy_count += 1

    total_valid = len(valid_outfits)
    k = len(subset_item_ids)
    baseline_cap = float(3 * k + 2)
    raw_score = (total_valid / baseline_cap) * 100.0
    norm_score = round(max(0.0, min(100.0, raw_score)), 1)

    if total_valid == 0:
        if not existing_wardrobe:
            reason = "no compatible items found yet — upload some wardrobe items first"
        else:
            reason = "Subset items do not form complete outfits with each other or existing wardrobe."
    elif synergy_count > 0:
        reason = (
            f"High synergy: unlocks {total_valid} complete outfits, including "
            f"{synergy_count} paired directly across cart items."
        )
    else:
        reason = f"Unlocks {total_valid} complete outfit combinations with your existing wardrobe."

    return AxisScore(
        axis=DecisionAxis.VERSATILITY,
        score=norm_score,
        reason=reason,
        source_agent="outfit_composition",
        raw_evidence={
            "total_outfits_count": total_valid,
            "synergy_outfits_count": synergy_count,
            "subset_size": k,
        },
    )


def score_subset_redundancy(subset_item_ids: list[int], db: Session) -> AxisScore:
    if not subset_item_ids:
        return AxisScore(
            axis=DecisionAxis.REDUNDANCY,
            score=EMPTY_SUBSET_SCORE,
            reason="Skip all: No wardrobe additions or duplicates.",
            source_agent="duplicate_detection",
            raw_evidence={"is_empty_subset": True},
        )

    # 1. Wardrobe Redundancy: average of individual item redundancy scores vs existing wardrobe
    indiv_scores = [score_redundancy(item_id, db).score for item_id in subset_item_ids]
    wardrobe_uniqueness = sum(indiv_scores) / len(indiv_scores) if indiv_scores else 100.0

    # 2. Within-Subset Redundancy check: pairwise similarity between items inside this cart subset
    max_internal_similarity = 0.0
    worst_pair: tuple[int, int] | None = None

    if len(subset_item_ids) >= 2:
        # Check Chroma embeddings if available
        embeddings_by_id: dict[int, list[float]] = {}
        try:
            collection = get_wardrobe_collection()
            res = collection.get(
                ids=[str(i) for i in subset_item_ids],
                include=["embeddings"],
            )
            if res and res.get("ids") and res.get("embeddings"):
                for doc_id, emb in zip(res["ids"], res["embeddings"]):
                    try:
                        embeddings_by_id[int(doc_id)] = emb
                    except ValueError:
                        pass
        except Exception as e:
            logger.debug("Could not fetch Chroma embeddings for within-subset check: %s", e)

        # Pairwise check
        candidate_items = (
            db.query(WardrobeItem)
            .filter(WardrobeItem.id.in_(subset_item_ids))
            .all()
        )
        item_map = {item.id: item for item in candidate_items}

        for id1, id2 in itertools.combinations(subset_item_ids, 2):
            sim_pct = 0.0
            if id1 in embeddings_by_id and id2 in embeddings_by_id:
                emb1 = embeddings_by_id[id1]
                emb2 = embeddings_by_id[id2]
                # Cosine similarity for normalized CLIP embeddings
                dot_prod = sum(a * b for a, b in zip(emb1, emb2))
                sim_pct = max(0.0, min(100.0, dot_prod * 100.0))
            else:
                # Fallback attribute similarity
                item1 = item_map.get(id1)
                item2 = item_map.get(id2)
                if item1 and item2 and item1.attributes and item2.attributes:
                    a1, a2 = item1.attributes, item2.attributes
                    match_count = 0
                    if a1.category and a2.category and a1.category.lower() == a2.category.lower():
                        match_count += 3
                    if a1.color and a2.color and a1.color.lower() == a2.color.lower():
                        match_count += 2
                    if a1.style and a2.style and a1.style.lower() == a2.style.lower():
                        match_count += 1
                    sim_pct = min(100.0, match_count * 16.6)

            if sim_pct > max_internal_similarity:
                max_internal_similarity = sim_pct
                worst_pair = (id1, id2)

    internal_uniqueness = max(0.0, 100.0 - max_internal_similarity)

    # Blend wardrobe uniqueness (60%) and internal cart uniqueness (40%)
    if len(subset_item_ids) >= 2:
        final_score = round(0.6 * wardrobe_uniqueness + 0.4 * internal_uniqueness, 1)
    else:
        final_score = round(wardrobe_uniqueness, 1)

    if max_internal_similarity >= 75.0 and worst_pair:
        reason = (
            f"Within-cart redundancy: items #{worst_pair[0]} and #{worst_pair[1]} "
            f"are {max_internal_similarity:.1f}% similar to each other."
        )
    elif wardrobe_uniqueness < 40.0:
        reason = "Subset items are largely redundant with your existing wardrobe."
    elif final_score >= 80.0:
        reason = "High uniqueness: items add fresh distinct pieces without internal overlap."
    else:
        reason = f"Moderate uniqueness ({final_score}/100) across cart and wardrobe."

    return AxisScore(
        axis=DecisionAxis.REDUNDANCY,
        score=final_score,
        reason=reason,
        source_agent="duplicate_detection",
        raw_evidence={
            "wardrobe_uniqueness": round(wardrobe_uniqueness, 1),
            "internal_uniqueness": round(internal_uniqueness, 1),
            "max_internal_similarity": round(max_internal_similarity, 1),
            "worst_pair": list(worst_pair) if worst_pair else None,
        },
    )


def score_subset_seasonal_relevance(subset_item_ids: list[int], db: Session) -> AxisScore:
    if not subset_item_ids:
        return AxisScore(
            axis=DecisionAxis.SEASONAL_RELEVANCE,
            score=EMPTY_SUBSET_SCORE,
            reason="Skip all: Neutral seasonal posture.",
            source_agent="vision_agent",
            raw_evidence={"is_empty_subset": True},
        )

    scores = [score_seasonal_relevance(i, db).score for i in subset_item_ids]
    avg_score = round(sum(scores) / len(scores), 1)

    if avg_score >= 80.0:
        reason = "In-season items — immediately wearable for current weather."
    elif avg_score >= 50.0:
        reason = "Balanced seasonal utility across the selected items."
    else:
        reason = "Off-season items — will sit unworn until weather changes."

    return AxisScore(
        axis=DecisionAxis.SEASONAL_RELEVANCE,
        score=avg_score,
        reason=reason,
        source_agent="vision_agent",
        raw_evidence={"individual_scores": scores},
    )


def score_subset_budget_impact(subset_item_ids: list[int], db: Session) -> AxisScore:
    if not subset_item_ids:
        return AxisScore(
            axis=DecisionAxis.BUDGET_IMPACT,
            score=EMPTY_SUBSET_SCORE,
            reason="Skip all: Zero budget impact ($0 spend).",
            source_agent="economics_agent",
            raw_evidence={"is_empty_subset": True},
        )

    scores = [score_budget_impact(i, db).score for i in subset_item_ids]
    avg_score = round(sum(scores) / len(scores), 1)

    if avg_score >= 75.0:
        reason = "Strong value-for-money with efficient cost-per-wear and low return risk."
    elif avg_score >= 45.0:
        reason = "Moderate economics across the selected items."
    else:
        reason = "High cost-per-wear or elevated return risk across this set."

    return AxisScore(
        axis=DecisionAxis.BUDGET_IMPACT,
        score=avg_score,
        reason=reason,
        source_agent="economics_agent",
        raw_evidence={"individual_scores": scores},
    )


def score_subset_style_alignment(subset_item_ids: list[int], db: Session) -> AxisScore:
    if not subset_item_ids:
        return AxisScore(
            axis=DecisionAxis.STYLE_ALIGNMENT,
            score=EMPTY_SUBSET_SCORE,
            reason="Skip all: No change to personal style profile.",
            source_agent="style_analysis",
            raw_evidence={"is_empty_subset": True},
        )

    scores = [score_style_alignment(i, db).score for i in subset_item_ids]
    avg_score = round(sum(scores) / len(scores), 1)

    if avg_score >= 70.0:
        reason = "Fits your established personal wardrobe style profile."
    elif avg_score >= 45.0:
        reason = "Moderate aesthetic alignment with your current wardrobe."
    else:
        reason = "Low style cohesion with what you currently wear."

    return AxisScore(
        axis=DecisionAxis.STYLE_ALIGNMENT,
        score=avg_score,
        reason=reason,
        source_agent="style_analysis",
        raw_evidence={"individual_scores": scores},
    )


def score_subset_occasion_coverage(subset_item_ids: list[int], db: Session) -> AxisScore:
    if not subset_item_ids:
        return AxisScore(
            axis=DecisionAxis.OCCASION_COVERAGE,
            score=EMPTY_SUBSET_SCORE,
            reason="Skip all: No new occasion expansion.",
            source_agent="occasion_analysis",
            raw_evidence={"is_empty_subset": True},
        )

    scores = [score_occasion_coverage(i, db).score for i in subset_item_ids]
    avg_score = round(sum(scores) / len(scores), 1)

    if avg_score >= 60.0:
        reason = "Fills functional lifestyle gaps in your wardrobe."
    elif avg_score >= 35.0:
        reason = "Adds incremental occasion coverage."
    else:
        reason = "Duplicates existing occasion coverage."

    return AxisScore(
        axis=DecisionAxis.OCCASION_COVERAGE,
        score=avg_score,
        reason=reason,
        source_agent="occasion_analysis",
        raw_evidence={"individual_scores": scores},
    )


def evaluate_subset(
    subset_item_ids: list[int],
    db: Session,
    weights: dict[DecisionAxis, float] | None = None,
) -> dict[str, Any]:
    active_weights = weights or DEFAULT_AXIS_WEIGHTS

    # 1. Empty subset ("Skip all") -> Fixed 50.0 baseline
    if not subset_item_ids:
        axes = [
            AxisScore(
                axis=DecisionAxis.VERSATILITY,
                score=EMPTY_SUBSET_SCORE,
                reason="Skip all: Baseline neutral purchase posture.",
                source_agent="outfit_composition",
            ),
            AxisScore(
                axis=DecisionAxis.REDUNDANCY,
                score=EMPTY_SUBSET_SCORE,
                reason="Skip all: Baseline neutral purchase posture.",
                source_agent="duplicate_detection",
            ),
            AxisScore(
                axis=DecisionAxis.SEASONAL_RELEVANCE,
                score=EMPTY_SUBSET_SCORE,
                reason="Skip all: Baseline neutral purchase posture.",
                source_agent="vision_agent",
            ),
            AxisScore(
                axis=DecisionAxis.BUDGET_IMPACT,
                score=EMPTY_SUBSET_SCORE,
                reason="Skip all: Baseline neutral purchase posture.",
                source_agent="economics_agent",
            ),
            AxisScore(
                axis=DecisionAxis.STYLE_ALIGNMENT,
                score=EMPTY_SUBSET_SCORE,
                reason="Skip all: Baseline neutral purchase posture.",
                source_agent="style_analysis",
            ),
            AxisScore(
                axis=DecisionAxis.OCCASION_COVERAGE,
                score=EMPTY_SUBSET_SCORE,
                reason="Skip all: Baseline neutral purchase posture.",
                source_agent="occasion_analysis",
            ),
        ]

        confidence = calculate_confidence(
            overall_score=EMPTY_SUBSET_SCORE,
            axis_scores=axes,
            style=None,
        )
        summary_panel = assemble_subset_summary_panel([], db, axes)

        return {
            "size": 0,
            "item_ids": [],
            "overall_score": EMPTY_SUBSET_SCORE,
            "verdict": "consider",
            "headline_reason": "SKIP ALL: Baseline neutral score (no money spent, no wardrobe change).",
            "axes": [a.model_dump() for a in axes],
            "total_price": 0.0,
            "confidence": confidence.model_dump(),
            "summary_panel": summary_panel.model_dump(),
        }

    # 2. Non-empty subset: compute 6 set-level axes
    axes = [
        score_subset_versatility(subset_item_ids, db),
        score_subset_redundancy(subset_item_ids, db),
        score_subset_seasonal_relevance(subset_item_ids, db),
        score_subset_budget_impact(subset_item_ids, db),
        score_subset_style_alignment(subset_item_ids, db),
        score_subset_occasion_coverage(subset_item_ids, db),
    ]

    total_weight = sum(active_weights.get(a.axis, 0.0) for a in axes)
    if total_weight <= 0:
        total_weight = 1.0

    raw_weighted = sum(
        active_weights.get(a.axis, 0.0) * a.score for a in axes
    ) / total_weight

    overall_score = round(max(0.0, min(100.0, raw_weighted)), 1)
    verdict = map_score_to_verdict(overall_score)
    headline = build_headline_reason(verdict, axes)

    # Compute total subset price
    items = db.query(WardrobeItem).filter(WardrobeItem.id.in_(subset_item_ids)).all()
    total_price = sum(item.price for item in items if item.price is not None)

    # Determine representative style for confidence category heuristic
    representative_style: str | None = None
    for item in items:
        if item.attributes and item.attributes.style:
            if item.attributes.style.strip().lower() in AMBIGUOUS_STYLES:
                representative_style = item.attributes.style
                break
            elif representative_style is None:
                representative_style = item.attributes.style

    confidence = calculate_confidence(
        overall_score=overall_score,
        axis_scores=axes,
        style=representative_style,
    )
    summary_panel = assemble_subset_summary_panel(subset_item_ids, db, axes)

    return {
        "size": len(subset_item_ids),
        "item_ids": subset_item_ids,
        "overall_score": overall_score,
        "verdict": verdict,
        "headline_reason": headline,
        "axes": [a.model_dump() for a in axes],
        "total_price": round(total_price, 2),
        "confidence": confidence.model_dump(),
        "summary_panel": summary_panel.model_dump(),
    }


def evaluate_and_rank_subsets(
    item_ids: list[int],
    db: Session,
    weights: dict[DecisionAxis, float] | None = None,
) -> list[dict[str, Any]]:
    # Generate all 2^n subsets
    raw_subsets: list[list[int]] = []
    n = len(item_ids)
    for r in range(n + 1):
        for combo in itertools.combinations(item_ids, r):
            raw_subsets.append(list(combo))

    scored_results: list[dict[str, Any]] = []
    for idx, subset in enumerate(raw_subsets, start=1):
        eval_res = evaluate_subset(subset, db, weights=weights)
        eval_res["subset_id"] = f"subset_{idx}"
        scored_results.append(eval_res)

    # Rank descending by overall_score
    # Ties broken by: higher versatility, then smaller size
    scored_results.sort(
        key=lambda s: (
            s["overall_score"],
            next((a["score"] for a in s["axes"] if a["axis"] == "versatility"), 0),
            -s["size"],
        ),
        reverse=True,
    )

    # Assign rank (1-indexed)
    for rank, item in enumerate(scored_results, start=1):
        item["rank"] = rank

    return scored_results
