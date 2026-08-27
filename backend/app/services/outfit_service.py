"""
Rule-Based Outfit Service (MILESTONE 15).

Provides classical, deterministic rule-based logic for outfit pairing:
- Category compatibility lookup table.
- Color harmony rules (neutrals & color families).
- Traceable `matched_because` reasoning for explainable AI decisions.

NO LLM calls are used in this module.
"""

import logging
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
# Dict[normalized_category, List[compatible_normalized_categories]]
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


def find_compatible_items(
    candidate_attributes: dict[str, Any],
    wardrobe_items: list[Any],
) -> list[dict[str, Any]]:
    """Filter user's wardrobe items to find pieces compatible with the candidate item.

    Args:
        candidate_attributes: Dict containing at minimum category and color.
        wardrobe_items: List of WardrobeItem SQLAlchemy model instances (with attributes).

    Returns:
        List of dicts formatted with item ID, URL, attributes, and `matched_because` rules list.
    """
    candidate_cat = candidate_attributes.get("category") or "unknown"
    candidate_color = candidate_attributes.get("color") or "unknown"

    matches = []

    for item in wardrobe_items:
        attrs = item.attributes
        item_cat = attrs.category if attrs else "unknown"
        item_color = attrs.color if attrs else "unknown"

        # Check Category Rule
        cat_compat, cat_reason = check_category_compatibility(candidate_cat, item_cat)
        if not cat_compat:
            continue

        # Check Color Rule
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
