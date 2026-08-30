"""
Rule-Based Outfit Service (MILESTONES 15 + 16).

Provides classical, deterministic rule-based logic for outfit pairing:
- Category compatibility lookup table.
- Color harmony rules (neutrals & color families).
- Season compatibility rules (exact season & all-season tags).
- Style / Occasion adjacency rules (casual, smart-casual, business-casual, formal, athletic).
- Full pairwise validation for complete multi-piece outfit combinations.
- Additive scoring and ranking of top 5 outfit combinations.
- Traceable `matched_because` / `matched_rules` and templated reason strings.

NO LLM calls are used in this module.
"""

import logging
from itertools import product
from typing import Any

logger = logging.getLogger(__name__)

# Standard normalized category groups
CATEGORY_MAP: dict[str, str] = {
    # Tops
    "top": "top",
    "shirt": "top",
    "t-shirt": "top",
    "blouse": "top",
    "sweater": "top",
    "hoodie": "top",
    "tank": "top",
    "crop top": "top",
    "polo": "top",
    # Bottoms
    "bottom": "bottom",
    "pants": "bottom",
    "jeans": "bottom",
    "trousers": "bottom",
    "shorts": "bottom",
    "skirt": "bottom",
    "leggings": "bottom",
    "sweatpants": "bottom",
    # Dresses & One-pieces
    "dress": "dress",
    "jumpsuit": "dress",
    "romper": "dress",
    "one-piece": "dress",
    # Outerwear
    "outerwear": "outerwear",
    "jacket": "outerwear",
    "coat": "outerwear",
    "blazer": "outerwear",
    "cardigan": "outerwear",
    "vest": "outerwear",
    # Footwear
    "footwear": "footwear",
    "shoes": "footwear",
    "sneakers": "footwear",
    "boots": "footwear",
    "heels": "footwear",
    "sandals": "footwear",
    "loafers": "footwear",
    "flats": "footwear",
}

# Classical category compatibility table
CATEGORY_COMPATIBILITY: dict[str, list[str]] = {
    "top": ["bottom", "footwear", "outerwear"],
    "bottom": ["top", "footwear", "outerwear"],
    "dress": ["footwear", "outerwear"],
    "outerwear": ["top", "bottom", "dress", "footwear"],
    "footwear": ["top", "bottom", "dress", "outerwear"],
}

# Neutral colors compatible with all colors
NEUTRAL_COLORS: set[str] = {
    "black",
    "white",
    "grey",
    "gray",
    "navy",
    "beige",
    "cream",
    "brown",
    "denim",
    "tan",
    "khaki",
    "nude",
    "charcoal",
    "silver",
    "gold",
    "ivory",
    "off-white",
}

# Color family mappings for non-neutrals
COLOR_FAMILIES: dict[str, str] = {
    "red": "warm_red",
    "burgundy": "warm_red",
    "maroon": "warm_red",
    "crimson": "warm_red",
    "pink": "rose",
    "rose": "rose",
    "magenta": "rose",
    "blue": "cool_blue",
    "sky blue": "cool_blue",
    "light blue": "cool_blue",
    "royal blue": "cool_blue",
    "cyan": "cool_blue",
    "teal": "green_teal",
    "green": "green_teal",
    "olive": "green_teal",
    "emerald": "green_teal",
    "mint": "green_teal",
    "yellow": "warm_yellow",
    "gold_yellow": "warm_yellow",
    "mustard": "warm_yellow",
    "orange": "warm_orange",
    "coral": "warm_orange",
    "peach": "warm_orange",
    "purple": "purple",
    "violet": "purple",
    "lavender": "purple",
}

# Style adjacency map (using style as occasion signal)
STYLE_ADJACENCY: dict[str, set[str]] = {
    "casual": {"casual", "smart-casual", "athletic", "sporty", "everyday"},
    "smart-casual": {"casual", "smart-casual", "business-casual", "formal", "everyday"},
    "business-casual": {"smart-casual", "business-casual", "formal", "workwear"},
    "formal": {"formal", "smart-casual", "business-casual", "elegant"},
    "athletic": {"athletic", "sporty", "casual", "activewear"},
    "sporty": {"athletic", "sporty", "casual", "activewear"},
    "workwear": {"business-casual", "workwear", "smart-casual"},
}

ALL_SEASON_TAGS: set[str] = {
    "all",
    "all-season",
    "all season",
    "all-seasons",
    "any",
    "year-round",
    "year round",
    "multi-season",
    "unknown",
    "",
}


def normalize_category(raw_category: str | None) -> str:
    """Normalize raw garment category string into a standard category key."""
    if not raw_category:
        return "unknown"
    cleaned = raw_category.strip().lower()
    return CATEGORY_MAP.get(cleaned, cleaned)


def normalize_color(raw_color: str | None) -> str:
    """Normalize raw garment color string."""
    if not raw_color:
        return "unknown"
    return raw_color.strip().lower()


def normalize_season(raw_season: str | None) -> str:
    """Normalize raw garment season string."""
    if not raw_season:
        return "all"
    cleaned = raw_season.strip().lower()
    if cleaned in ALL_SEASON_TAGS:
        return "all"
    return cleaned


def normalize_style(raw_style: str | None) -> str:
    """Normalize raw garment style string."""
    if not raw_style:
        return "unknown"
    return raw_style.strip().lower()


def check_category_compatibility(candidate_cat: str, item_cat: str) -> tuple[bool, str | None]:
    """Check if candidate category pairs with item category under rule table."""
    norm_candidate = normalize_category(candidate_cat)
    norm_item = normalize_category(item_cat)

    allowed = CATEGORY_COMPATIBILITY.get(norm_candidate, [])
    if norm_item in allowed:
        reason = f"category: {norm_candidate} pairs with {norm_item}"
        return True, reason

    return False, None


def check_color_harmony(candidate_color: str, item_color: str) -> tuple[bool, str | None]:
    """Check color harmony rules between candidate color and item color."""
    c_color = normalize_color(candidate_color)
    i_color = normalize_color(item_color)

    if c_color == "unknown" or i_color == "unknown":
        return True, "color: default match for unclassified color"

    # Neutral rules
    if c_color in NEUTRAL_COLORS:
        return True, f"color: candidate {c_color} is neutral"
    if i_color in NEUTRAL_COLORS:
        return True, f"color: wardrobe {i_color} is neutral"

    # Exact color match
    if c_color == i_color:
        return True, f"color: matching color {c_color}"

    # Same color family match
    c_family = COLOR_FAMILIES.get(c_color)
    i_family = COLOR_FAMILIES.get(i_color)
    if c_family and i_family and c_family == i_family:
        return True, f"color: {c_color} and {i_color} are in the same color family"

    return False, None


def check_season_compatibility(season_a: str | None, season_b: str | None) -> tuple[bool, str | None, int]:
    """Check season compatibility between two garments."""
    s_a = normalize_season(season_a)
    s_b = normalize_season(season_b)

    if s_a == "all" or s_b == "all":
        return True, "season: versatile all-season pairing", 5

    if s_a == s_b:
        return True, f"season: exact {s_a} season match", 10

    # Incompatible seasonal mismatch
    return False, None, 0


def check_style_compatibility(style_a: str | None, style_b: str | None) -> tuple[bool, str | None, int]:
    """Check style/occasion compatibility between two garments using adjacency rules."""
    st_a = normalize_style(style_a)
    st_b = normalize_style(style_b)

    if st_a == "unknown" or st_b == "unknown":
        return True, "style: default versatile style match", 5

    if st_a == st_b:
        return True, f"style: matching {st_a} style", 10

    adj_a = STYLE_ADJACENCY.get(st_a, {st_a})
    if st_b in adj_a:
        return True, f"style: adjacent {st_a} and {st_b} styles", 5

    return False, None, 0


def are_items_pairwise_compatible(item_a: dict, item_b: dict) -> tuple[bool, list[str], int]:
    """Check full pairwise compatibility between any 2 items (category, color, season, style)."""
    attrs_a = item_a.get("attributes") or {}
    attrs_b = item_b.get("attributes") or {}

    cat_a, cat_b = attrs_a.get("category"), attrs_b.get("category")
    col_a, col_b = attrs_a.get("color"), attrs_b.get("color")
    sea_a, sea_b = attrs_a.get("season"), attrs_b.get("season")
    sty_a, sty_b = attrs_a.get("style"), attrs_b.get("style")

    reasons = []
    total_score = 0

    # 1. Category Check
    cat_ok, cat_reason = check_category_compatibility(cat_a, cat_b)
    if not cat_ok:
        if normalize_category(cat_a) == normalize_category(cat_b):
            return False, [], 0
    elif cat_reason:
        reasons.append(cat_reason)
        total_score += 5

    # 2. Color Harmony Check
    col_ok, col_reason = check_color_harmony(col_a, col_b)
    if not col_ok:
        return False, [], 0
    if col_reason:
        reasons.append(col_reason)
        if "neutral" in col_reason:
            total_score += 8
        elif "matching" in col_reason:
            total_score += 10
        elif "family" in col_reason:
            total_score += 6
        else:
            total_score += 5

    # 3. Season Check
    sea_ok, sea_reason, sea_score = check_season_compatibility(sea_a, sea_b)
    if not sea_ok:
        return False, [], 0
    if sea_reason:
        reasons.append(sea_reason)
        total_score += sea_score

    # 4. Style / Occasion Check
    sty_ok, sty_reason, sty_score = check_style_compatibility(sty_a, sty_b)
    if not sty_ok:
        return False, [], 0
    if sty_reason:
        reasons.append(sty_reason)
        total_score += sty_score

    return True, reasons, total_score


def find_compatible_items(
    candidate_attributes: dict[str, Any],
    wardrobe_items: list[Any],
) -> list[dict[str, Any]]:
    """M15 compatible items flat-list search."""
    candidate_cat = candidate_attributes.get("category") or "unknown"
    candidate_color = candidate_attributes.get("color") or "unknown"

    matches = []
    for item in wardrobe_items:
        attrs = item.attributes
        item_cat = attrs.category if attrs else "unknown"
        item_color = attrs.color if attrs else "unknown"

        cat_compat, cat_reason = check_category_compatibility(candidate_cat, item_cat)
        if not cat_compat:
            continue

        color_compat, color_reason = check_color_harmony(candidate_color, item_color)
        if not color_compat:
            continue

        matched_because = []
        if cat_reason:
            matched_because.append(cat_reason)
        if color_reason:
            matched_because.append(color_reason)

        matches.append(
            {
                "wardrobe_item_id": item.id,
                "cloudinary_url": item.cloudinary_url,
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
                    else None
                ),
                "matched_because": matched_because,
            }
        )

    return matches


def generate_templated_reason(candidate: dict, combination_items: list[dict]) -> str:
    """Generate a plain-English reason summary from real matched fields without LLM calls."""
    cand_attrs = candidate.get("attributes") or {}
    cand_cat = normalize_category(cand_attrs.get("category"))
    cand_color = normalize_color(cand_attrs.get("color"))
    cand_style = normalize_style(cand_attrs.get("style"))
    cand_season = normalize_season(cand_attrs.get("season"))

    piece_names = []
    for item in combination_items:
        i_attrs = item.get("attributes") or {}
        color = normalize_color(i_attrs.get("color"))
        cat = i_attrs.get("category") or "piece"
        piece_names.append(f"{color} {cat}")

    pieces_str = " and ".join(piece_names) if piece_names else "wardrobe pieces"
    style_desc = f"{cand_style} " if cand_style != "unknown" else ""
    season_desc = "all-season" if cand_season == "all" else f"{cand_season}"

    if cand_color in NEUTRAL_COLORS:
        color_note = f"the {cand_color} {cand_cat}'s neutral tone works effortlessly with the {pieces_str}"
    else:
        color_note = f"the {cand_color} {cand_cat} pairs harmoniously with the {pieces_str}"

    return (
        f"A {style_desc}{season_desc} outfit: {color_note}, creating a cohesive look for "
        f"{cand_style if cand_style != 'unknown' else 'everyday'} settings."
    )


def build_ranked_outfit_combinations(
    candidate_item: dict,
    wardrobe_items: list[Any],
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """Build, validate, score, and rank multi-piece outfit combinations for a candidate item."""
    cand_attrs = candidate_item.get("attributes") or {}
    cand_cat = normalize_category(cand_attrs.get("category"))

    serialized_wardrobe = []
    for item in wardrobe_items:
        attrs = item.attributes
        serialized_wardrobe.append(
            {
                "wardrobe_item_id": item.id,
                "cloudinary_url": item.cloudinary_url,
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
        )

    individually_compatible = []
    for w_item in serialized_wardrobe:
        is_compat, reasons, score = are_items_pairwise_compatible(candidate_item, w_item)
        if is_compat:
            individually_compatible.append((w_item, reasons, score))

    by_category: dict[str, list[tuple[dict, list[str], int]]] = {}
    for w_item, reasons, score in individually_compatible:
        cat = normalize_category(w_item["attributes"].get("category"))
        by_category.setdefault(cat, []).append((w_item, reasons, score))

    slot_groups: list[list[str]] = []
    if cand_cat == "top":
        slot_groups = [["bottom", "footwear"], ["bottom", "footwear", "outerwear"]]
    elif cand_cat == "bottom":
        slot_groups = [["top", "footwear"], ["top", "footwear", "outerwear"]]
    elif cand_cat == "dress":
        slot_groups = [["footwear"], ["footwear", "outerwear"]]
    elif cand_cat == "outerwear":
        slot_groups = [["top", "bottom", "footwear"], ["dress", "footwear"]]
    elif cand_cat == "footwear":
        slot_groups = [["top", "bottom"], ["dress"]]
    else:
        slot_groups = [["bottom", "footwear"], ["top", "footwear"]]

    valid_combinations = []

    for slots in slot_groups:
        if not all(slot in by_category and len(by_category[slot]) > 0 for slot in slots):
            continue

        slot_item_lists = [by_category[slot] for slot in slots]
        for combo_tuple in product(*slot_item_lists):
            combo_items = [t[0] for t in combo_tuple]

            all_pairwise_ok = True
            combo_reasons = set()
            combo_total_score = 0

            # Candidate vs each item
            for w_item in combo_items:
                ok, r_list, sc = are_items_pairwise_compatible(candidate_item, w_item)
                if not ok:
                    all_pairwise_ok = False
                    break
                combo_reasons.update(r_list)
                combo_total_score += sc

            if not all_pairwise_ok:
                continue

            # Each item vs each other item
            for i in range(len(combo_items)):
                for j in range(i + 1, len(combo_items)):
                    ok, r_list, sc = are_items_pairwise_compatible(combo_items[i], combo_items[j])
                    if not ok:
                        all_pairwise_ok = False
                        break
                    combo_reasons.update(r_list)
                    combo_total_score += sc
                if not all_pairwise_ok:
                    break

            if not all_pairwise_ok:
                continue

            reason_summary = generate_templated_reason(candidate_item, combo_items)

            valid_combinations.append(
                {
                    "outfit_id": f"outfit_{len(valid_combinations) + 1}",
                    "total_score": combo_total_score,
                    "reason_summary": reason_summary,
                    "candidate": candidate_item,
                    "items": combo_items,
                    "matched_rules": sorted(list(combo_reasons)),
                }
            )

    valid_combinations.sort(key=lambda x: x["total_score"], reverse=True)
    return valid_combinations[:top_n]
