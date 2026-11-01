"""Fast, dependency-light colour checks used as a duplicate-search guardrail."""

from __future__ import annotations

import colorsys
import io
from collections import Counter
from pathlib import Path
from urllib.request import urlopen

from PIL import Image


_NEUTRAL_FAMILIES = {"white", "grey"}


def _colour_family(red: int, green: int, blue: int) -> str:
    hue, saturation, value = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
    if value < 0.22:
        return "black"
    if saturation < 0.16:
        return "white" if value > 0.82 else "grey"

    degrees = hue * 360
    if degrees < 15 or degrees >= 345:
        return "red"
    if degrees < 42:
        return "brown" if value < 0.68 else "orange"
    if degrees < 70:
        return "beige" if saturation < 0.42 else "yellow"
    if degrees < 165:
        return "green"
    if degrees < 265:
        return "blue"
    if degrees < 325:
        return "purple"
    return "pink"


def _open_image(image_url: str) -> Image.Image:
    """Open local fallback uploads directly and hosted images with a short timeout."""
    local_path = Path(image_url)
    if local_path.exists():
        return Image.open(local_path).convert("RGB")
    if "/api/uploads/" in image_url:
        filename = image_url.split("/api/uploads/", 1)[1].split("?", 1)[0]
        local_path = Path(__file__).resolve().parent.parent.parent / "data" / "uploads" / filename
        return Image.open(local_path).convert("RGB")

    with urlopen(image_url, timeout=1.5) as response:  # nosec B310: URLs originate from image storage
        return Image.open(io.BytesIO(response.read())).convert("RGB")


def dominant_colour_families(image_url: str | None) -> set[str]:
    """Return meaningful dominant colours, or an empty set when the image is unavailable."""
    if not image_url:
        return set()
    try:
        with _open_image(image_url) as image:
            width, height = image.size
            # The central garment area is less likely than the edge to be a product-page background.
            crop = image.crop((width // 6, height // 8, width * 5 // 6, height * 7 // 8))
            crop.thumbnail((72, 72))
            pixels = (
                crop.get_flattened_data()
                if hasattr(crop, "get_flattened_data")
                else crop.getdata()
            )
            counts = Counter(_colour_family(*pixel[:3]) for pixel in pixels)
    except Exception:
        return set()

    total = sum(counts.values())
    if not total:
        return set()

    meaningful_counts = {
        family: count for family, count in counts.items() if family not in _NEUTRAL_FAMILIES
    }
    if not meaningful_counts:
        return set()

    # Keep the leading garment colour and only near-equal co-dominant colours.
    # A small black shadow on blue denim must not make it a "black" garment.
    leading_count = max(meaningful_counts.values())
    return {
        family
        for family, count in meaningful_counts.items()
        if count / total >= 0.12 and count >= leading_count * 0.8
    }


def photos_have_compatible_colours(candidate_url: str | None, existing_url: str | None) -> bool:
    """Reject only clear visual conflicts; unavailable images must never block a result."""
    candidate_colours = dominant_colour_families(candidate_url)
    existing_colours = dominant_colour_families(existing_url)
    if not candidate_colours or not existing_colours:
        return True
    return bool(candidate_colours & existing_colours)
