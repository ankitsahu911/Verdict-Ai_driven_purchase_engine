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


def color_families(value: str | None) -> set[str]:
    """Map model wording such as 'black and white' to stable colour families."""
    if not value:
        return set()
    families = set()
    for token in re.findall(r"[a-z]+", value.lower()):
        if token in _COLOR_FAMILIES:
            families.add(_COLOR_FAMILIES[token])
    return families


def color_family(value: str | None) -> str | None:
    """Return the first stable colour family for backwards-compatible callers."""
    return next(iter(color_families(value)), None)


def colors_are_compatible(candidate_color: str | None, existing_color: str | None) -> bool:
    """Known conflicting colours must not be presented as close duplicates."""
    candidate_families = color_families(candidate_color)
    existing_families = color_families(existing_color)
    return not candidate_families or not existing_families or bool(candidate_families & existing_families)


def attributes_are_duplicate_compatible(
    candidate: dict[str, Any], existing: dict[str, Any]
) -> bool:
    candidate_category = normalize_category(candidate.get("category"))
    existing_category = normalize_category(existing.get("category"))
    return bool(
        candidate_category
        and candidate_category == existing_category
        and colors_are_compatible(candidate.get("color"), existing.get("color"))
    )


def attribute_duplicate_score(
    candidate: dict[str, Any], existing: dict[str, Any]
) -> tuple[float, str | None]:
    """Return a conservative duplicate-risk floor for close wardrobe attributes."""
    if not attributes_are_duplicate_compatible(candidate, existing):
        return 0.0, None

    candidate_category = normalize_category(candidate.get("category"))
    shared_colours = color_families(candidate.get("color")) & color_families(
        existing.get("color")
    )
    if not shared_colours:
        return 0.0, None

    score = 78.0
    matched_details = [f"same {sorted(shared_colours)[0]} {candidate_category}"]
    for field, bonus in (("style", 7.0), ("material", 5.0), ("pattern", 3.0)):
        candidate_value = str(candidate.get(field) or "").strip().lower()
        existing_value = str(existing.get(field) or "").strip().lower()
        if candidate_value and existing_value and candidate_value == existing_value:
            score += bonus
            matched_details.append(f"same {field}")

    return min(score, 95.0), ", ".join(matched_details)
