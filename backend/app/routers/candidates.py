"""
Candidate Evaluation Orchestration Router (MILESTONE 14).

POST /api/candidates
Chains Vision Agent, Try-On Agent, Embedding Agent, and Duplicate Detection
into a single orchestrated endpoint with per-section graceful error handling.
"""

import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import ExtractionSource, GarmentAttributes, User, WardrobeItem
from app.routers.wardrobe import _file_is_allowed, _stream_to_temp, get_or_create_user
from app.services.chroma_service import find_near_duplicate, upsert_wardrobe_embedding
from app.services.cloudinary_service import upload_image
from app.services.embedding_service import generate_embedding
from app.services.outfit_service import find_compatible_items
from app.services.tryon_service import TryOnServiceError, generate_tryon
from app.services.vision_service import VisionServiceError, analyze_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def evaluate_candidate_item(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a candidate garment image and run full evaluation in one flow.

    Execution Steps:
    1. Upload image to Cloudinary & create WardrobeItem(is_candidate=True).
    2. Vision Agent: Extract 6 garment attributes & save GarmentAttributes.
    3. Try-On Agent: Virtual try-on render + fit signal analysis.
    4. Embedding Agent: Generate CLIP vector & store in ChromaDB.
    5. Duplicate Detection: Query ChromaDB for nearest non-candidate wardrobe match.

    Each sub-step (2-5) catches exceptions independently and records error messages in
    the ``errors`` dictionary without failing the entire request.
    """
    owner = get_or_create_user(db, user["uid"], user["email"])
    filename = file.filename or "candidate.jpg"

    if not _file_is_allowed(file.content_type or "", filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Only JPG, PNG, and WebP are allowed.",
        )

    tmp_path: str | None = None
    try:
        tmp_path, _size = _stream_to_temp(file)
        public_id = f"verdict/candidates/{owner.firebase_uid}/{uuid.uuid4().hex}"
        cloud = upload_image(tmp_path, public_id=public_id)

        # Step 1: Create WardrobeItem row with is_candidate=True
        candidate_item = WardrobeItem(
            user_id=owner.id,
            cloudinary_url=cloud["url"],
            cloudinary_public_id=cloud["public_id"],
            is_candidate=True,
            uploaded_at=datetime.now(timezone.utc),
        )
        db.add(candidate_item)
        db.commit()
        db.refresh(candidate_item)

    except Exception as e:
        logger.error("Failed uploading candidate image: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed uploading candidate photo: {e}",
        ) from e
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    item_id = candidate_item.id
    image_url = candidate_item.cloudinary_url

    attributes_res: dict | None = None
    tryon_res: dict | None = None
    duplicate_res: dict | None = None
    embedding: list[float] | None = None
    errors: dict[str, str] = {}

    # Step 2: Vision Agent Analysis
    try:
        logger.info("M14 Step 2 [Vision] Analyzing candidate item %s", item_id)
        extracted = analyze_image(image_url)

        now = datetime.now(timezone.utc)
        attrs = GarmentAttributes(
            wardrobe_item_id=item_id,
            category=extracted["category"],
            color=extracted["color"],
            pattern=extracted["pattern"],
            style=extracted["style"],
            season=extracted["season"],
            material=extracted["material"],
            extraction_source=ExtractionSource.AI,
            updated_at=now,
        )
        db.add(attrs)
        db.commit()

        attributes_res = {
            "category": attrs.category,
            "color": attrs.color,
            "pattern": attrs.pattern,
            "style": attrs.style,
            "season": attrs.season,
            "material": attrs.material,
        }
    except Exception as err:
        logger.warning("M14 Vision step failed for candidate item %s: %s", item_id, err)
        errors["attributes"] = str(err)

    # Step 3: Virtual Try-On & Fit Signal Analysis
    try:
        logger.info("M14 Step 3 [Try-On] Generating virtual try-on for candidate item %s", item_id)
        category = attributes_res.get("category") if attributes_res else None
        tryon_res = generate_tryon(
            garment_url=image_url,
            garment_category=category,
        )
    except Exception as err:
        logger.warning("M14 Try-On step failed for candidate item %s: %s", item_id, err)
        errors["tryon"] = str(err)

    # Step 4: Local CLIP Embedding Generation & ChromaDB Storage
    try:
        logger.info("M14 Step 4 [Embedding] Generating CLIP vector for candidate item %s", item_id)
        embedding = generate_embedding(image_url)
        category_str = (attributes_res.get("category") if attributes_res else None) or "unknown"
        upsert_wardrobe_embedding(
            item_id=item_id,
            user_id=owner.id,
            category=category_str,
            embedding=embedding,
        )
    except Exception as err:
        logger.warning("M14 Embedding step failed for candidate item %s: %s", item_id, err)
        errors["embedding"] = str(err)

    # Step 5: Duplicate Detection
    if embedding:
        try:
            logger.info("M14 Step 5 [Duplicate] Querying near-duplicates for candidate item %s", item_id)
            near_dup = find_near_duplicate(
                query_embedding=embedding,
                user_id=owner.id,
                exclude_item_id=item_id,
            )
            if near_dup:
                matched_id = near_dup["wardrobe_item_id"]
                matched_item = db.query(WardrobeItem).filter(WardrobeItem.id == matched_id).first()

                matched_url = (
                    matched_item.cloudinary_url
                    if matched_item
                    else near_dup.get("metadata", {}).get("cloudinary_url", "")
                )
                matched_category = (
                    (matched_item.attributes.category if matched_item and matched_item.attributes else None)
                    or near_dup.get("metadata", {}).get("category")
                    or "item"
                )
                pct = near_dup["similarity_percentage"]

                duplicate_res = {
                    "wardrobe_item_id": matched_id,
                    "cloudinary_url": matched_url,
                    "similarity_percentage": pct,
                    "distance": near_dup["distance"],
                    "category": matched_category,
                    "message": f"{pct}% similar to a {matched_category} you already own",
                }
        except Exception as err:
            logger.warning("M14 Duplicate detection step failed for candidate item %s: %s", item_id, err)
            errors["duplicate"] = str(err)

    return {
        "candidate_item_id": item_id,
        "cloudinary_url": image_url,
        "attributes": attributes_res,
        "tryon": tryon_res,
        "duplicate": duplicate_res,
        "errors": errors if errors else None,
    }


@router.get("/{candidate_id}/outfit-matches")
async def get_candidate_outfit_matches(
    candidate_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return rule-based outfit matches for a candidate garment from user's existing wardrobe.

    Enforces ownership check. Queries user's non-candidate wardrobe items (is_candidate = False)
    and evaluates classical category compatibility & color harmony rules.
    Each returned match includes a `matched_because` array detailing the exact rules applied.
    """
    owner = get_or_create_user(db, user["uid"], user["email"])

    candidate = db.query(WardrobeItem).filter(WardrobeItem.id == candidate_id).first()
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate item not found",
        )
    if candidate.user_id != owner.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this candidate item",
        )

    attrs = candidate.attributes
    candidate_attributes = {
        "category": attrs.category if attrs else "unknown",
        "color": attrs.color if attrs else "unknown",
        "pattern": attrs.pattern if attrs else None,
        "style": attrs.style if attrs else None,
        "season": attrs.season if attrs else None,
        "material": attrs.material if attrs else None,
    }

    # Fetch user's non-candidate wardrobe items
    existing_items = (
        db.query(WardrobeItem)
        .filter(
            WardrobeItem.user_id == owner.id,
            WardrobeItem.is_candidate == False,
            WardrobeItem.id != candidate_id,
        )
        .all()
    )

    matches = find_compatible_items(
        candidate_attributes=candidate_attributes,
        wardrobe_items=existing_items,
    )

    return {
        "candidate_id": candidate_id,
        "candidate_attributes": candidate_attributes,
        "total_matches": len(matches),
        "matches": matches,
    }

