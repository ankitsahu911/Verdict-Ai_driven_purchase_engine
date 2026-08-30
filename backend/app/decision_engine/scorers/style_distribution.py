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
            styles.append("casual")

    total_count = len(styles)
    if total_count == 0:
        return {}

    counts = Counter(styles)
    distribution: dict[str, float] = {}
    for st, count in counts.items():
        distribution[st] = round((count / total_count) * 100.0, 1)

    return distribution
