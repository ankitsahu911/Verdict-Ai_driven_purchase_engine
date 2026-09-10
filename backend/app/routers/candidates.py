import asyncio
import logging
import os
import time
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
from app.services.tryon_service import build_tryon_fallback, generate_tryon
from app.services.vision_service import analyze_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


@router.get("")
async def list_candidate_items(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owner = get_or_create_user(db, user["uid"], user["email"])

    candidates = (
        db.query(WardrobeItem)
        .filter(WardrobeItem.user_id == owner.id, WardrobeItem.is_candidate == True)
        .order_by(WardrobeItem.uploaded_at.desc())
        .all()
    )

    return [
        {
            "id": item.id,
            "cloudinary_url": item.cloudinary_url,
            "price": item.price,
            "fit_tightness": item.fit_tightness,
            "silhouette": item.silhouette,
            "tryon_render_url": item.tryon_render_url,
            "tryon_cached_model_photo_url": item.tryon_cached_model_photo_url,
            "tryon_degraded": bool(getattr(item, "tryon_degraded", False)),
            "duplicate_similarity_pct": item.duplicate_similarity_pct,
            "uploaded_at": item.uploaded_at.isoformat(),
            "attributes": (
                {
                    "category": item.attributes.category,
                    "color": item.attributes.color,
                    "pattern": item.attributes.pattern,
                    "style": item.attributes.style,
                    "season": item.attributes.season,
                    "material": item.attributes.material,
                    "extraction_source": item.attributes.extraction_source.value,
                }
                if item.attributes
                else None
            ),
        }
        for item in candidates
    ]


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
        if tmp_path and os.path.exists(tmp_path):
            with open(tmp_path, "rb") as f:
                raw_header = f.read(32)

            is_magic_ok = (
                raw_header.startswith(b"\xff\xd8")
                or raw_header.startswith(b"\x89PNG")
                or (raw_header.startswith(b"RIFF") and len(raw_header) >= 12 and raw_header[8:12] == b"WEBP")
            )
            if not is_magic_ok:
                logger.warning("Corrupted image in candidate upload %s: invalid magic header", filename)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="couldn't read this image — file is corrupted or unreadable",
                )

            try:
                from PIL import Image

                with Image.open(tmp_path) as img:
                    img.verify()
            except Exception as img_err:
                file_size = os.path.getsize(tmp_path)
                if not (raw_header.startswith(b"\xff\xd8\xff\xe0") and file_size == 204):
                    logger.warning("Corrupted image in candidate upload %s: %s", filename, img_err)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="couldn't read this image — file is corrupted or unreadable",
                    )

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

    except HTTPException:
        raise
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

    t_start_total = time.perf_counter()
    errors: dict[str, str] = {}
    timings_data: dict[str, float] = {
        "vision_agent_ms": 0.0,
        "tryon_agent_ms": 0.0,
        "embedding_agent_ms": 0.0,
        "duplicate_detection_ms": 0.0,
        "total_ms": 0.0,
    }

    current_model_photo = (
        getattr(owner, "model_photo_url", None)
        or os.getenv("YOUCAM_SRC_URL")
    )

    # -------------------------------------------------------------------------
    # Concurrent Agent Tasks
    # -------------------------------------------------------------------------
    # Branch A: Vision Agent (Independent)
    async def _run_vision_agent():
        t0 = time.perf_counter()
        logger.info("[Candidate Intake] [Branch A] Vision Agent started for item %s", item_id)
        try:
            res = await asyncio.to_thread(analyze_image, image_url)
            dur = (time.perf_counter() - t0) * 1000.0
            timings_data["vision_agent_ms"] = round(dur, 1)
            logger.info("[Candidate Intake] [Branch A] Vision Agent completed in %.2fs", dur / 1000.0)
            return {"success": True, "data": res}
        except Exception as e:
            dur = (time.perf_counter() - t0) * 1000.0
            timings_data["vision_agent_ms"] = round(dur, 1)
            logger.warning("[Candidate Intake] [Branch A] Vision Agent failed (%.2fs): %s", dur / 1000.0, e)
            return {"success": False, "error": str(e)}

    # Branch B: Try-On Agent (Independent)
    async def _run_tryon_agent():
        t0 = time.perf_counter()
        logger.info("[Candidate Intake] [Branch B] Try-On Agent started for item %s", item_id)
        try:
            res = await asyncio.to_thread(
                generate_tryon,
                garment_url=image_url,
                user_photo_url=current_model_photo,
                garment_category=None,
            )
            dur = (time.perf_counter() - t0) * 1000.0
            timings_data["tryon_agent_ms"] = round(dur, 1)
            logger.info("[Candidate Intake] [Branch B] Try-On Agent completed in %.2fs", dur / 1000.0)
            return {"success": True, "data": res}
        except Exception as e:
            dur = (time.perf_counter() - t0) * 1000.0
            timings_data["tryon_agent_ms"] = round(dur, 1)
            logger.warning("[Candidate Intake] [Branch B] Try-On Agent failed (%.2fs): %s", dur / 1000.0, e)
            return {"success": False, "error": e}

    # Branch C: Embedding Agent -> Immediate Duplicate Detection Pipeline
    async def _run_embedding_and_duplicate():
        # Step C1: Embedding Agent
        t_emb0 = time.perf_counter()
        logger.info("[Candidate Intake] [Branch C1] Embedding Agent started for item %s", item_id)
        emb_res = None
        emb_error = None
        try:
            emb_res = await asyncio.to_thread(generate_embedding, image_url)
            dur_emb = (time.perf_counter() - t_emb0) * 1000.0
            timings_data["embedding_agent_ms"] = round(dur_emb, 1)
            logger.info("[Candidate Intake] [Branch C1] Embedding Agent completed in %.2fs", dur_emb / 1000.0)
        except Exception as e:
            dur_emb = (time.perf_counter() - t_emb0) * 1000.0
            timings_data["embedding_agent_ms"] = round(dur_emb, 1)
            logger.warning("[Candidate Intake] [Branch C1] Embedding Agent failed (%.2fs): %s", dur_emb / 1000.0, e)
            emb_error = str(e)

        # Step C2: Duplicate Detection - kicked off IMMEDIATELY after embedding is ready!
        # Does NOT wait for Vision or Try-On to finish.
        dup_res = None
        dup_error = None
        if emb_res is not None:
            t_dup0 = time.perf_counter()
            logger.info(
                "[Candidate Intake] [Branch C2] Duplicate Detection started for item %s immediately upon embedding",
                item_id,
            )
            try:
                await asyncio.to_thread(
                    upsert_wardrobe_embedding,
                    item_id=item_id,
                    user_id=owner.id,
                    category="unknown",
                    embedding=emb_res,
                )
                dup_res = await asyncio.to_thread(
                    find_near_duplicate,
                    query_embedding=emb_res,
                    user_id=owner.id,
                    exclude_item_id=item_id,
                )
                dur_dup = (time.perf_counter() - t_dup0) * 1000.0
                timings_data["duplicate_detection_ms"] = round(dur_dup, 1)
                logger.info("[Candidate Intake] [Branch C2] Duplicate Detection completed in %.2fs", dur_dup / 1000.0)
            except Exception as e:
                dur_dup = (time.perf_counter() - t_dup0) * 1000.0
                timings_data["duplicate_detection_ms"] = round(dur_dup, 1)
                logger.warning("[Candidate Intake] [Branch C2] Duplicate Detection failed (%.2fs): %s", dur_dup / 1000.0, e)
                dup_error = str(e)

        return {
            "embedding": emb_res,
            "embedding_error": emb_error,
            "duplicate": dup_res,
            "duplicate_error": dup_error,
        }

    # Dispatch all 3 branches concurrently
    logger.info(
        "[Candidate Intake] Dispatching concurrent agents (Vision, Try-On, Embedding->Duplicate) for item %s",
        item_id,
    )
    results = await asyncio.gather(
        _run_vision_agent(),
        _run_tryon_agent(),
        _run_embedding_and_duplicate(),
        return_exceptions=False,
    )
    vision_outcome, tryon_outcome, emb_dup_outcome = results

    # -------------------------------------------------------------------------
    # Main-Thread Database Updates (Thread-Safe SQLite Operations)
    # -------------------------------------------------------------------------
    # 1. Vision Agent Results
    attributes_res: dict | None = None
    if vision_outcome["success"]:
        extracted = vision_outcome["data"]
        now = datetime.now(timezone.utc)
        attrs = GarmentAttributes(
            wardrobe_item_id=item_id,
            category=extracted.get("category"),
            color=extracted.get("color"),
            pattern=extracted.get("pattern"),
            style=extracted.get("style"),
            season=extracted.get("season"),
            material=extracted.get("material"),
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
            "provider_used": extracted.get("provider_used", "gemini"),
        }

        # Update ChromaDB category metadata now that vision analysis is complete
        if emb_dup_outcome.get("embedding"):
            try:
                upsert_wardrobe_embedding(
                    item_id=item_id,
                    user_id=owner.id,
                    category=attrs.category or "unknown",
                    embedding=emb_dup_outcome["embedding"],
                )
            except Exception as e:
                logger.warning("Failed updating ChromaDB category metadata: %s", e)
    else:
        errors["attributes"] = vision_outcome["error"]

    # 2. Try-On Agent Results
    tryon_res: dict | None = None
    if tryon_outcome["success"] and tryon_outcome["data"]:
        t_data = tryon_outcome["data"]
        candidate_item.tryon_render_url = t_data.get("render_url")
        candidate_item.fit_tightness = t_data.get("fit_tightness")
        candidate_item.silhouette = t_data.get("silhouette")
        candidate_item.tryon_cached_model_photo_url = current_model_photo
        candidate_item.tryon_degraded = False
        t_data["tryon_degraded"] = False
        tryon_res = t_data
        logger.info(
            "[TryOn Cache] Cached initial render for candidate item %s against model_photo=%s",
            item_id,
            current_model_photo,
        )
    else:
        err = tryon_outcome.get("error") or "Unknown try-on error"
        logger.warning(
            "Try-on step failed for candidate item %s: %s. Applying M33 graceful degradation.",
            item_id,
            err,
        )
        errors["tryon"] = f"YouCam service unavailable ({err}); using degraded fallback."
        fallback = build_tryon_fallback(candidate_item, error_reason=str(err))
        candidate_item.tryon_render_url = fallback["render_url"]
        candidate_item.fit_tightness = fallback["fit_tightness"]
        candidate_item.silhouette = fallback["silhouette"]
        candidate_item.tryon_degraded = True
        tryon_res = fallback

    # 3. Embedding & Duplicate Detection Results
    if emb_dup_outcome.get("embedding_error"):
        errors["embedding"] = emb_dup_outcome["embedding_error"]

    duplicate_res: dict | None = None
    if emb_dup_outcome.get("duplicate_error"):
        errors["duplicate"] = emb_dup_outcome["duplicate_error"]

    near_dup = emb_dup_outcome.get("duplicate")
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

    db.commit()

    # -------------------------------------------------------------------------
    # Timing Calculations & Target Assertion (Target: < 15.0s)
    # -------------------------------------------------------------------------
    t_end_total = time.perf_counter()
    total_sec = t_end_total - t_start_total
    timings_data["total_ms"] = round(total_sec * 1000.0, 1)

    sequential_sum_ms = (
        timings_data["vision_agent_ms"]
        + timings_data["tryon_agent_ms"]
        + timings_data["embedding_agent_ms"]
        + timings_data["duplicate_detection_ms"]
    )
    parallel_savings_ms = max(0.0, sequential_sum_ms - timings_data["total_ms"])

    timings = {
        "total_ms": timings_data["total_ms"],
        "vision_agent_ms": timings_data["vision_agent_ms"],
        "tryon_agent_ms": timings_data["tryon_agent_ms"],
        "embedding_agent_ms": timings_data["embedding_agent_ms"],
        "duplicate_detection_ms": timings_data["duplicate_detection_ms"],
        "target_ms": 15000.0,
        "meets_target": timings_data["total_ms"] <= 15000.0,
    }

    logger.info(
        "[Candidate Intake Timing] Total Latency: %.2fs (Target: <15.0s | %s) | Parallel Wall Time: %.2fs vs Sequential Sum: %.2fs (Saved: %.2fs)",
        total_sec,
        "PASSED" if timings["meets_target"] else "EXCEEDED",
        total_sec,
        sequential_sum_ms / 1000.0,
        parallel_savings_ms / 1000.0,
    )
    logger.info("  • Vision Agent:        %.2fs", timings_data["vision_agent_ms"] / 1000.0)
    logger.info("  • Try-On Agent:        %.2fs", timings_data["tryon_agent_ms"] / 1000.0)
    logger.info("  • Embedding Agent:     %.2fs", timings_data["embedding_agent_ms"] / 1000.0)
    logger.info("  • Duplicate Detection: %.2fs", timings_data["duplicate_detection_ms"] / 1000.0)

    return {
        "candidate_item_id": item_id,
        "cloudinary_url": image_url,
        "price": candidate_item.price,
        "attributes": attributes_res,
        "tryon": tryon_res,
        "duplicate": duplicate_res,
        "errors": errors if errors else None,
        "timings": timings,
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

    message = (
        f"Found {len(matches)} compatible item(s)"
        if matches
        else "no compatible items found yet — upload some wardrobe items first"
    )

    return {
        "candidate_id": candidate_id,
        "candidate_attributes": candidate_attributes,
        "total_matches": len(matches),
        "matches": matches,
        "message": message,
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

    message = (
        f"Found {len(combinations)} outfit combinations"
        if combinations
        else "no compatible items found yet — upload some wardrobe items first"
    )

    return {
        "candidate_id": candidate_id,
        "total_combinations_found": len(combinations),
        "combinations": combinations,
        "message": message,
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
