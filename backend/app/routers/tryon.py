import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import WardrobeItem
from app.routers.wardrobe import get_or_create_user
from app.services.tryon_service import (
    TryOnConnectionError,
    TryOnServiceError,
    TryOnTimeoutError,
    build_tryon_fallback,
    generate_tryon,
)

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
    cached: bool = False
    tryon_degraded: bool = False


@router.get("/{wardrobe_item_id}", response_model=TryOnResponse)
async def get_tryon_render(
    wardrobe_item_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    current_model_photo = getattr(owner, "model_photo_url", None) or os.getenv("YOUCAM_SRC_URL")
    if item.tryon_render_url and isinstance(item.tryon_render_url, str):
        is_valid = bool(
            item.tryon_cached_model_photo_url
            and isinstance(item.tryon_cached_model_photo_url, str)
            and item.tryon_cached_model_photo_url == current_model_photo
        )
        logger.info(
            "[TryOn Cache] GET item %s: cache %s (cached_url=%s, current_url=%s)",
            wardrobe_item_id,
            "VALID" if is_valid else "STALE",
            item.tryon_cached_model_photo_url,
            current_model_photo,
        )
        return TryOnResponse(
            render_url=item.tryon_render_url,
            fit_tightness=item.fit_tightness,
            silhouette=item.silhouette,
            notes="Cached try-on render" if is_valid else "Stale try-on render (model photo changed)",
            cached=is_valid,
            tryon_degraded=bool(getattr(item, "tryon_degraded", False)),
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No try-on render found for this item",
    )


@router.post("/{wardrobe_item_id}", response_model=TryOnResponse)
async def create_tryon_render(
    wardrobe_item_id: int,
    payload: Optional[TryOnRequest] = None,
    force: bool = Query(
        False,
        description="Re-run YouCam try-on even if cached render exists",
    ),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    current_model_photo_url = (
        user_photo_url
        or getattr(owner, "model_photo_url", None)
        or os.getenv("YOUCAM_SRC_URL")
    )

    # Check cache: item must have tryon_render_url AND tryon_cached_model_photo_url matching current_model_photo_url
    is_cached = (
        not force
        and bool(item.tryon_render_url)
        and isinstance(item.tryon_render_url, str)
        and bool(item.tryon_cached_model_photo_url)
        and isinstance(item.tryon_cached_model_photo_url, str)
        and item.tryon_cached_model_photo_url == current_model_photo_url
        and not getattr(item, "tryon_degraded", False)
    )

    if is_cached:
        logger.info(
            "[TryOn Cache] HIT for wardrobe item %s (model_photo=%s). Returning cached render without calling YouCam.",
            wardrobe_item_id,
            current_model_photo_url,
        )
        return TryOnResponse(
            render_url=item.tryon_render_url,
            fit_tightness=item.fit_tightness,
            silhouette=item.silhouette,
            notes="Cached try-on render",
            cached=True,
            tryon_degraded=False,
        )

    logger.info(
        "[TryOn Cache] MISS for wardrobe item %s (cached_model_photo=%s, current_model_photo=%s, force=%s). Calling YouCam API.",
        wardrobe_item_id,
        getattr(item, "tryon_cached_model_photo_url", None),
        current_model_photo_url,
        force,
    )

    try:
        result = generate_tryon(
            garment_url=item.cloudinary_url,
            user_photo_url=current_model_photo_url,
            garment_category=garment_category,
        )
        # Persist the fresh result and model photo URL used for future cache hits
        item.tryon_render_url = result.get("render_url")
        item.fit_tightness = result.get("fit_tightness")
        item.silhouette = result.get("silhouette")
        item.tryon_cached_model_photo_url = current_model_photo_url
        item.tryon_degraded = False
        db.commit()
        db.refresh(item)

        return TryOnResponse(
            render_url=result["render_url"],
            fit_tightness=result.get("fit_tightness"),
            silhouette=result.get("silhouette"),
            notes=result.get("notes"),
            cached=False,
            tryon_degraded=False,
        )
    except (TryOnServiceError, Exception) as e:
        logger.warning(
            "Try-on failed for wardrobe item %s: %s. Applying M33 graceful degradation.",
            wardrobe_item_id,
            e,
        )
        fallback = build_tryon_fallback(item, error_reason=str(e))
        item.tryon_render_url = fallback["render_url"]
        item.fit_tightness = fallback["fit_tightness"]
        item.silhouette = fallback["silhouette"]
        item.tryon_degraded = True
        db.commit()
        db.refresh(item)

        return TryOnResponse(
            render_url=fallback["render_url"],
            fit_tightness=fallback["fit_tightness"],
            silhouette=fallback["silhouette"],
            notes=fallback["notes"],
            cached=fallback["cached"],
            tryon_degraded=True,
        )

