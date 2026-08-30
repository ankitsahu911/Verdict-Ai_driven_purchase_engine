import json
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
    query_similar_items,
    upsert_wardrobe_embedding,
)
from app.services.embedding_service import generate_embedding

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("verify")


def verify_embeddings(target_item_id: int | None = None, top_k: int = 5) -> dict:
    db = SessionLocal()
    try:
        if target_item_id is not None:
            target_item = (
                db.query(WardrobeItem)
                .filter(WardrobeItem.id == target_item_id)
                .first()
            )
            if not target_item:
                print(f"ERROR: Wardrobe item with ID {target_item_id} not found in DB.")
                sys.exit(1)
        else:
            target_item = (
                db.query(WardrobeItem).order_by(WardrobeItem.id.asc()).first()
            )
            if not target_item:
                print("WARNING: No wardrobe items found in database.")
                return {}

        target_id = target_item.id
        target_url = target_item.cloudinary_url
        target_category = (
            target_item.attributes.category
            if (target_item.attributes and target_item.attributes.category)
            else "unknown"
        )

        print(f"\n=======================================================")
        print(f" Target Item ID:  {target_id}")
        print(f" Target Category: {target_category}")
        print(f" Target URL:      {target_url}")
        print(f"=======================================================\n")

        print("Generating/loading vector embedding for target item...")
        query_vector = generate_embedding(target_url)

        upsert_wardrobe_embedding(
            item_id=target_id,
            user_id=target_item.user_id,
            category=target_category,
            embedding=query_vector,
        )

        print(f"Querying top-{top_k} nearest neighbors in ChromaDB (excluding self)...\n")
        matches = query_similar_items(
            query_embedding=query_vector,
            top_k=top_k,
            exclude_item_id=target_id,
        )

        if not matches:
            print("No other matching items found in ChromaDB.")
            return {"target_id": target_id, "matches": []}

        print(f"{'Rank':<5} {'Item ID':<10} {'Distance':<12} {'Category':<15} {'URL'}")
        print("-" * 75)

        enriched_matches = []
        for rank, match in enumerate(matches, start=1):
            m_id = match["id"]
            dist = match["distance"]
            meta = match.get("metadata", {})
            m_category = meta.get("category", "unknown")

            db_match = db.query(WardrobeItem).filter(WardrobeItem.id == m_id).first()
            m_url = db_match.cloudinary_url if db_match else "unknown_url"

            print(f"{rank:<5} {m_id:<10} {dist:<12.4f} {m_category:<15} {m_url[:35]}...")
            enriched_matches.append(
                {
                    "rank": rank,
                    "item_id": m_id,
                    "distance": dist,
                    "category": m_category,
                    "url": m_url,
                }
            )

        print("-" * 75)
        print("Verification query completed successfully.\n")
        return {"target_id": target_id, "matches": enriched_matches}
    finally:
        db.close()


if __name__ == "__main__":
    item_arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    verify_embeddings(target_item_id=item_arg)
