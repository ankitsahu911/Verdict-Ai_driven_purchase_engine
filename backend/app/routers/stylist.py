"""
Stylist Chat Router for Verdict (Milestone 35).
Exposes POST /api/stylist/chat for grounded AI wardrobe consultation.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.routers.wardrobe import get_or_create_user
from app.services.stylist_service import stylist_chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stylist", tags=["stylist"])


class StylistChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The user's query or styling question.")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Max wardrobe items to retrieve as context.")


class RetrievedWardrobeItem(BaseModel):
    id: int
    category: str
    color: str
    style: str
    pattern: str
    season: str
    material: str
    thumbnail_url: Optional[str] = None
    similarity_score: float
    distance: float


class StylistChatResponse(BaseModel):
    reply: str
    retrieved_items: list[RetrievedWardrobeItem]
    provider_used: str
    model_used: str
    guardrail_triggered: bool = False


@router.post("/chat", response_model=StylistChatResponse)
async def chat_with_stylist(
    payload: StylistChatRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    RAG chat endpoint:
    - Encodes message with CLIP text encoder.
    - Queries ChromaDB for the user's top-K most semantically relevant items.
    - Structural guardrail: short-circuits to canned template if no items meet threshold.
    - Prompts the LLM (via provider-abstraction with automatic Ollama fallback).
    - Returns grounded advice and the list of retrieved context items.
    """
    owner = get_or_create_user(db, user["uid"], user["email"])

    try:
        result = stylist_chat(
            user_id=owner.id,
            message=payload.message,
            db=db,
            top_k=payload.top_k or 5,
        )
        return StylistChatResponse(
            reply=result["reply"],
            retrieved_items=result["retrieved_items"],
            provider_used=result["provider_used"],
            model_used=result["model_used"],
            guardrail_triggered=result.get("guardrail_triggered", False),
        )
    except Exception as e:
        logger.error("Stylist chat processing failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stylist chat failed: {e}",
        ) from e
