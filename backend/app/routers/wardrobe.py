"""
Wardrobe routes: upload (M6) and attribute extraction (M7/M8).

Pixels in via multipart/form-data, rows out in Postgres. Vision Agent
extracts 6 attributes per item and caches results in the DB.
"""

import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import ExtractionSource, GarmentAttributes, User, WardrobeItem
from app.services.chroma_service import find_near_duplicate, upsert_wardrobe_embedding
from app.services.cloudinary_service import upload_image
from app.services.embedding_service import generate_embedding
from app.services.vision_service import VisionServiceError, analyze_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wardrobe", tags=["wardrobe"])

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
CHUNK_SIZE = 1024 * 1024


def get_or_create_user(db: Session, uid: str, email: str) -> User:
    """Find the user by Firebase UID, creating a `users` row on first login."""
    user = db.query(User).filter(User.firebase_uid == uid).first()
    if user is None:
        user = User(
            firebase_uid=uid,
            email=email,
            created_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.flush()
    return user


def _file_is_allowed(content_type: str, filename: str) -> bool:
    if content_type in ALLOWED_CONTENT_TYPES:
        return True
    ext = Path(filename).suffix.lower()
    return ext in {".jpg", ".jpeg", ".png", ".webp"}


def _stream_to_temp(upload: UploadFile) -> tuple[str, int]:
    """Write the uploaded file to a temp file, enforcing the size limit.

    Returns (temp_path, byte_count). Raises ValueError if over the limit.
    """
    suffix = Path(upload.filename or "upload").suffix or ".jpg"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp_path = tmp.name
    size = 0
    try:
        while True:
            chunk = upload.file.read(CHUNK_SIZE)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                limit_mb = MAX_FILE_BYTES // (1024 * 1024)
                raise ValueError(
                    f"{upload.filename} exceeds the {limit_mb}MB limit"
                )
            tmp.write(chunk)
    except Exception:
        tmp.close()
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    finally:
        tmp.close()
    return tmp_path, size


@router.post("/upload")
async def upload_wardrobe_photos(
    files: List[UploadFile] = File(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload one or more photos to Cloudinary and record them as wardrobe items.

    Each file is handled independently: a failing file is skipped and reported
    in `failed` rather than aborting the batch.
    """
    owner = get_or_create_user(db, user["uid"], user["email"])

    uploaded: list[dict] = []
    failed: list[dict] = []

    for upload in files:
        filename = upload.filename or "unnamed"

        if not _file_is_allowed(upload.content_type or "", filename):
            failed.append(
                {
                    "filename": filename,
                    "error": (
                        "Unsupported file type. Only JPG, PNG and WebP "
                        "are allowed."
                    ),
                }
            )
            continue

        tmp_path: str | None = None
        try:
            tmp_path, _size = _stream_to_temp(upload)
            public_id = f"verdict/{owner.firebase_uid}/{uuid.uuid4().hex}"
            cloud = upload_image(tmp_path, public_id=public_id)

            # Savepoint so a failing insert rolls back only this file.
            with db.begin_nested():
                item = WardrobeItem(
                    user_id=owner.id,
                    cloudinary_url=cloud["url"],
                    cloudinary_public_id=cloud["public_id"],
                    is_candidate=False,
                    uploaded_at=datetime.now(timezone.utc),
                )
                db.add(item)
                db.flush()
                db.refresh(item)

            # Generate CLIP embedding and store in ChromaDB
            try:
                embedding = generate_embedding(item.cloudinary_url)
                upsert_wardrobe_embedding(
                    item_id=item.id,
                    user_id=owner.id,
                    category="unknown",
                    embedding=embedding,
                )
            except Exception as embed_err:
                logger.warning(
                    "Embedding generation skipped/failed for item %s: %s",
                    item.id,
                    embed_err,
                )

            uploaded.append(
                {
                    "id": item.id,
                    "filename": filename,
                    "url": item.cloudinary_url,
                    "public_id": item.cloudinary_public_id,
                }
            )
        except Exception as e:
            failed.append({"filename": filename, "error": str(e)})
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    db.commit()

    return {"uploaded": uploaded, "failed": failed}


_EXTRACTED_FIELDS = ("category", "color", "pattern", "style", "season", "material")


class AttributeUpdate(BaseModel):
    category: str | None = None
    color: str | None = None
    pattern: str | None = None
    style: str | None = None
    season: str | None = None
    material: str | None = None


def _serialize_item(item: WardrobeItem) -> dict:
    """Serialize a wardrobe item with its attributes for the grid view."""
    attrs = item.attributes
    return {
        "id": item.id,
        "cloudinary_url": item.cloudinary_url,
        "uploaded_at": item.uploaded_at.isoformat(),
        "attributes": (
            {
                "category": attrs.category,
                "color": attrs.color,
                "pattern": attrs.pattern,
                "style": attrs.style,
                "season": attrs.season,
                "material": attrs.material,
                "extraction_source": attrs.extraction_source.value
                if attrs.extraction_source
                else None,
            }
            if attrs
            else None
        ),
    }


@router.get("")
async def list_wardrobe_items(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all wardrobe items for the logged-in user with their attributes."""
    owner = get_or_create_user(db, user["uid"], user["email"])
    items = (
        db.query(WardrobeItem)
        .filter(WardrobeItem.user_id == owner.id)
        .order_by(WardrobeItem.uploaded_at.desc())
        .all()
    )
    return [_serialize_item(it) for it in items]


@router.patch("/{item_id}/attributes")
async def update_attributes(
    item_id: int,
    payload: AttributeUpdate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Partially update garment attributes for a wardrobe item.

    Ownership is checked — returns 403 if the item doesn't belong to the
    caller. Sets ``extraction_source = manual_override`` on save.
    """
    owner = get_or_create_user(db, user["uid"], user["email"])

    item = db.query(WardrobeItem).filter(WardrobeItem.id == item_id).first()
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

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No attributes provided",
        )

    now = datetime.now(timezone.utc)
    attrs = item.attributes
    if attrs is None:
        attrs = GarmentAttributes(
            wardrobe_item_id=item.id,
            updated_at=now,
        )
        db.add(attrs)

    for field in ("category", "color", "pattern", "style", "season", "material"):
        if field in updates:
            setattr(attrs, field, updates[field] or None)

    attrs.extraction_source = ExtractionSource.MANUAL_OVERRIDE
    attrs.updated_at = now
    db.commit()
    db.refresh(attrs)

    return {
        "item_id": item.id,
        "attributes": {
            "category": attrs.category,
            "color": attrs.color,
            "pattern": attrs.pattern,
            "style": attrs.style,
            "season": attrs.season,
            "material": attrs.material,
            "extraction_source": attrs.extraction_source.value,
        },
    }


def _attrs_complete(attrs: GarmentAttributes | None) -> bool:
    """True when a row exists with extraction_source='ai' and all 6 fields."""
    if attrs is None or attrs.extraction_source != ExtractionSource.AI:
        return False
    return all(getattr(attrs, f) for f in _EXTRACTED_FIELDS)


@router.post("/{item_id}/analyze")
async def analyze_wardrobe_item(
    item_id: int,
    force: bool = Query(False, description="Re-run vision even if cached"),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Extract 6 garment attributes from an item's photo via the vision agent.

    On first call, runs Gemini vision and writes all 6 fields to the
    garment_attributes row. Subsequent calls return the cached row instantly
    unless ``?force=true`` is passed.

    Logs whether the request hit the cache or called the vision API.
    """
    owner = get_or_create_user(db, user["uid"], user["email"])

    item = db.query(WardrobeItem).filter(WardrobeItem.id == item_id).first()
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

    attrs = item.attributes

    if not force and _attrs_complete(attrs):
        logger.info(
            "CACHE HIT item=%s — all 6 attributes present, skipping vision call",
            item_id,
        )
        return {
            "id": attrs.id,
            "wardrobe_item_id": item.id,
            "category": attrs.category,
            "color": attrs.color,
            "pattern": attrs.pattern,
            "style": attrs.style,
            "season": attrs.season,
            "material": attrs.material,
            "extraction_source": attrs.extraction_source.value,
            "cached": True,
        }

    logger.info(
        "CACHE MISS item=%s force=%s — calling vision API",
        item_id,
        force,
    )

    try:
        extracted = analyze_image(item.cloudinary_url)
    except VisionServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e

    now = datetime.now(timezone.utc)

    if attrs is None:
        attrs = GarmentAttributes(
            wardrobe_item_id=item.id,
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
    else:
        attrs.category = extracted["category"]
        attrs.color = extracted["color"]
        attrs.pattern = extracted["pattern"]
        attrs.style = extracted["style"]
        attrs.season = extracted["season"]
        attrs.material = extracted["material"]
        attrs.extraction_source = ExtractionSource.AI
        attrs.updated_at = now

    db.commit()
    db.refresh(attrs)

    return {
        "id": attrs.id,
        "wardrobe_item_id": item.id,
        "category": attrs.category,
        "color": attrs.color,
        "pattern": attrs.pattern,
        "style": attrs.style,
        "season": attrs.season,
        "material": attrs.material,
        "extraction_source": attrs.extraction_source.value,
        "cached": False,
    }


class NearDuplicateCheckRequest(BaseModel):
    item_id: int | None = None
    image_url: str | None = None


@router.post("/near-duplicate")
async def check_near_duplicate(
    payload: NearDuplicateCheckRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Find near-duplicate item in logged-in user's wardrobe by embedding similarity.

    Requires either ``item_id`` or ``image_url`` in request payload.
    Queries ChromaDB scoped to logged-in user, excluding ``item_id`` if provided.
    Returns nearest match item details, cloudinary URL, and 0-100% similarity score.
    """
    owner = get_or_create_user(db, user["uid"], user["email"])

    image_url: str | None = None
    exclude_item_id: int | None = None

    if payload.item_id is not None:
        item = db.query(WardrobeItem).filter(WardrobeItem.id == payload.item_id).first()
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
        image_url = item.cloudinary_url
        exclude_item_id = item.id
    elif payload.image_url:
        image_url = payload.image_url
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either item_id or image_url must be provided",
        )

    try:
        embedding = generate_embedding(image_url)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate embedding for near-duplicate check: {err}",
        ) from err

    result = find_near_duplicate(
        query_embedding=embedding,
        user_id=owner.id,
        exclude_item_id=exclude_item_id,
    )

    if not result:
        return {
            "has_duplicate": False,
            "match": None,
        }

    matched_item_id = result["wardrobe_item_id"]
    matched_item = db.query(WardrobeItem).filter(WardrobeItem.id == matched_item_id).first()

    cloudinary_url = (
        matched_item.cloudinary_url
        if matched_item
        else result.get("metadata", {}).get("cloudinary_url", "")
    )
    category = (
        (matched_item.attributes.category if matched_item and matched_item.attributes else None)
        or result.get("metadata", {}).get("category")
        or "item"
    )

    similarity_pct = result["similarity_percentage"]
    message = f"{similarity_pct}% similar to a {category} you already own"

    return {
        "has_duplicate": True,
        "match": {
            "wardrobe_item_id": matched_item_id,
            "cloudinary_url": cloudinary_url,
            "similarity_percentage": similarity_pct,
            "distance": result["distance"],
            "category": category,
            "message": message,
        },
    }


@router.get("/{item_id}/near-duplicate")
async def get_item_near_duplicate(
    item_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get single nearest neighbor for an existing item among user's other wardrobe items."""
    return await check_near_duplicate(
        payload=NearDuplicateCheckRequest(item_id=item_id),
        user=user,
        db=db,
    )

