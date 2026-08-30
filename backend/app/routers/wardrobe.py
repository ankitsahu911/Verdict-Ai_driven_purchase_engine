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
    owner = get_or_create_user(db, user["uid"], user["email"])

    successful: list[dict] = []
    failed: list[dict] = []

    for file in files:
        filename = file.filename or "unknown.jpg"
        content_type = file.content_type or ""

        if not _file_is_allowed(content_type, filename):
            failed.append({
                "filename": filename,
                "error": "Unsupported file type. Only JPG, PNG, and WebP are allowed.",
            })
            continue

        tmp_path: str | None = None
        try:
            tmp_path, size_bytes = _stream_to_temp(file)
            public_id = f"verdict/wardrobe/{owner.firebase_uid}/{uuid.uuid4().hex}"
            cloud = upload_image(tmp_path, public_id=public_id)

            item = WardrobeItem(
                user_id=owner.id,
                cloudinary_url=cloud["url"],
                cloudinary_public_id=cloud["public_id"],
                uploaded_at=datetime.now(timezone.utc),
            )
            db.add(item)
            db.commit()
            db.refresh(item)

            try:
                embedding = generate_embedding(item.cloudinary_url)
                upsert_wardrobe_embedding(
                    item_id=item.id,
                    user_id=owner.id,
                    category="unknown",
                    embedding=embedding,
                )
            except Exception as emb_err:
                logger.warning(
                    "Background embedding generation failed for item %s: %s",
                    item.id,
                    emb_err,
                )

            successful.append({
                "id": item.id,
                "filename": filename,
                "cloudinary_url": item.cloudinary_url,
                "cloudinary_public_id": item.cloudinary_public_id,
                "uploaded_at": item.uploaded_at.isoformat(),
                "size_bytes": size_bytes,
            })
        except Exception as err:
            logger.error("Failed uploading %s: %s", filename, err)
            failed.append({
                "filename": filename,
                "error": str(err),
            })
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    return {
        "uploaded_count": len(successful),
        "failed_count": len(failed),
        "items": successful,
        "failed": failed,
    }


@router.get("")
async def list_wardrobe_items(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    owner = get_or_create_user(db, user["uid"], user["email"])

    query = (
        db.query(WardrobeItem)
        .filter(WardrobeItem.user_id == owner.id, WardrobeItem.is_candidate == False)
        .order_by(WardrobeItem.uploaded_at.desc())
    )
    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "items": [
            {
                "id": item.id,
                "cloudinary_url": item.cloudinary_url,
                "cloudinary_public_id": item.cloudinary_public_id,
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
            for item in items
        ],
    }


@router.get("/{item_id}")
async def get_wardrobe_item(
    item_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    return {
        "id": item.id,
        "cloudinary_url": item.cloudinary_url,
        "cloudinary_public_id": item.cloudinary_public_id,
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


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wardrobe_item(
    item_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    db.delete(item)
    db.commit()
    return None


@router.post("/{item_id}/extract-attributes")
async def extract_attributes_endpoint(
    item_id: int,
    force: bool = Query(
        False,
        description="Re-run AI extraction even if cached attributes already exist",
    ),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    if item.attributes and not force:
        attrs = item.attributes
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

    try:
        extracted = analyze_image(item.cloudinary_url)
    except VisionServiceError as err:
        logger.error("VisionServiceError extracting attributes for item %s: %s", item_id, err)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(err),
        ) from err

    now = datetime.now(timezone.utc)
    attrs = item.attributes

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
    return await check_near_duplicate(
        payload=NearDuplicateCheckRequest(item_id=item_id),
        user=user,
        db=db,
    )
