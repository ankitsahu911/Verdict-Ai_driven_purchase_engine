"""
Try-On Agent router (MILESTONES 10 + 11).

POST /api/tryon/{wardrobe_item_id}
Runs YouCam virtual try-on on a wardrobe item and immediately performs
structured fit analysis on the resulting render image.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import WardrobeItem
from app.routers.wardrobe import get_or_create_user
from app.services.tryon_service import TryOnServiceError, generate_tryon

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tryon", tags=["tryon"])


class TryOnRequest(BaseModel):
    user_photo_url: Optional[str] = None
    garment_category: Optional[str] = None


class TryOnResponse(BaseModel):
    render_url: str
    fit_tightness: Optional[str] = None
    silhouette: Optional[str] = None
    notes: Optional[str] = None


@router.post("/{wardrobe_item_id}", response_model=TryOnResponse)
async def create_tryon_render(
    wardrobe_item_id: int,
    payload: Optional[TryOnRequest] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run virtual try-on for a wardrobe item and return render URL with structured fit analysis.

    Validates wardrobe item ownership, calls YouCam virtual try-on, and performs
    fit analysis pass using Gemini vision on the rendered result.
    """
    owner = get_or_create_user(db, user["uid"], user["email"])

    item = db.query(WardrobeItem).filter(WardrobeItem.id == wardrobe_item_id).first()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wardrobe item not found",
        )
    if item.user_id != owner.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this item",
        )

    user_photo_url = payload.user_photo_url if payload else None
    garment_category = payload.garment_category if payload else None

    try:
        result = generate_tryon(
            garment_url=item.cloudinary_url,
            user_photo_url=user_photo_url,
            garment_category=garment_category,
        )
    except TryOnServiceError as e:
        logger.error("Try-on failed for wardrobe item %s: %s", wardrobe_item_id, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e

    return result
