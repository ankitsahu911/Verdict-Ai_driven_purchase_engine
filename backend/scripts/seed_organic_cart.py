"""
Seeds the development database (verdict_dev.db) with:
1. Dev User ('dev_user_local')
2. Realistic existing wardrobe (3-4 owned pieces)
3. An organic, un-curated 4-item candidate cart for Milestone 38 UI walkthrough:
   - Beige Linen Shirt ($48.00)
   - Charcoal Slim Chinos ($62.00)
   - Olive Green Windbreaker ($115.00)
   - White Canvas Sneakers ($70.00)
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(dotenv_path=BACKEND_ROOT.parent / ".env")

from app.db import SessionLocal, Base, engine
from app.models import ExtractionSource, GarmentAttributes, User, WardrobeItem
from app.services.chroma_service import (
    get_wardrobe_collection,
    upsert_wardrobe_embedding,
)
from app.services.embedding_service import generate_embedding

# Ensure tables exist
Base.metadata.create_all(bind=engine)


def seed():
    db = SessionLocal()
    try:
        # Find or create dev user
        dev_uid = "dev_user_local"
        user = db.query(User).filter(User.firebase_uid == dev_uid).first()
        if not user:
            user = User(
                firebase_uid=dev_uid,
                email="dev@verdict.engine",
                display_name="Dev Tester",
                created_at=datetime.now(timezone.utc),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Created dev user: {user.email} (ID: {user.id})")
        else:
            print(f"Found existing dev user: {user.email} (ID: {user.id})")

        # Clear existing items for this user to make walkthrough clean and reproducible
        db.query(WardrobeItem).filter(WardrobeItem.user_id == user.id).delete()
        db.commit()

        try:
            col = get_wardrobe_collection()
            col.delete(where={"user_id": user.id})
        except Exception:
            pass

        print("\nSeeding owned wardrobe items...")
        owned_specs = [
            {
                "category": "top",
                "color": "navy",
                "pattern": "solid",
                "style": "casual",
                "season": "all-season",
                "material": "cotton",
                "price": 35.0,
                "url": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600",
            },
            {
                "category": "bottom",
                "color": "blue",
                "pattern": "solid",
                "style": "casual",
                "season": "all-season",
                "material": "denim",
                "price": 75.0,
                "url": "https://images.unsplash.com/photo-1560243563-062bfc001d68?w=600",
            },
            {
                "category": "outerwear",
                "color": "black",
                "pattern": "solid",
                "style": "smart-casual",
                "season": "winter",
                "material": "wool",
                "price": 160.0,
                "url": "https://images.unsplash.com/photo-1539533018447-63fcce2678e3?w=600",
            },
        ]

        for spec in owned_specs:
            item = WardrobeItem(
                user_id=user.id,
                cloudinary_url=spec["url"],
                is_candidate=False,
                price=spec["price"],
                fit_tightness="regular",
                silhouette="tailored",
                uploaded_at=datetime.now(timezone.utc),
            )
            db.add(item)
            db.commit()
            db.refresh(item)

            attrs = GarmentAttributes(
                wardrobe_item_id=item.id,
                category=spec["category"],
                color=spec["color"],
                pattern=spec["pattern"],
                style=spec["style"],
                season=spec["season"],
                material=spec["material"],
                extraction_source=ExtractionSource.MANUAL_OVERRIDE,
                updated_at=datetime.now(timezone.utc),
            )
            db.add(attrs)
            db.commit()

        print("Seeding organic, un-curated candidate cart (4 items)...")
        candidate_specs = [
            {
                "name": "Beige Linen Casual Shirt",
                "category": "top",
                "color": "beige",
                "pattern": "solid",
                "style": "casual",
                "season": "summer",
                "material": "linen",
                "price": 48.0,
                "fit_tightness": "regular",
                "silhouette": "relaxed",
                "url": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=600",
            },
            {
                "name": "Charcoal Slim-Fit Chinos",
                "category": "bottom",
                "color": "charcoal",
                "pattern": "solid",
                "style": "smart-casual",
                "season": "all-season",
                "material": "cotton",
                "price": 62.0,
                "fit_tightness": "slim",
                "silhouette": "tailored",
                "url": "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=600",
            },
            {
                "name": "Olive Green Windbreaker Jacket",
                "category": "outerwear",
                "color": "olive",
                "pattern": "solid",
                "style": "athletic",
                "season": "all-season",
                "material": "synthetic",
                "price": 115.0,
                "fit_tightness": "regular",
                "silhouette": "relaxed",
                "url": "https://images.unsplash.com/photo-1544441893-675973e31985?w=600",
            },
            {
                "name": "White Canvas Low-Top Sneakers",
                "category": "footwear",
                "color": "white",
                "pattern": "solid",
                "style": "casual",
                "season": "all-season",
                "material": "canvas",
                "price": 70.0,
                "fit_tightness": "regular",
                "silhouette": "regular",
                "url": "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=600",
            },
        ]

        for spec in candidate_specs:
            cand = WardrobeItem(
                user_id=user.id,
                cloudinary_url=spec["url"],
                is_candidate=True,
                price=spec["price"],
                fit_tightness=spec["fit_tightness"],
                silhouette=spec["silhouette"],
                tryon_render_url=spec["url"],
                tryon_degraded=False,
                uploaded_at=datetime.now(timezone.utc),
            )
            db.add(cand)
            db.commit()
            db.refresh(cand)

            attrs = GarmentAttributes(
                wardrobe_item_id=cand.id,
                category=spec["category"],
                color=spec["color"],
                pattern=spec["pattern"],
                style=spec["style"],
                season=spec["season"],
                material=spec["material"],
                extraction_source=ExtractionSource.MANUAL_OVERRIDE,
                updated_at=datetime.now(timezone.utc),
            )
            db.add(attrs)
            db.commit()
            print(f"  -> Candidate #{cand.id}: {spec['name']} (${spec['price']:.2f})")

        print("\nDatabase successfully seeded with organic candidate cart!")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
