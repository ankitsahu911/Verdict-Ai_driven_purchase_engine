import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw, ImageFont

from app.db import SessionLocal
from app.models import User, WardrobeItem, GarmentAttributes, ExtractionSource
from app.decision_engine.subset_evaluator import evaluate_and_rank_subsets
from app.services.chroma_service import upsert_wardrobe_embedding
from app.services.embedding_service import generate_embedding

UPLOADS_DIR = Path(__file__).resolve().parent.parent / "data" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

CANDIDATES_SPEC = [
    {
        "code": "A",
        "name": "Designer Slim-Fit White Cotton Tee (Near-Duplicate & Poor Fit)",
        "category": "top",
        "color": "white",
        "pattern": "solid",
        "style": "casual",
        "season": "spring",
        "material": "cotton",
        "price": 280.0,
        "fit_tightness": "tight",
        "silhouette": "skinny",
        "duplicate_similarity_pct": 96.0,
        "duplicate_match_item_id": 8,  # Matches #8 White Crewneck Tee
        "bg_color": (245, 245, 245),
        "text_color": (30, 30, 30),
        "filename": "demo_cand_01_white_tee.jpg",
    },
    {
        "code": "B",
        "name": "Classic Beige Double-Breasted Trench (Versatile Gap-Filler)",
        "category": "outerwear",
        "color": "beige",
        "pattern": "solid",
        "style": "smart-casual",
        "season": "all-season",
        "material": "cotton",
        "price": 135.0,
        "fit_tightness": "regular",
        "silhouette": "tailored",
        "duplicate_similarity_pct": None,
        "duplicate_match_item_id": None,
        "bg_color": (218, 196, 163),
        "text_color": (40, 30, 20),
        "filename": "demo_cand_02_beige_trench.jpg",
    },
    {
        "code": "C",
        "name": "Olive Merino Knit Longsleeve Polo (Ambiguous)",
        "category": "top",
        "color": "olive",
        "pattern": "solid",
        "style": "smart-casual",
        "season": "fall",
        "material": "wool",
        "price": 78.0,
        "fit_tightness": "slim",
        "silhouette": "tailored",
        "duplicate_similarity_pct": None,
        "duplicate_match_item_id": None,
        "bg_color": (85, 95, 65),
        "text_color": (240, 240, 230),
        "filename": "demo_cand_03_olive_polo.jpg",
    },
    {
        "code": "D",
        "name": "Rust Corduroy Overshirt (Ambiguous)",
        "category": "top",
        "color": "brown",
        "pattern": "solid",
        "style": "casual",
        "season": "fall",
        "material": "corduroy",
        "price": 68.0,
        "fit_tightness": "regular",
        "silhouette": "relaxed",
        "duplicate_similarity_pct": None,
        "duplicate_match_item_id": None,
        "bg_color": (165, 82, 55),
        "text_color": (250, 245, 240),
        "filename": "demo_cand_04_rust_shacket.jpg",
    },
]


def create_garment_image(filepath: Path, label: str, bg_color: tuple, text_color: tuple):
    img = Image.new("RGB", (600, 600), color=bg_color)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([30, 30, 570, 570], radius=24, outline=text_color, width=4)
    # Draw label bar
    draw.rectangle([50, 480, 550, 540], fill=(20, 20, 20))
    draw.text((65, 500), label.upper(), fill=(255, 255, 255))
    img.save(filepath, format="JPEG", quality=90)


def seed():
    db = SessionLocal()
    try:
        demo_user = db.query(User).filter(User.firebase_uid == "demo_user_wardrobe").first()
        if not demo_user:
            raise RuntimeError("Demo user not found!")

        # Delete any existing candidate items for demo user to ensure clean state
        existing_cands = db.query(WardrobeItem).filter(
            WardrobeItem.user_id == demo_user.id,
            WardrobeItem.is_candidate == True,
        ).all()
        for ec in existing_cands:
            if ec.attributes:
                db.delete(ec.attributes)
            db.delete(ec)
        db.commit()

        white_tee = (
            db.query(WardrobeItem)
            .join(GarmentAttributes)
            .filter(
                WardrobeItem.user_id == demo_user.id,
                WardrobeItem.is_candidate == False,
                GarmentAttributes.category == "top",
                GarmentAttributes.color == "white",
            )
            .first()
        )
        matched_item_id = white_tee.id if white_tee else None

        created_cands = []
        for spec in CANDIDATES_SPEC:
            img_path = UPLOADS_DIR / spec["filename"]
            create_garment_image(
                img_path,
                f"{spec['category']}: {spec['color']} {spec['material']}",
                spec["bg_color"],
                spec["text_color"],
            )

            url = f"http://localhost:8000/api/uploads/{spec['filename']}"
            dup_id = matched_item_id if spec["duplicate_match_item_id"] is not None else None
            item = WardrobeItem(
                user_id=demo_user.id,
                cloudinary_url=url,
                cloudinary_public_id=f"demo_candidate_{spec['code'].lower()}",
                is_candidate=True,
                price=spec["price"],
                fit_tightness=spec["fit_tightness"],
                silhouette=spec["silhouette"],
                duplicate_similarity_pct=spec["duplicate_similarity_pct"],
                duplicate_match_item_id=dup_id,
                uploaded_at=datetime.now(timezone.utc),
            )
            db.add(item)
            db.flush()

            attrs = GarmentAttributes(
                wardrobe_item_id=item.id,
                category=spec["category"],
                color=spec["color"],
                pattern=spec["pattern"],
                style=spec["style"],
                season=spec["season"],
                material=spec["material"],
                extraction_source=ExtractionSource.AI,
                updated_at=datetime.now(timezone.utc),
            )
            db.add(attrs)
            db.flush()

            # Upsert into ChromaDB
            try:
                emb = generate_embedding(url)
                upsert_wardrobe_embedding(
                    item_id=item.id,
                    user_id=demo_user.id,
                    category=spec["category"],
                    embedding=emb,
                )
            except Exception as e:
                print(f"Embedding warning for #{item.id}: {e}")

            created_cands.append(item)

        db.commit()
        cand_ids = [c.id for c in created_cands]
        print(f"Successfully seeded {len(created_cands)} candidate items: {cand_ids}")

        # Test What-If Evaluation
        print("\nEvaluating What-If Combinations...")
        ranked = evaluate_and_rank_subsets(cand_ids, db)
        print(f"Total Subsets Evaluated: {len(ranked)}")

        buy_count = sum(1 for r in ranked if r["verdict"].upper() == "BUY")
        consider_count = sum(1 for r in ranked if r["verdict"].upper() == "CONSIDER")
        skip_count = sum(1 for r in ranked if r["verdict"].upper() == "SKIP")

        print(f"\nVerdict Summary across 16 combinations:")
        print(f"  BUY: {buy_count}")
        print(f"  CONSIDER: {consider_count}")
        print(f"  SKIP: {skip_count}")

        for r in ranked:
            items_str = ", ".join(str(i) for i in r["item_ids"]) or "Skip all"
            print(f"  Rank #{r['rank']:2d} | Score: {r['overall_score']:5.1f} | Verdict: {r['verdict']:8s} | Items: [{items_str}] | {r['headline_reason'][:60]}...")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
