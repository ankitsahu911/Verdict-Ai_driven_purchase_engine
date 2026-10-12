import os
import sys
import shutil
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.db import SessionLocal
from app.models import GarmentAttributes, ExtractionSource, WardrobeItem, User
from app.services.chroma_service import (
    upsert_wardrobe_embedding,
    find_near_duplicate,
    get_wardrobe_collection,
    normalize_category,
)
from app.services.embedding_service import generate_embedding
from app.decision_engine.orchestrator import synthesize_buy_score

USER_UPLOADED_JACKET = Path(r"C:\Users\anknk\.gemini\antigravity\brain\e4a68fd5-c9b8-4166-b243-53401a90c575\.user_uploaded\media_1791612160033_87ecc36f.png")
UPLOADS_DIR = BACKEND_DIR / "data" / "uploads"
JACKET_FILENAME = "outerwear_06_rust_bomber_jacket.png"
DEST_JACKET_PATH = UPLOADS_DIR / JACKET_FILENAME

def main():
    db = SessionLocal()
    demo_user = db.query(User).filter(User.firebase_uid == "demo_user_wardrobe").first()
    if not demo_user:
        print("Demo user not found!")
        return

    print(f"Demo user found: ID={demo_user.id}, UID={demo_user.firebase_uid}")

    # 1. Copy user uploaded photo to uploads directory
    if USER_UPLOADED_JACKET.exists():
        shutil.copyfile(str(USER_UPLOADED_JACKET), str(DEST_JACKET_PATH))
        print(f"[OK] Copied jacket photo to {DEST_JACKET_PATH}")
    else:
        # Fallback to candidate 46 file
        cand46_file = UPLOADS_DIR / "c3cbd2b523174f7abbb178e2ef30fd9c_tmp74m3c6du.png"
        if cand46_file.exists():
            shutil.copyfile(str(cand46_file), str(DEST_JACKET_PATH))
            print(f"[OK] Copied cand46 photo to {DEST_JACKET_PATH}")

    # 2. Check or create wardrobe item for the rust bomber jacket
    jacket_item = db.query(WardrobeItem).filter(
        WardrobeItem.user_id == demo_user.id,
        WardrobeItem.is_candidate == False,
        WardrobeItem.cloudinary_url.like(f"%{JACKET_FILENAME}%")
    ).first()

    now_utc = datetime.now(timezone.utc)
    if not jacket_item:
        jacket_item = WardrobeItem(
            user_id=demo_user.id,
            is_candidate=False,
            cloudinary_url=f"http://localhost:8000/api/uploads/{JACKET_FILENAME}",
            cloudinary_public_id=f"local/wardrobe/{JACKET_FILENAME}",
            price=89.0,
            uploaded_at=now_utc,
        )
        db.add(jacket_item)
        db.commit()
        db.refresh(jacket_item)
        print(f"[OK] Created new WardrobeItem for Rust Bomber Jacket: ID={jacket_item.id}")
    else:
        print(f"[OK] Existing WardrobeItem found for Rust Bomber Jacket: ID={jacket_item.id}")

    # Attributes for jacket
    attrs = db.query(GarmentAttributes).filter(GarmentAttributes.wardrobe_item_id == jacket_item.id).first()
    if not attrs:
        attrs = GarmentAttributes(
            wardrobe_item_id=jacket_item.id,
            category="outerwear",
            color="rust brown",
            pattern="solid",
            style="casual",
            season="all-season",
            material="synthetic",
            extraction_source=ExtractionSource.AI,
            updated_at=now_utc,
        )
        db.add(attrs)
    else:
        attrs.category = "outerwear"
        attrs.color = "rust brown"
        attrs.pattern = "solid"
        attrs.style = "casual"
        attrs.season = "all-season"
        attrs.material = "synthetic"
        attrs.extraction_source = ExtractionSource.AI
        attrs.updated_at = now_utc
    db.commit()
    print(f"[OK] Updated attributes for jacket item {jacket_item.id}: {attrs.category}, {attrs.color}")

    # 3. Clean up ALL candidate IDs from ChromaDB
    chroma_col = get_wardrobe_collection()
    cand_items = db.query(WardrobeItem).filter(WardrobeItem.is_candidate == True).all()
    cand_ids = [str(c.id) for c in cand_items]
    existing_chroma_ids = chroma_col.get()["ids"]
    to_delete = [cid for cid in cand_ids if cid in existing_chroma_ids]
    if to_delete:
        chroma_col.delete(ids=to_delete)
        print(f"[OK] Deleted {len(to_delete)} candidate IDs from ChromaDB wardrobe collection.")

    # 4. Backfill ChromaDB embeddings for ALL wardrobe items of demo user
    wardrobe_items = db.query(WardrobeItem).filter(
        WardrobeItem.user_id == demo_user.id,
        WardrobeItem.is_candidate == False
    ).all()
    print(f"\nBackfilling embeddings for {len(wardrobe_items)} wardrobe items...")

    success_emb = 0
    for it in wardrobe_items:
        # Determine local path
        fname = it.cloudinary_url.split("/")[-1] if it.cloudinary_url else ""
        local_p = UPLOADS_DIR / fname
        if not local_p.exists():
            continue
        try:
            emb = generate_embedding(str(local_p))
            cat = it.attributes.category if it.attributes else "unknown"
            upsert_wardrobe_embedding(
                item_id=it.id,
                user_id=demo_user.id,
                category=cat,
                embedding=emb,
            )
            success_emb += 1
        except Exception as e:
            print(f"  Failed embedding for item {it.id}: {e}")

    print(f"[OK] Successfully embedded {success_emb} items into ChromaDB.")

    # 5. Test duplicate detection for candidate 46
    cand_46 = db.query(WardrobeItem).filter(WardrobeItem.id == 46).first()
    if cand_46:
        print(f"\nRe-evaluating Candidate 46 against Wardrobe...")
        emb_46 = generate_embedding(cand_46.cloudinary_url)
        cand_cat = cand_46.attributes.category if cand_46.attributes else "outerwear"
        dup_match = find_near_duplicate(
            query_embedding=emb_46,
            user_id=demo_user.id,
            exclude_item_id=cand_46.id,
            category=cand_cat,
        )
        print(f"Candidate 46 Duplicate Match Result: {dup_match}")

        if dup_match:
            cand_46.duplicate_match_item_id = dup_match["wardrobe_item_id"]
            cand_46.duplicate_similarity_pct = float(dup_match["similarity_percentage"])
            db.commit()

            # Resynthesize buy score
            res = synthesize_buy_score(candidate_item_id=cand_46.id, db=db, persist=True)
            print(f"\n--- CANDIDATE 46 DECISION RESULTS ---")
            print(f"Verdict: {res.verdict.upper()}")
            print(f"Overall Buy Score: {res.overall_score} / 100")
            print(f"Headline: {res.headline_reason}")
            matched_item = db.query(WardrobeItem).filter(WardrobeItem.id == dup_match['wardrobe_item_id']).first()
            print(f"Matched Item ID: {dup_match['wardrobe_item_id']}")
            print(f"Matched Category: {matched_item.attributes.category if matched_item and matched_item.attributes else 'unknown'}")
            print(f"Matched Image URL: {matched_item.cloudinary_url if matched_item else ''}")
            print(f"Similarity: {dup_match['similarity_percentage']}%")

    db.close()

if __name__ == "__main__":
    main()
