"""
Stylist Service for Verdict (Milestone 35).
Backend RAG pipeline for grounded stylist conversations:
1. Embeds user text query with CLIP text encoder (sharing wardrobe image embedding space).
2. Queries ChromaDB for top-K nearest wardrobe items scoped to user.
3. Retrieves item attributes from DB as context.
4. Executes grounded LLM completion through provider abstraction layer.
"""

import logging
import os
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import WardrobeItem
from app.services.chroma_service import (
    distance_to_similarity_percentage,
    query_similar_items,
)
from app.services.embedding_service import generate_text_embedding
from app.services.llm_provider import get_chat_completion

logger = logging.getLogger(__name__)

STYLIST_GUARDRAIL_REDIRECT_MESSAGE = (
    "I can help with questions about your own wardrobe and purchase decisions — "
    "I don't have general fashion trend info. Try asking about a specific item you own or are considering."
)

DEFAULT_SIMILARITY_THRESHOLD_PCT: float = 20.0

STYLIST_SYSTEM_PROMPT = """You are "Verdict Stylist" — an expert AI wardrobe and purchase decision advisor.
Your mission is to help the user evaluate outfit combinations and purchase decisions strictly grounded in their personal wardrobe.

OPERATIONAL RULES & GUARDRAILS:
1. WARDROBE GROUNDING: Only discuss and make recommendations using the user's actual retrieved wardrobe items provided in the context below. Reference items explicitly by category, color, style, and/or Item ID.
2. DECLINE UNGROUNDED/GENERIC QUERIES: If the user asks general fashion trivia, questions unrelated to their clothes, or questions that cannot be grounded in the retrieved wardrobe data, politely decline and steer them back:
   "I can only advise on outfit pairings and purchase decisions grounded in your own wardrobe items. Please ask about items in your closet or how a candidate purchase pairs with what you own."
3. EMPTY WARDROBE: If no matching items are provided in the context, inform the user that no relevant items were found in their wardrobe and prompt them to add wardrobe items.
4. TONE: Be concise, direct, helpful, and realistic. Focus on outfit cohesion, color harmony, and versatility."""


def retrieve_wardrobe_context(
    user_id: int,
    query_text: str,
    top_k: int = 5,
    db: Optional[Session] = None,
) -> list[dict[str, Any]]:
    """
    1. Embed query_text with CLIP text encoder.
    2. Search ChromaDB for top-K matching wardrobe items owned by user_id.
    3. Query Postgres for full GarmentAttributes and URLs.
    """
    if not query_text or not query_text.strip():
        return []

    try:
        query_embedding = generate_text_embedding(query_text.strip())
    except Exception as e:
        logger.warning("Failed to generate CLIP text embedding for query: %s", e)
        return []

    matches = query_similar_items(
        query_embedding=query_embedding,
        top_k=top_k,
        user_id=user_id,
    )

    if not matches:
        return []

    matched_ids = [m["id"] for m in matches]
    dist_map = {m["id"]: m["distance"] for m in matches}

    if db is None:
        return [
            {
                "id": mid,
                "category": "unknown",
                "color": "unknown",
                "style": "unknown",
                "pattern": "unknown",
                "season": "all-season",
                "material": "unknown",
                "thumbnail_url": None,
                "similarity_score": distance_to_similarity_percentage(dist_map.get(mid, 1.0)),
                "distance": dist_map.get(mid, 1.0),
            }
            for mid in matched_ids
        ]

    # Query DB items
    items = (
        db.query(WardrobeItem)
        .filter(WardrobeItem.id.in_(matched_ids), WardrobeItem.user_id == user_id)
        .all()
    )

    item_map = {item.id: item for item in items}
    retrieved: list[dict[str, Any]] = []

    # Preserve ranking order from Chroma
    for mid in matched_ids:
        item = item_map.get(mid)
        if not item:
            continue

        attrs = item.attributes
        dist = dist_map.get(mid, 1.0)
        similarity_pct = distance_to_similarity_percentage(dist)

        retrieved.append(
            {
                "id": item.id,
                "category": attrs.category if attrs else "item",
                "color": attrs.color if attrs else "unknown",
                "style": attrs.style if attrs else "casual",
                "pattern": attrs.pattern if attrs else "solid",
                "season": attrs.season if attrs else "all-season",
                "material": attrs.material if attrs else "unknown",
                "thumbnail_url": item.cloudinary_url,
                "similarity_score": similarity_pct,
                "distance": dist,
            }
        )

    return retrieved


def format_wardrobe_context(retrieved_items: list[dict[str, Any]]) -> str:
    """Format retrieved items list into clean Markdown for LLM prompt."""
    if not retrieved_items:
        return "No relevant items found in the user's wardrobe."

    lines = ["RETRIEVED USER WARDROBE ITEMS (Ordered by relevance to user query):"]
    for item in retrieved_items:
        lines.append(
            f"- Item #{item['id']}: {item['color']} {item['category']} "
            f"(Style: {item['style']}, Pattern: {item['pattern']}, Season: {item['season']}, "
            f"Material: {item['material']}, Match: {item['similarity_score']}%). "
            f"Thumbnail: {item.get('thumbnail_url') or 'N/A'}"
        )
    return "\n".join(lines)


def stylist_chat(
    user_id: int,
    message: str,
    db: Session,
    top_k: int = 5,
    force_fallback: bool = False,
    similarity_threshold: Optional[float] = None,
) -> dict[str, Any]:
    """
    RAG chat entry point with structural guardrails:
    1. Retrieves top-K wardrobe items via CLIP text embedding.
    2. Structural Guardrail Check:
       - If no items meet the similarity threshold (or user has no items),
         immediately return templated redirect WITHOUT calling the LLM.
    3. If grounded items exist:
       - Formats grounded items into prompt context.
       - Calls LLM provider abstraction layer with automatic Ollama fallback.
       - Returns grounded response with context item chips.
    """
    threshold = (
        similarity_threshold
        if similarity_threshold is not None
        else float(os.getenv("STYLIST_SIMILARITY_THRESHOLD", str(DEFAULT_SIMILARITY_THRESHOLD_PCT)))
    )

    retrieved_items = retrieve_wardrobe_context(
        user_id=user_id,
        query_text=message,
        top_k=top_k,
        db=db,
    )

    # Filter items that satisfy the minimum similarity threshold
    grounded_items = [
        item for item in retrieved_items
        if item.get("similarity_score", 0.0) >= threshold
    ]

    # Structural guardrail: if no relevant items found in wardrobe, short-circuit
    if not grounded_items:
        logger.info(
            "[Stylist Guardrail] Triggered: query '%s' has 0 items >= %s%% similarity (raw retrieved: %d). Short-circuiting LLM.",
            message[:50],
            threshold,
            len(retrieved_items),
        )
        return {
            "reply": STYLIST_GUARDRAIL_REDIRECT_MESSAGE,
            "retrieved_items": [],
            "provider_used": "guardrail_template",
            "model_used": "none",
            "guardrail_triggered": True,
        }

    context_str = format_wardrobe_context(grounded_items)

    user_prompt = (
        f"USER MESSAGE:\n\"{message.strip()}\"\n\n"
        f"{context_str}\n\n"
        f"INSTRUCTION: Answer the user's message thoughtfully and specifically using the retrieved wardrobe items above."
    )

    completion = get_chat_completion(
        prompt=user_prompt,
        system_instruction=STYLIST_SYSTEM_PROMPT,
        force_fallback=force_fallback,
    )

    return {
        "reply": completion.content,
        "retrieved_items": grounded_items,
        "provider_used": completion.provider_used,
        "model_used": completion.model_used,
        "guardrail_triggered": False,
    }

