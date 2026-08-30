import logging
import os
from pathlib import Path

import chromadb

logger = logging.getLogger(__name__)

COLLECTION_NAME = "wardrobe_items"


def get_chroma_client():
    chroma_host = os.getenv("CHROMA_HOST")
    if chroma_host:
        return chromadb.HttpClient(host=chroma_host)

    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(data_dir))


def get_wardrobe_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
        embedding_function=None,
    )


def upsert_wardrobe_embedding(
    item_id: int,
    user_id: int,
    category: str | None,
    embedding: list[float],
) -> None:
    collection = get_wardrobe_collection()
    doc_id = str(item_id)
    metadata = {
        "user_id": int(user_id),
        "category": str(category or "unknown"),
    }

    collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        metadatas=[metadata],
    )


def has_wardrobe_embedding(item_id: int) -> bool:
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
    collection = get_wardrobe_collection()

    where_filter = {}
    if user_id is not None:
        where_filter["user_id"] = int(user_id)
    if category is not None:
        where_filter["category"] = str(category)

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
    if distance > 1.0:
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
