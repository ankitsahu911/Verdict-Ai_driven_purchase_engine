import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Ensure backend directory is in python path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.db import engine, SessionLocal
from app.models import Base, User, WardrobeItem, GarmentAttributes, ExtractionSource
from app.services.chroma_service import get_wardrobe_collection, upsert_wardrobe_embedding
from app.services.embedding_service import generate_embedding

PHOTOS_DIR = BACKEND_DIR / "data" / "demo_wardrobe_photos"
UPLOADS_DIR = BACKEND_DIR / "data" / "uploads"
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# 24-Item Curated Demo Wardrobe Specification Matrix
DEMO_WARDROBE_SPECS = [
    # --- TOPS (5 items) ---
    {
        "filename": "top_01_white_crewneck_tee.jpg",
        "category": "top",
        "name": "Classic White Crewneck Tee",
        "color": "white",
        "pattern": "solid",
        "style": "casual",
        "season": "all-season",
        "material": "cotton",
        "price": 28.0,
        "fit_tightness": "regular",
        "silhouette": "relaxed",
        "source_base": "candidate_1_white_tee.jpg",
        "bg_color": (245, 245, 245),
        "fg_color": (250, 250, 250),
    },
    {
        "filename": "top_02_blue_oxford_shirt.jpg",
        "category": "top",
        "name": "Light Blue Oxford Button-Down",
        "color": "light blue",
        "pattern": "solid",
        "style": "smart-casual",
        "season": "all-season",
        "material": "cotton",
        "price": 65.0,
        "fit_tightness": "regular",
        "silhouette": "tailored",
        "source_base": None,
        "bg_color": (230, 235, 245),
        "fg_color": (160, 195, 235),
    },
    {
        "filename": "top_03_grey_cashmere_sweater.jpg",
        "category": "top",
        "name": "Heather Grey Cashmere Crewneck",
        "color": "grey",
        "pattern": "solid",
        "style": "casual",
        "season": "winter",
        "material": "cashmere",
        "price": 120.0,
        "fit_tightness": "regular",
        "silhouette": "relaxed",
        "source_base": None,
        "bg_color": (225, 225, 230),
        "fg_color": (150, 150, 155),
    },
    {
        "filename": "top_04_striped_breton_tee.jpg",
        "category": "top",
        "name": "Nautical Striped Breton Long-Sleeve",
        "color": "navy white",
        "pattern": "striped",
        "style": "casual",
        "season": "spring",
        "material": "cotton",
        "price": 42.0,
        "fit_tightness": "regular",
        "silhouette": "relaxed",
        "source_base": None,
        "bg_color": (240, 240, 245),
        "fg_color": (30, 45, 80),
    },
    {
        "filename": "top_05_black_silk_blouse.jpg",
        "category": "top",
        "name": "Black Silk Evening Blouse",
        "color": "black",
        "pattern": "solid",
        "style": "formal",
        "season": "all-season",
        "material": "silk",
        "price": 85.0,
        "fit_tightness": "regular",
        "silhouette": "flowy",
        "source_base": None,
        "bg_color": (220, 220, 220),
        "fg_color": (25, 25, 25),
    },

    # --- BOTTOMS (5 items) ---
    {
        "filename": "bottom_01_dark_indigo_jeans.jpg",
        "category": "bottom",
        "name": "Dark Indigo Selvedge Denim",
        "color": "dark blue",
        "pattern": "solid",
        "style": "casual",
        "season": "all-season",
        "material": "denim",
        "price": 78.0,
        "fit_tightness": "regular",
        "silhouette": "straight",
        "source_base": "candidate_3_blue_jeans.jpg",
        "bg_color": (235, 235, 240),
        "fg_color": (30, 45, 85),
    },
    {
        "filename": "bottom_02_beige_tailored_chinos.jpg",
        "category": "bottom",
        "name": "Beige Tailored Stretch Chinos",
        "color": "beige",
        "pattern": "solid",
        "style": "smart-casual",
        "season": "spring",
        "material": "cotton",
        "price": 62.0,
        "fit_tightness": "slim",
        "silhouette": "tailored",
        "source_base": None,
        "bg_color": (245, 240, 230),
        "fg_color": (210, 190, 160),
    },
    {
        "filename": "bottom_03_charcoal_dress_trousers.jpg",
        "category": "bottom",
        "name": "Charcoal Wool Pleated Trousers",
        "color": "charcoal",
        "pattern": "solid",
        "style": "formal",
        "season": "all-season",
        "material": "wool",
        "price": 95.0,
        "fit_tightness": "regular",
        "silhouette": "straight",
        "source_base": None,
        "bg_color": (230, 230, 235),
        "fg_color": (60, 60, 65),
    },
    {
        "filename": "bottom_04_olive_cargo_pants.jpg",
        "category": "bottom",
        "name": "Olive Green Ripstop Cargo Pants",
        "color": "olive",
        "pattern": "solid",
        "style": "streetwear",
        "season": "fall",
        "material": "cotton",
        "price": 70.0,
        "fit_tightness": "regular",
        "silhouette": "relaxed",
        "source_base": None,
        "bg_color": (235, 240, 230),
        "fg_color": (85, 95, 60),
    },
    {
        "filename": "bottom_05_black_running_shorts.jpg",
        "category": "bottom",
        "name": "Performance Running Shorts",
        "color": "black",
        "pattern": "solid",
        "style": "athletic",
        "season": "summer",
        "material": "synthetic",
        "price": 38.0,
        "fit_tightness": "regular",
        "silhouette": "relaxed",
        "source_base": None,
        "bg_color": (235, 235, 235),
        "fg_color": (35, 35, 35),
    },

    # --- OUTERWEAR (5 items) ---
    {
        "filename": "outerwear_01_camel_wool_overcoat.jpg",
        "category": "outerwear",
        "name": "Camel Tailored Wool Overcoat",
        "color": "camel",
        "pattern": "solid",
        "style": "formal",
        "season": "winter",
        "material": "wool",
        "price": 195.0,
        "fit_tightness": "regular",
        "silhouette": "structured",
        "source_base": None,
        "bg_color": (245, 235, 220),
        "fg_color": (195, 145, 90),
    },
    {
        "filename": "outerwear_02_navy_tailored_blazer.jpg",
        "category": "outerwear",
        "name": "Navy Modern Fit Wool Blazer",
        "color": "navy",
        "pattern": "solid",
        "style": "smart-casual",
        "season": "all-season",
        "material": "wool blend",
        "price": 160.0,
        "fit_tightness": "regular",
        "silhouette": "tailored",
        "source_base": None,
        "bg_color": (225, 230, 240),
        "fg_color": (25, 40, 75),
    },
    {
        "filename": "outerwear_03_black_leather_jacket.jpg",
        "category": "outerwear",
        "name": "Black Moto Leather Biker Jacket",
        "color": "black",
        "pattern": "solid",
        "style": "streetwear",
        "season": "fall",
        "material": "leather",
        "price": 210.0,
        "fit_tightness": "slim",
        "silhouette": "structured",
        "source_base": "candidate_5_leather_jacket.jpg",
        "bg_color": (230, 230, 230),
        "fg_color": (20, 20, 20),
    },
    {
        "filename": "outerwear_04_olive_quilted_vest.jpg",
        "category": "outerwear",
        "name": "Olive Quilted Thermal Utility Vest",
        "color": "olive",
        "pattern": "quilted",
        "style": "casual",
        "season": "fall",
        "material": "synthetic",
        "price": 85.0,
        "fit_tightness": "regular",
        "silhouette": "relaxed",
        "source_base": "candidate_2_khaki_jacket.jpg",
        "bg_color": (235, 240, 230),
        "fg_color": (90, 100, 70),
    },
    {
        "filename": "outerwear_05_heather_grey_hoodie.jpg",
        "category": "outerwear",
        "name": "Heather Grey Zip Athletic Hoodie",
        "color": "heather grey",
        "pattern": "solid",
        "style": "casual",
        "season": "all-season",
        "material": "cotton fleece",
        "price": 55.0,
        "fit_tightness": "regular",
        "silhouette": "relaxed",
        "source_base": None,
        "bg_color": (235, 235, 240),
        "fg_color": (160, 160, 165),
    },

    # --- DRESSES (3 items) ---
    {
        "filename": "dress_01_navy_midi_shirt_dress.jpg",
        "category": "dress",
        "name": "Navy Belted Midi Shirt Dress",
        "color": "navy",
        "pattern": "solid",
        "style": "smart-casual",
        "season": "summer",
        "material": "cotton",
        "price": 98.0,
        "fit_tightness": "regular",
        "silhouette": "flowy",
        "source_base": None,
        "bg_color": (230, 235, 245),
        "fg_color": (30, 45, 80),
    },
    {
        "filename": "dress_02_little_black_dress.jpg",
        "category": "dress",
        "name": "Classic Black Crepe Cocktail Dress",
        "color": "black",
        "pattern": "solid",
        "style": "formal",
        "season": "all-season",
        "material": "crepe",
        "price": 110.0,
        "fit_tightness": "regular",
        "silhouette": "tailored",
        "source_base": "candidate_4_black_dress.jpg",
        "bg_color": (230, 230, 230),
        "fg_color": (25, 25, 25),
    },
    {
        "filename": "dress_03_floral_summer_maxi_dress.jpg",
        "category": "dress",
        "name": "Terracotta Floral Bohemian Maxi Dress",
        "color": "terracotta floral",
        "pattern": "floral",
        "style": "casual",
        "season": "summer",
        "material": "viscose",
        "price": 88.0,
        "fit_tightness": "regular",
        "silhouette": "flowy",
        "source_base": None,
        "bg_color": (245, 235, 230),
        "fg_color": (205, 110, 85),
    },

    # --- FOOTWEAR (4 items) ---
    {
        "filename": "footwear_01_white_minimalist_sneakers.jpg",
        "category": "footwear",
        "name": "White Minimalist Leather Sneakers",
        "color": "white",
        "pattern": "solid",
        "style": "casual",
        "season": "all-season",
        "material": "leather",
        "price": 90.0,
        "fit_tightness": "regular",
        "silhouette": "low-top",
        "source_base": None,
        "bg_color": (245, 245, 245),
        "fg_color": (240, 240, 240),
    },
    {
        "filename": "footwear_02_brown_suede_chelsea_boots.jpg",
        "category": "footwear",
        "name": "Cognac Brown Suede Chelsea Boots",
        "color": "brown",
        "pattern": "solid",
        "style": "smart-casual",
        "season": "fall",
        "material": "suede",
        "price": 145.0,
        "fit_tightness": "regular",
        "silhouette": "ankle-boot",
        "source_base": None,
        "bg_color": (240, 235, 225),
        "fg_color": (140, 90, 50),
    },
    {
        "filename": "footwear_03_black_oxford_dress_shoes.jpg",
        "category": "footwear",
        "name": "Black Full-Grain Leather Oxfords",
        "color": "black",
        "pattern": "solid",
        "style": "formal",
        "season": "all-season",
        "material": "leather",
        "price": 130.0,
        "fit_tightness": "regular",
        "silhouette": "dress",
        "source_base": None,
        "bg_color": (230, 230, 230),
        "fg_color": (20, 20, 20),
    },
    {
        "filename": "footwear_04_olive_trail_running_shoes.jpg",
        "category": "footwear",
        "name": "Olive Trail Performance Running Shoes",
        "color": "olive",
        "pattern": "colorblock",
        "style": "athletic",
        "season": "all-season",
        "material": "synthetic",
        "price": 110.0,
        "fit_tightness": "regular",
        "silhouette": "sneaker",
        "source_base": None,
        "bg_color": (235, 240, 235),
        "fg_color": (80, 100, 75),
    },

    # --- ACCESSORIES (2 items) ---
    {
        "filename": "accessory_01_burgundy_wool_scarf.jpg",
        "category": "accessory",
        "name": "Burgundy Ribbed Merino Wool Scarf",
        "color": "burgundy",
        "pattern": "ribbed",
        "style": "casual",
        "season": "winter",
        "material": "wool",
        "price": 35.0,
        "fit_tightness": "regular",
        "silhouette": "wrap",
        "source_base": None,
        "bg_color": (240, 230, 235),
        "fg_color": (120, 30, 50),
    },
    {
        "filename": "accessory_02_brown_leather_belt.jpg",
        "category": "accessory",
        "name": "Antique Brown Full-Grain Leather Belt",
        "color": "brown",
        "pattern": "solid",
        "style": "smart-casual",
        "season": "all-season",
        "material": "leather",
        "price": 45.0,
        "fit_tightness": "regular",
        "silhouette": "standard",
        "source_base": None,
        "bg_color": (240, 235, 230),
        "fg_color": (115, 75, 45),
    },
]

def generate_garment_photo(spec: dict, target_path: Path):
    """Generate or adapt a high-resolution garment photo with realistic palette & textures."""
    source_base = spec.get("source_base")
    cand_dir = BACKEND_DIR / "data" / "test_candidates"

    if source_base and (cand_dir / source_base).exists():
        # Enhance existing real candidate image
        img = Image.open(cand_dir / source_base).convert("RGB")
        img = img.resize((600, 600), Image.Resampling.LANCZOS)
    else:
        # Create a clean, elegant studio garment card
        w, h = 600, 600
        bg_col = spec.get("bg_color", (240, 240, 240))
        fg_col = spec.get("fg_color", (70, 70, 70))
        
        img = Image.new("RGB", (w, h), color=bg_col)
        draw = ImageDraw.Draw(img)

        # Draw soft ambient shadow
        shadow_box = [110, 110, 490, 490]
        draw.rounded_rectangle(shadow_box, radius=32, fill=(215, 215, 220))
        img = img.filter(ImageFilter.GaussianBlur(radius=8))
        draw = ImageDraw.Draw(img)

        # Draw main garment silhouette card
        card_box = [100, 100, 500, 500]
        draw.rounded_rectangle(card_box, radius=28, fill=fg_col)

        # Draw subtle inner contour / pattern
        pattern = spec.get("pattern")
        if pattern == "striped":
            for y in range(140, 460, 24):
                draw.line([(120, y), (480, y)], fill=(255, 255, 255), width=6)
        elif pattern == "quilted":
            for x in range(120, 480, 40):
                draw.line([(x, 120), (x + 80, 480)], fill=(bg_col[0] - 20, bg_col[1] - 20, bg_col[2] - 20), width=2)
                draw.line([(x + 80, 120), (x, 480)], fill=(bg_col[0] - 20, bg_col[1] - 20, bg_col[2] - 20), width=2)
        elif pattern == "floral":
            for ox, oy in [(200, 200), (350, 250), (250, 380), (400, 400), (180, 320)]:
                draw.ellipse([ox - 15, oy - 15, ox + 15, oy + 15], fill=(255, 210, 180))

        # Add category & material tag label inside photo
        draw.rounded_rectangle([130, 430, 470, 475], radius=12, fill=(0, 0, 0, 160))
        draw.text((150, 442), f"{spec['category'].upper()} • {spec['material'].capitalize()}", fill=(255, 255, 255))

    img.save(target_path, format="JPEG", quality=92)


def batch_ingest_demo_wardrobe():
    print("=================================================================")
    print("MILESTONE 39: CURATED DEMO WARDROBE BATCH INGESTION")
    print("=================================================================")
    
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 1. Initialize or reset demo user
    demo_user = db.query(User).filter(User.firebase_uid == "demo_user_wardrobe").first()
    if not demo_user:
        demo_user = User(
            firebase_uid="demo_user_wardrobe",
            email="demo@verdict.engine",
            display_name="Verdict Demo Presenter",
            created_at=datetime.now(timezone.utc),
        )
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)
        print(f"Created dedicated Demo User: ID {demo_user.id} ({demo_user.email})")
    else:
        print(f"Found existing Demo User: ID {demo_user.id} ({demo_user.email})")

    # Clean existing items for demo user to ensure clean, exact 24-item set
    existing_items = db.query(WardrobeItem).filter(WardrobeItem.user_id == demo_user.id).all()
    if existing_items:
        print(f"Purging {len(existing_items)} existing items from demo account for clean rebuild...")
        coll = get_wardrobe_collection()
        for itm in existing_items:
            try:
                coll.delete(ids=[str(itm.id)])
            except Exception:
                pass
            db.delete(itm)
        db.commit()

    print(f"\nIngesting {len(DEMO_WARDROBE_SPECS)} curated wardrobe items...")
    coll = get_wardrobe_collection()
    ingested = []

    for idx, spec in enumerate(DEMO_WARDROBE_SPECS, 1):
        photo_path = PHOTOS_DIR / spec["filename"]
        generate_garment_photo(spec, photo_path)

        # Upload destination (local served uploads)
        upload_dest = UPLOADS_DIR / spec["filename"]
        if photo_path != upload_dest:
            with open(photo_path, "rb") as src, open(upload_dest, "wb") as dst:
                dst.write(src.read())

        photo_url = f"http://localhost:8000/api/uploads/{spec['filename']}"
        now = datetime.now(timezone.utc)

        # Create WardrobeItem
        item = WardrobeItem(
            user_id=demo_user.id,
            cloudinary_url=photo_url,
            cloudinary_public_id=f"demo_wardrobe/{spec['filename']}",
            is_candidate=False,
            price=spec["price"],
            fit_tightness=spec["fit_tightness"],
            silhouette=spec["silhouette"],
            tryon_render_url=photo_url,
            tryon_degraded=False,
            uploaded_at=now,
        )
        db.add(item)
        db.flush()

        # Create 100% complete GarmentAttributes (no nulls!)
        attrs = GarmentAttributes(
            wardrobe_item_id=item.id,
            category=spec["category"],
            color=spec["color"],
            pattern=spec["pattern"],
            style=spec["style"],
            season=spec["season"],
            material=spec["material"],
            extraction_source=ExtractionSource.AI,
            updated_at=now,
        )
        db.add(attrs)
        db.commit()
        db.refresh(item)

        # Generate real 512-dim CLIP embedding
        embedding = generate_embedding(str(photo_path))
        upsert_wardrobe_embedding(
            item_id=item.id,
            user_id=demo_user.id,
            category=spec["category"],
            embedding=embedding,
        )

        ingested.append({
            "id": item.id,
            "category": spec["category"],
            "name": spec["name"],
            "color": spec["color"],
            "season": spec["season"],
            "style": spec["style"],
            "price": spec["price"],
        })
        print(f"  [{idx:02d}/24] Ingested #{item.id}: {spec['name']} (${spec['price']:.2f}) -> {spec['category']} | {spec['season']} | {spec['style']}")

    db.close()
    print(f"\nSuccessfully ingested and indexed all {len(ingested)} items into ChromaDB and DB.")
    print("=================================================================\n")

if __name__ == "__main__":
    batch_ingest_demo_wardrobe()
