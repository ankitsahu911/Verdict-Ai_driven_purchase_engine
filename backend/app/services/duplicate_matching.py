"""Small, explainable attribute checks that complement visual duplicate search."""

from __future__ import annotations

import re
from typing import Any

from app.services.chroma_service import normalize_category


_COLOR_FAMILIES = {
    "black": "black", "white": "white", "grey": "grey", "gray": "grey",
    "navy": "blue", "blue": "blue", "teal": "blue", "cyan": "blue",
    "red": "red", "burgundy": "red", "maroon": "red", "pink": "pink",
    "purple": "purple", "violet": "purple", "green": "green", "olive": "green",
    "yellow": "yellow", "orange": "orange", "brown": "brown", "beige": "beige",
    "tan": "beige", "cream": "beige", "khaki": "beige", "gold": "gold", "silver": "silver",
}


def color_family(value: str | None) -> str | None:
    """Map model wording such as 'navy blue' to one stable colour family."""
    if not value:
        return None
    for token in re.findall(r"[a-z]+", value.lower()):
        if token in _COLOR_FAMILIES:
            return _COLOR_FAMILIES[token]
    return None


def attribute_duplicate_score(
    candidate: dict[str, Any], existing: dict[str, Any]
) -> tuple[float, str | None]:
    """Return a conservative duplicate-risk floor for close wardrobe attributes."""
    candidate_category = normalize_category(candidate.get("category"))
    existing_category = normalize_category(existing.get("category"))
    if not candidate_category or candidate_category != existing_category:
        return 0.0, None

    candidate_colour = color_family(candidate.get("color"))
    existing_colour = color_family(existing.get("color"))
    if not candidate_colour or candidate_colour != existing_colour:
        return 0.0, None

    score = 78.0
    matched_details = [f"same {candidate_colour} {candidate_category}"]
    for field, bonus in (("style", 7.0), ("material", 5.0), ("pattern", 3.0)):
        candidate_value = str(candidate.get(field) or "").strip().lower()
        existing_value = str(existing.get(field) or "").strip().lower()
        if candidate_value and existing_value and candidate_value == existing_value:
            score += bonus
            matched_details.append(f"same {field}")

    return min(score, 95.0), ", ".join(matched_details)
