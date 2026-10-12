import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.db import SessionLocal
from app.models import GarmentAttributes, ExtractionSource, WardrobeItem, User
from app.services.chroma_service import upsert_wardrobe_embedding, find_near_duplicate, get_wardrobe_collection
from app.services.embedding_service import generate_embedding
from app.decision_engine.orchestrator import synthesize_buy_score

def sync_dress():
    db = SessionLocal()
    demo_user = db.query(User).filter(User.firebase_uid == "demo_user_wardrobe").first()
    if not demo_user:
        print("Demo user not found!")
        return

    print(f"Demo user found: ID={demo_user.id}, UID={demo_user.firebase_uid}")

    # 1. Fix any local filesystem paths in wardrobe_items to HTTP URLs
    all_items = db.query(WardrobeItem).filter(WardrobeItem.user_id == demo_user.id).all()
    for it in all_items:
        if it.cloudinary_url and ("\\" in it.cloudinary_url or "C:" in it.cloudinary_url):
            fname = Path(it.cloudinary_url).name
            it.cloudinary_url = f"http://localhost:8000/api/uploads/{fname}"
            print(f"Normalized item {it.id} url to: {it.cloudinary_url}")
    db.commit()

    # 2. Check item 36 (the floral dress wardrobe item)
    item_36 = db.query(WardrobeItem).filter(WardrobeItem.id == 36).first()
    if not item_36:
        # Create it if not present
        item_36 = WardrobeItem(
            id=36,
            user_id=demo_user.id,
            is_candidate=False,
            cloudinary_url="http://localhost:8000/api/uploads/dress_04_light_blue_floral.png",
            cloudinary_public_id="local/wardrobe/dress_04_light_blue_floral.png",
            price=68.0,
        )
        db.add(item_36)
        db.commit()
        db.refresh(item_36)
    else:
        item_36.is_candidate = False
        item_36.price = 68.0
        item_36.cloudinary_url = "http://localhost:8000/api/uploads/dress_04_light_blue_floral.png"
        item_36.cloudinary_public_id = "local/wardrobe/dress_04_light_blue_floral.png"
        db.commit()

    # 3. Attributes for item 36
    from datetime import datetime, timezone
    attrs = db.query(GarmentAttributes).filter(GarmentAttributes.wardrobe_item_id == item_36.id).first()
    now_utc = datetime.now(timezone.utc)
    if not attrs:
        attrs = GarmentAttributes(
            wardrobe_item_id=item_36.id,
            category="dress",
            color="light blue",
            pattern="floral",
            style="casual",
            season="summer",
            material="chiffon",
            extraction_source=ExtractionSource.AI,
            updated_at=now_utc,
        )
        db.add(attrs)
    else:
        attrs.category = "dress"
        attrs.color = "light blue"
        attrs.pattern = "floral"
        attrs.style = "casual"
        attrs.season = "summer"
        attrs.material = "chiffon"
        attrs.extraction_source = ExtractionSource.AI
        attrs.updated_at = now_utc
    db.commit()
    print(f"Updated item 36 attributes: category={attrs.category}, color={attrs.color}, pattern={attrs.pattern}")

    # 4. Generate CLIP embedding from dress_04_light_blue_floral.png
    dress_path = BACKEND_DIR / "data" / "uploads" / "dress_04_light_blue_floral.png"
    if not dress_path.exists():
        print(f"Error: {dress_path} does not exist!")
        return

    print("Generating 512-dim CLIP embedding for dress_04_light_blue_floral.png...")
    emb = generate_embedding(str(dress_path))
    print(f"Generated embedding vector: len={len(emb)}, sample={emb[:3]}...")

    # Upsert into ChromaDB
    upsert_wardrobe_embedding(
        item_id=item_36.id,
        user_id=demo_user.id,
        category="dress",
        embedding=emb,
    )
    print(f"Successfully upserted item {item_36.id} into ChromaDB collection 'wardrobe_items'.")

    # 5. Test duplicate detection: candidate 37 (or 38)
    # Check if duplicate detection matches item 36
    dup_match = find_near_duplicate(
        query_embedding=emb,
        user_id=demo_user.id,
        exclude_item_id=9999, # don't exclude 36
    )
    print(f"Duplicate match check against self: {dup_match}")

    # 6. Test evaluating candidate 37
    cand_37 = db.query(WardrobeItem).filter(WardrobeItem.id == 37).first()
    if cand_37:
        cand_emb = generate_embedding(cand_37.cloudinary_url)
        cand_dup = find_near_duplicate(
            query_embedding=cand_emb,
            user_id=demo_user.id,
            exclude_item_id=cand_37.id,
        )
        print(f"\nCandidate 37 duplicate match against wardrobe: {cand_dup}")
        if cand_dup:
            cand_37.duplicate_match_item_id = cand_dup["wardrobe_item_id"]
            cand_37.duplicate_similarity_pct = float(cand_dup["similarity_percentage"])
            db.commit()

        # Run synthesize buy score
        res = synthesize_buy_score(candidate_item_id=cand_37.id, db=db, persist=True)
        print("\n--- BUY SCORE RESULT FOR CANDIDATE 37 ---")
        print(f"Overall Buy Score: {res.overall_score} / 100")
        print(f"Verdict: {res.verdict.upper()}")
        print(f"Headline Reason: {res.headline_reason}")
        for ax in res.axes:
            print(f"  - [{ax.axis}]: {ax.score:.1f} | {ax.reason}")

    db.close()

if __name__ == "__main__":
    sync_dress()
