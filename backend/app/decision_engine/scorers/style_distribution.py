"""
Wardrobe Style Distribution Helper (MILESTONE 22).

Calculates the percentage distribution of garment styles in a user's wardrobe.
Shared by Style Alignment (cohesion) and Occasion Coverage (gap filling) scorers.
"""

from collections import Counter
import logging
from sqlalchemy.orm import Session

from app.models import WardrobeItem

logger = logging.getLogger(__name__)


def get_wardrobe_style_distribution(
    user_id: int,
    db: Session,
    exclude_item_id: int | None = None,
) -> dict[str, float]:
    """Compute the percentage distribution of styles across a user's non-candidate wardrobe.

    Args:
        user_id: Database primary key of the User.
        db: Active SQLAlchemy database session.
        exclude_item_id: Optional item ID to exclude (e.g. candidate item).

    Returns:
        Dictionary mapping normalized style strings to their percentage in the wardrobe (0.0 to 100.0).
        Returns empty dictionary if user has no non-candidate wardrobe items.
    """
    query = db.query(WardrobeItem).filter(
        WardrobeItem.user_id == user_id,
        WardrobeItem.is_candidate == False,
    )
    if exclude_item_id:
        query = query.filter(WardrobeItem.id != exclude_item_id)

    wardrobe_items = query.all()
    if not wardrobe_items:
        return {}

    styles: list[str] = []
    for item in wardrobe_items:
        if item.attributes and item.attributes.style:
            st = item.attributes.style.strip().lower()
            if st:
                styles.append(st)
        else:
            styles.append("casual")  # default fallback style

    total_count = len(styles)
    if total_count == 0:
        return {}

    counts = Counter(styles)
    distribution: dict[str, float] = {}
    for st, count in counts.items():
        distribution[st] = round((count / total_count) * 100.0, 1)

    return distribution
