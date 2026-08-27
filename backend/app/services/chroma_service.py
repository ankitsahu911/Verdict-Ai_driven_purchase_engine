"""
ChromaDB Vector Store Service (MILESTONES 2 + 12).

Provides helper functions to store, retrieve, and query wardrobe item vector
embeddings in ChromaDB (`wardrobe_items` collection).
"""

import logging
import os
from pathlib import Path

import chromadb

logger = logging.getLogger(__name__)

COLLECTION_NAME = "wardrobe_items"


def get_chroma_client():
    """Return persistent ChromaDB client (local backend/data or hosted CHROMA_HOST)."""
    chroma_host = os.getenv("CHROMA_HOST")
    if chroma_host:
        logger.info("Connecting to hosted ChromaDB at %s", chroma_host)
        return chromadb.HttpClient(host=chroma_host)

    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(data_dir))


def get_wardrobe_collection():
    """Get or create the `wardrobe_items` collection using cosine distance space."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
        embedding_function=None,  # Custom CLIP vectors supplied
    )


def upsert_wardrobe_embedding(
    item_id: int,
    user_id: int,
    category: str | None,
    embedding: list[float],
) -> None:
    """Upsert a vector embedding into ChromaDB using wardrobe_items.id as record key.

    Metadata includes at minimum user_id and category for downstream filtering.
    """
    collection = get_wardrobe_collection()
    doc_id = str(item_id)
    metadata = {
        "user_id": int(user_id),
        "category": str(category or "unknown"),
    }

    logger.info("Upserting ChromaDB vector for item_id=%s user_id=%s", item_id, user_id)
    collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        metadatas=[metadata],
    )


def has_wardrobe_embedding(item_id: int) -> bool:
    """Check if a wardrobe item vector already exists in ChromaDB."""
    collection = get_wardrobe_collection()
    try:
        res = collection.get(ids=[str(item_id)])
        return bool(res and res.get("ids") and len(res["ids"]) > 0)
    except Exception:
        return False


def query_similar_items(
    query_embedding: list[float],
    top_k: int = 5,
    user_id: int | None = None,
    category: str | None = None,
    exclude_item_id: int | None = None,
) -> list[dict]:
    """Query ChromaDB for nearest neighbor items by embedding similarity.

    Supports metadata filtering on user_id and category.
    Returns list of dicts: [{"id": int, "distance": float, "metadata": dict}]
    """
    collection = get_wardrobe_collection()

    where_filter = {}
    if user_id is not None:
        where_filter["user_id"] = int(user_id)
    if category is not None:
        where_filter["category"] = str(category)

    # Fetch extra results if excluding query item itself
    fetch_k = top_k + 1 if exclude_item_id is not None else top_k

    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": max(fetch_k, 1),
    }
    if where_filter:
        kwargs["where"] = where_filter

    res = collection.query(**kwargs)

    if not res or not res.get("ids") or len(res["ids"][0]) == 0:
        return []

    matched_ids = res["ids"][0]
    matched_dists = res["distances"][0] if res.get("distances") else [0.0] * len(matched_ids)
    matched_metas = res["metadatas"][0] if res.get("metadatas") else [{}] * len(matched_ids)

    matches = []
    for mid, dist, meta in zip(matched_ids, matched_dists, matched_metas):
        try:
            item_id = int(mid)
        except ValueError:
            item_id = mid

        if exclude_item_id is not None and item_id == exclude_item_id:
            continue

        matches.append(
            {
                "id": item_id,
                "distance": float(dist),
                "metadata": meta,
            }
        )
        if len(matches) >= top_k:
            break

    return matches


def distance_to_similarity_percentage(distance: float) -> float:
    """Convert ChromaDB distance metric to 0-100% cosine similarity percentage.

    In cosine distance space: d_cosine = 1 - cosine_similarity.
    Therefore, cosine_similarity = 1.0 - d_cosine.
    If distance > 1.0 (e.g. from squared L2 on unit vectors d_l2 = 2 * d_cosine),
    we handle both gracefully.
    """
    if distance > 1.0:
        # Squared L2 distance for unit vectors: d_l2 = 2 * (1 - cos_sim) => cos_sim = 1 - d_l2/2
        cos_sim = 1.0 - (distance / 2.0)
    else:
        cos_sim = 1.0 - distance

    clamped_sim = max(0.0, min(1.0, cos_sim))
    return round(clamped_sim * 100.0, 1)


def find_near_duplicate(
    query_embedding: list[float],
    user_id: int,
    exclude_item_id: int | None = None,
) -> dict | None:
    """Query ChromaDB for the single nearest neighbor wardrobe item belonging to user_id.

    Excludes exclude_item_id if provided.
    Returns dict: {"wardrobe_item_id": int, "similarity_percentage": float, "distance": float}
    or None if no match is found.
    """
    matches = query_similar_items(
        query_embedding=query_embedding,
        top_k=1,
        user_id=user_id,
        exclude_item_id=exclude_item_id,
    )
    if not matches:
        return None

    top_match = matches[0]
    similarity_pct = distance_to_similarity_percentage(top_match["distance"])

    return {
        "wardrobe_item_id": top_match["id"],
        "similarity_percentage": similarity_pct,
        "distance": top_match["distance"],
        "metadata": top_match.get("metadata", {}),
    }

