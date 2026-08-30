import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.decision_engine.orchestrator import synthesize_buy_score
from app.decision_engine.scorers import (
    score_budget_impact,
    score_occasion_coverage,
    score_redundancy,
    score_seasonal_relevance,
    score_style_alignment,
    score_versatility,
)
from app.models import ExtractionSource, GarmentAttributes, WardrobeItem
from app.routers.wardrobe import _file_is_allowed, _stream_to_temp, get_or_create_user
from app.services.chroma_service import find_near_duplicate, upsert_wardrobe_embedding
from app.services.cloudinary_service import upload_image
from app.services.economics_service import (
    calculate_cost_per_wear,
    calculate_return_risk,
)
from app.services.embedding_service import generate_embedding
from app.services.outfit_service import (
    build_ranked_outfit_combinations,
    find_compatible_items,
)
from app.services.tryon_service import generate_tryon
from app.services.vision_service import analyze_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def evaluate_candidate_item(
    file: UploadFile = File(...),
    price: float | None = Form(None),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

        parsed_price: float | None = None
        if price is not None and not hasattr(price, "__class__") or not type(price).__name__ == "Form":
            try:
                parsed_price = float(price)  # type: ignore
            except (ValueError, TypeError):
                parsed_price = None

        candidate_item = WardrobeItem(
            user_id=owner.id,
            cloudinary_url=cloud["url"],
            cloudinary_public_id=cloud["public_id"],
            is_candidate=True,
            price=parsed_price,
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

    try:
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
        logger.warning("Vision analysis failed for candidate item %s: %s", item_id, err)
        errors["attributes"] = str(err)

    try:
        category = attributes_res.get("category") if attributes_res else None
        tryon_res = generate_tryon(
            garment_url=image_url,
            garment_category=category,
        )
        if tryon_res:
            candidate_item.tryon_render_url = tryon_res.get("render_url")
            candidate_item.fit_tightness = tryon_res.get("fit_tightness")
            candidate_item.silhouette = tryon_res.get("silhouette")
    except Exception as err:
        logger.warning("Try-on step failed for candidate item %s: %s", item_id, err)
        errors["tryon"] = str(err)

    try:
        embedding = generate_embedding(image_url)
        category_str = (attributes_res.get("category") if attributes_res else None) or "unknown"
        upsert_wardrobe_embedding(
            item_id=item_id,
            user_id=owner.id,
            category=category_str,
            embedding=embedding,
        )
    except Exception as err:
        logger.warning("Embedding generation failed for candidate item %s: %s", item_id, err)
        errors["embedding"] = str(err)

    if embedding:
        try:
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

                candidate_item.duplicate_match_item_id = matched_id
                candidate_item.duplicate_similarity_pct = float(pct)

                duplicate_res = {
                    "wardrobe_item_id": matched_id,
                    "cloudinary_url": matched_url,
                    "similarity_percentage": pct,
                    "distance": near_dup["distance"],
                    "category": matched_category,
                    "message": f"{pct}% similar to a {matched_category} you already own",
                }
        except Exception as err:
            logger.warning("Duplicate detection failed for candidate item %s: %s", item_id, err)
            errors["duplicate"] = str(err)

    db.commit()

    return {
        "candidate_item_id": item_id,
        "cloudinary_url": image_url,
        "price": candidate_item.price,
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


@router.get("/{candidate_id}/outfit-combinations")
async def get_candidate_outfit_combinations(
    candidate_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
    candidate_dict = {
        "wardrobe_item_id": candidate.id,
        "cloudinary_url": candidate.cloudinary_url,
        "attributes": (
            {
                "category": attrs.category,
                "color": attrs.color,
                "pattern": attrs.pattern,
                "style": attrs.style,
                "season": attrs.season,
                "material": attrs.material,
            }
            if attrs
            else {}
        ),
    }

    existing_items = (
        db.query(WardrobeItem)
        .filter(
            WardrobeItem.user_id == owner.id,
            WardrobeItem.is_candidate == False,
            WardrobeItem.id != candidate_id,
        )
        .all()
    )

    combinations = build_ranked_outfit_combinations(
        candidate_item=candidate_dict,
        wardrobe_items=existing_items,
        top_n=5,
    )

    return {
        "candidate_id": candidate_id,
        "total_combinations_found": len(combinations),
        "combinations": combinations,
    }


class PriceUpdateRequest(BaseModel):
    price: float


@router.patch("/{candidate_id}/price")
async def update_candidate_price(
    candidate_id: int,
    payload: PriceUpdateRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    if payload.price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price must be a positive number",
        )

    candidate.price = float(payload.price)
    db.commit()
    db.refresh(candidate)

    return {
        "candidate_id": candidate_id,
        "price": candidate.price,
    }


@router.get("/{candidate_id}/economics")
async def get_candidate_economics(
    candidate_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    if candidate.price is None or candidate.price <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price not set for candidate item. Set price via PATCH /api/candidates/{id}/price first.",
        )

    attrs = candidate.attributes
    category = attrs.category if attrs else None

    try:
        econ = calculate_cost_per_wear(category=category, price=candidate.price)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err

    return_risk_info = calculate_return_risk(
        category=category,
        fit_tightness=candidate.fit_tightness,
    )

    return {
        "candidate_id": candidate_id,
        "price": candidate.price,
        "cost_per_wear": econ["cost_per_wear"],
        "baseline_wears_used": econ["baseline_wears_used"],
        "category": econ["category"],
        "return_risk": {
            "score": return_risk_info["return_risk_score"],
            "baseline_risk": return_risk_info["baseline_risk"],
            "fit_adjustment": return_risk_info["fit_adjustment"],
            "fit_tightness": return_risk_info["fit_tightness"],
            "reasoning": return_risk_info["reasoning"],
        },
    }


@router.get("/{candidate_id}/axes")
async def get_candidate_axis_scores(
    candidate_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    v_score = score_versatility(candidate_id, db)
    r_score = score_redundancy(candidate_id, db)
    s_score = score_seasonal_relevance(candidate_id, db)
    b_score = score_budget_impact(candidate_id, db)
    sa_score = score_style_alignment(candidate_id, db)
    oc_score = score_occasion_coverage(candidate_id, db)

    axes_list = [
        v_score.model_dump(),
        r_score.model_dump(),
        s_score.model_dump(),
        b_score.model_dump(),
        sa_score.model_dump(),
        oc_score.model_dump(),
    ]

    return {
        "candidate_id": candidate_id,
        "total_axes": len(axes_list),
        "axes": axes_list,
    }


@router.get("/{candidate_id}/buy-score")
async def get_candidate_buy_score(
    candidate_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    result = synthesize_buy_score(
        candidate_item_id=candidate_id,
        db=db,
        persist=True,
    )

    return result.model_dump()
