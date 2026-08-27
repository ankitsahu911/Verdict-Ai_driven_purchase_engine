"""
Batch Backfill Script for Wardrobe CLIP Embeddings (MILESTONE 12).

Scans all existing `wardrobe_items` in Postgres and generates + stores missing
CLIP embeddings in ChromaDB (`wardrobe_items` collection).

Idempotent: safe to re-run multiple times — skips items already embedded.

Usage:
    python scripts/backfill_embeddings.py
"""

import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import WardrobeItem
from app.services.chroma_service import (
    has_wardrobe_embedding,
    upsert_wardrobe_embedding,
)
from app.services.embedding_service import EmbeddingServiceError, generate_embedding

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("backfill")


def backfill_embeddings() -> tuple[int, int, int]:
    """Loop over all wardrobe items and generate missing ChromaDB embeddings.

    Returns:
        (total_items, backfilled_count, skipped_count)
    """
    db = SessionLocal()
    try:
        items = db.query(WardrobeItem).order_by(WardrobeItem.id.asc()).all()
        total_items = len(items)
        logger.info("Found %d wardrobe item(s) in Postgres.", total_items)

        backfilled_count = 0
        skipped_count = 0
        failed_count = 0

        for idx, item in enumerate(items, start=1):
            item_id = item.id
            user_id = item.user_id
            url = item.cloudinary_url
            category = (
                item.attributes.category
                if (item.attributes and item.attributes.category)
                else "unknown"
            )

            if has_wardrobe_embedding(item_id):
                logger.info(
                    "[%d/%d] SKIP item_id=%d — vector already present in ChromaDB.",
                    idx,
                    total_items,
                    item_id,
                )
                skipped_count += 1
                continue

            logger.info(
                "[%d/%d] EMBED item_id=%d category='%s' url=%s",
                idx,
                total_items,
                item_id,
                category,
                url,
            )

            try:
                embedding = generate_embedding(url)
                upsert_wardrobe_embedding(
                    item_id=item_id,
                    user_id=user_id,
                    category=category,
                    embedding=embedding,
                )
                backfilled_count += 1
                logger.info("  -> Successfully stored vector for item_id=%d", item_id)
            except EmbeddingServiceError as e:
                logger.error("  -> FAILED item_id=%d: %s", item_id, e)
                failed_count += 1
            except Exception as e:
                logger.error("  -> UNEXPECTED ERROR item_id=%d: %s", item_id, e)
                failed_count += 1

        logger.info(
            "\nBackfill Complete: %d total, %d backfilled, %d skipped, %d failed.",
            total_items,
            backfilled_count,
            skipped_count,
            failed_count,
        )
        return total_items, backfilled_count, skipped_count
    finally:
        db.close()


if __name__ == "__main__":
    backfill_embeddings()
