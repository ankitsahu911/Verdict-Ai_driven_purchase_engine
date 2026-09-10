import logging
from typing import Any, List, Sequence
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.decision_engine.schema import AxisScore, DecisionAxis
from app.decision_engine.scorers import (
    score_seasonal_relevance,
    score_versatility,
)
from app.models import WardrobeItem
from app.services.economics_service import calculate_cost_per_wear

logger = logging.getLogger(__name__)

# Static material-to-sustainability reference table (heuristic estimate)
SUSTAINABILITY_REFERENCE: dict[str, dict[str, str]] = {
    # Natural / lower impact fibers
    "cotton": {"tier": "Lower impact", "category": "Natural plant fiber"},
    "organic cotton": {"tier": "Lower impact", "category": "Organic natural fiber"},
    "linen": {"tier": "Lower impact", "category": "Natural flax fiber"},
    "wool": {"tier": "Lower impact", "category": "Natural animal fiber"},
    "merino": {"tier": "Lower impact", "category": "Natural merino wool"},
    "cashmere": {"tier": "Lower impact", "category": "Natural goat fiber"},
    "silk": {"tier": "Lower impact", "category": "Natural protein filament"},
    "hemp": {"tier": "Lower impact", "category": "Sustainable bast fiber"},
    "jute": {"tier": "Lower impact", "category": "Natural bast fiber"},
    "denim": {"tier": "Lower impact", "category": "Cotton-based weave"},
    "cotton twill": {"tier": "Lower impact", "category": "Cotton-based twill"},

    # Synthetic / higher impact fibers
    "polyester": {"tier": "Higher impact", "category": "Petroleum-derived synthetic"},
    "nylon": {"tier": "Higher impact", "category": "Petroleum-derived synthetic"},
    "acrylic": {"tier": "Higher impact", "category": "Synthetic polymer"},
    "spandex": {"tier": "Higher impact", "category": "Synthetic elastomeric fiber"},
    "elastane": {"tier": "Higher impact", "category": "Synthetic elastomeric fiber"},
    "polyurethane": {"tier": "Higher impact", "category": "Polyurethane synthetic"},
    "viscose": {"tier": "Higher impact", "category": "Chemically-processed semi-synthetic"},
    "rayon": {"tier": "Higher impact", "category": "Chemically-processed semi-synthetic"},
    "acetate": {"tier": "Higher impact", "category": "Cellulose acetate"},
    "fleece": {"tier": "Higher impact", "category": "Synthetic fleece knit"},
    "faux leather": {"tier": "Higher impact", "category": "Synthetic leather substitute"},
}


class DecisionSummaryMetrics(BaseModel):
    versatility: float = Field(..., description="0-100 versatility score")
    versatility_outfits_count: int = Field(default=0, description="Total outfits unlocked")
    duplicate_risk: float = Field(..., description="Original non-inverted duplicate similarity percentage (0-100%)")
    duplicate_risk_label: str = Field(..., description="Human-readable duplicate risk text")
    seasonality: float = Field(..., description="0-100 seasonal relevance score")
    seasonality_label: str = Field(..., description="Seasonality description")
    cost_per_wear: float = Field(..., description="Raw estimated cost per wear in currency units")
    cost_per_wear_formatted: str = Field(..., description="Formatted string (e.g. '$4.20 / wear')")
    sustainability_tier: str = Field(..., description="'Lower impact' | 'Higher impact' | 'Unrated'")
    sustainability_reason: str = Field(..., description="Disclaimer noting rough material-based estimate")
    is_estimate: bool = Field(default=True, description="Flag indicating heuristic nature")


def classify_sustainability_tier(material: str | None) -> tuple[str, str]:
    if not material or not material.strip():
        return "Unrated", "Material unknown. Rough estimate not available."

    mat_lower = material.strip().lower()

    if mat_lower in SUSTAINABILITY_REFERENCE:
        entry = SUSTAINABILITY_REFERENCE[mat_lower]
        return entry["tier"], f"Rough material estimate based on {entry['category']} ('{material}'). Not a certified rating."

    synthetic_keywords = [
        "polyester", "nylon", "acrylic", "spandex", "elastane",
        "polyurethane", "rayon", "viscose", "synthetic", "poly", "fleece",
    ]
    natural_keywords = [
        "cotton", "linen", "wool", "silk", "cashmere", "hemp", "merino", "denim", "twill",
    ]

    has_synthetic = any(k in mat_lower for k in synthetic_keywords)
    has_natural = any(k in mat_lower for k in natural_keywords)

    if has_synthetic and has_natural:
        return "Higher impact", f"Rough material estimate: blended fabric containing synthetics ('{material}'). Not a certified rating."
    elif has_synthetic:
        return "Higher impact", f"Rough material estimate: synthetic fiber composition ('{material}'). Not a certified rating."
    elif has_natural:
        return "Lower impact", f"Rough material estimate: natural fiber composition ('{material}'). Not a certified rating."

    return "Unrated", f"Material '{material}' is unrated in reference table. Rough estimate only."


def assemble_candidate_summary_panel(
    candidate_item_id: int,
    db: Session,
    versatility_axis: AxisScore | None = None,
    seasonality_axis: AxisScore | None = None,
) -> DecisionSummaryMetrics:
    candidate = db.query(WardrobeItem).filter(WardrobeItem.id == candidate_item_id).first()

    # 1. Versatility: reuse M20 directly
    if versatility_axis is None:
        versatility_axis = score_versatility(candidate_item_id, db)
    versatility_score = versatility_axis.score
    outfits_count = 0
    if versatility_axis.raw_evidence and isinstance(versatility_axis.raw_evidence, dict):
        outfits_count = int(versatility_axis.raw_evidence.get("combinations_count", 0))

    # 2. Duplicate Risk: NON-INVERTED duplicate similarity percentage
    raw_dup = getattr(candidate, "duplicate_similarity_pct", None) if candidate else None
    dup_sim = float(raw_dup) if isinstance(raw_dup, (int, float)) else 0.0
    if dup_sim >= 70.0:
        dup_label = f"{dup_sim:.1f}% similarity to closet (High duplicate risk — low uniqueness on radar)"
    elif dup_sim >= 35.0:
        dup_label = f"{dup_sim:.1f}% similarity to closet (Moderate duplicate risk)"
    elif dup_sim > 0.0:
        dup_label = f"{dup_sim:.1f}% similarity to closet (Low duplicate risk — high uniqueness on radar)"
    else:
        dup_label = "0.0% duplicate similarity (Completely unique vs closet)"

    # 3. Seasonality: reuse M21 directly
    if seasonality_axis is None:
        seasonality_axis = score_seasonal_relevance(candidate_item_id, db)
    seasonality_score = getattr(seasonality_axis, "score", 50.0)
    if seasonality_score >= 80.0:
        seasonality_label = "In-Season (High utility)"
    elif seasonality_score >= 50.0:
        seasonality_label = "Upcoming / Transition season"
    else:
        seasonality_label = "Off-Season (Low immediate wear)"

    # 4. Cost-per-wear: raw currency-per-wear number from M17
    category = candidate.attributes.category if (candidate and candidate.attributes) else None
    price = getattr(candidate, "price", None) if candidate else None
    if isinstance(price, (int, float)) and price > 0:
        try:
            cpw_data = calculate_cost_per_wear(category=category, price=float(price))
            cpw = float(cpw_data.get("cost_per_wear", 0.0))
        except Exception:
            cpw = 0.0
    else:
        cpw = 0.0
    cpw_formatted = f"${cpw:.2f} / wear" if cpw > 0 else "$0.00 / wear"

    # 5. Sustainability: material-based heuristic tier
    material = candidate.attributes.material if (candidate and candidate.attributes) else None
    tier, reason = classify_sustainability_tier(material)

    return DecisionSummaryMetrics(
        versatility=round(versatility_score, 1),
        versatility_outfits_count=outfits_count,
        duplicate_risk=round(dup_sim, 1),
        duplicate_risk_label=dup_label,
        seasonality=round(seasonality_score, 1),
        seasonality_label=seasonality_label,
        cost_per_wear=round(cpw, 2),
        cost_per_wear_formatted=cpw_formatted,
        sustainability_tier=tier,
        sustainability_reason=reason,
        is_estimate=True,
    )


def assemble_subset_summary_panel(
    subset_item_ids: Sequence[int],
    db: Session,
    subset_axes: Sequence[AxisScore | dict[str, Any]],
) -> DecisionSummaryMetrics:
    if not subset_item_ids:
        return DecisionSummaryMetrics(
            versatility=50.0,
            versatility_outfits_count=0,
            duplicate_risk=0.0,
            duplicate_risk_label="0.0% (Skip all baseline)",
            seasonality=50.0,
            seasonality_label="Baseline neutral timing",
            cost_per_wear=0.0,
            cost_per_wear_formatted="$0.00 / wear",
            sustainability_tier="Unrated",
            sustainability_reason="No items selected (Skip all baseline).",
            is_estimate=True,
        )

    items = db.query(WardrobeItem).filter(WardrobeItem.id.in_(subset_item_ids)).all()

    # 1. Versatility: from set-level versatility axis
    vers_score = 50.0
    outfits_count = 0
    season_score = 50.0

    for ax in subset_axes:
        axis_name = getattr(ax, "axis", None) or (ax.get("axis") if isinstance(ax, dict) else None)
        axis_name_str = getattr(axis_name, "value", str(axis_name))
        score_val = getattr(ax, "score", None) if not isinstance(ax, dict) else ax.get("score")
        raw_ev = getattr(ax, "raw_evidence", None) if not isinstance(ax, dict) else ax.get("raw_evidence")

        if axis_name_str == "versatility":
            vers_score = float(score_val or 50.0)
            if isinstance(raw_ev, dict):
                outfits_count = int(raw_ev.get("total_outfits_count", 0))
        elif axis_name_str == "seasonal_relevance":
            season_score = float(score_val or 50.0)

    # 2. Duplicate Risk: Max non-inverted duplicate similarity across the subset items
    dup_sims = []
    for it in items:
        raw_d = getattr(it, "duplicate_similarity_pct", None)
        if isinstance(raw_d, (int, float)):
            dup_sims.append(float(raw_d))
        else:
            dup_sims.append(0.0)
    max_dup = max(dup_sims) if dup_sims else 0.0
    if max_dup >= 70.0:
        dup_label = f"{max_dup:.1f}% peak wardrobe similarity (High duplicate risk — low uniqueness on radar)"
    elif max_dup >= 35.0:
        dup_label = f"{max_dup:.1f}% peak wardrobe similarity (Moderate risk)"
    elif max_dup > 0.0:
        dup_label = f"{max_dup:.1f}% peak wardrobe similarity (Low risk — high uniqueness on radar)"
    else:
        dup_label = "0.0% duplicate similarity (Cart items unique vs closet)"

    # 3. Seasonality: set-level seasonality label
    if season_score >= 80.0:
        season_label = "In-Season Cart (Immediate wear)"
    elif season_score >= 50.0:
        season_label = "Mixed / Transition seasonal utility"
    else:
        season_label = "Off-Season Cart"

    # 4. Cost-per-wear: mean cost-per-wear across subset
    cpw_values: list[float] = []
    for it in items:
        cat = it.attributes.category if it.attributes else None
        p = getattr(it, "price", None)
        if isinstance(p, (int, float)) and p > 0:
            try:
                cpw_item = float(calculate_cost_per_wear(category=cat, price=float(p)).get("cost_per_wear", 0.0))
                if cpw_item > 0:
                    cpw_values.append(cpw_item)
            except Exception:
                pass

    mean_cpw = sum(cpw_values) / len(cpw_values) if cpw_values else 0.0
    cpw_formatted = f"${mean_cpw:.2f} / wear (mean)" if mean_cpw > 0 else "$0.00 / wear"

    # 5. Sustainability: combined material tiers
    tiers: list[str] = []
    materials: list[str] = []
    for it in items:
        mat = it.attributes.material if it.attributes else None
        if mat:
            materials.append(mat)
            t, _ = classify_sustainability_tier(mat)
            tiers.append(t)

    if not tiers:
        cart_tier = "Unrated"
        reason = "Materials unknown for items in cart."
    elif all(t == "Lower impact" for t in tiers):
        cart_tier = "Lower impact"
        reason = f"All items in bundle feature predominantly natural fibers ({', '.join(materials)}). Rough estimate."
    elif any(t == "Higher impact" for t in tiers):
        cart_tier = "Higher impact"
        reason = f"Bundle includes synthetic fibers ({', '.join(materials)}). Rough material-based estimate."
    else:
        cart_tier = "Unrated"
        reason = "Bundle materials unrated. Rough estimate."

    return DecisionSummaryMetrics(
        versatility=round(vers_score, 1),
        versatility_outfits_count=outfits_count,
        duplicate_risk=round(max_dup, 1),
        duplicate_risk_label=dup_label,
        seasonality=round(season_score, 1),
        seasonality_label=season_label,
        cost_per_wear=round(mean_cpw, 2),
        cost_per_wear_formatted=cpw_formatted,
        sustainability_tier=cart_tier,
        sustainability_reason=reason,
        is_estimate=True,
    )
