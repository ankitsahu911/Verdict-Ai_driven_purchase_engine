import io
import os
import sys
import time
import urllib.request
from pathlib import Path
from PIL import Image, ImageOps

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.db import SessionLocal
from app.models import WardrobeItem, User
from app.services.chroma_service import upsert_wardrobe_embedding
from app.services.embedding_service import generate_embedding

UPLOADS_DIR = BACKEND_DIR / "data" / "uploads"
DEMO_DIR = BACKEND_DIR / "data" / "demo_wardrobe_photos"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
DEMO_DIR.mkdir(parents=True, exist_ok=True)

PHOTO_MAP = {
    # Tops (5)
    "top_01_white_crewneck_tee.jpg": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=800&auto=format&fit=crop&q=85",
    "top_02_blue_oxford_shirt.jpg": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=800&auto=format&fit=crop&q=85",
    "top_03_grey_cashmere_sweater.jpg": "https://images.unsplash.com/photo-1620799140408-edc6dcb6d633?w=800&auto=format&fit=crop&q=85",
    "top_04_striped_breton_tee.jpg": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=800&auto=format&fit=crop&q=85",
    "top_05_black_silk_blouse.jpg": "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?w=800&auto=format&fit=crop&q=85",
    
    # Bottoms (5)
    "bottom_01_dark_indigo_jeans.jpg": "https://images.unsplash.com/photo-1542272604-787c3835535d?w=800&auto=format&fit=crop&q=85",
    "bottom_02_beige_tailored_chinos.jpg": "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=800&auto=format&fit=crop&q=85",
    "bottom_03_charcoal_dress_trousers.jpg": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=800&auto=format&fit=crop&q=85",
    "bottom_04_olive_cargo_pants.jpg": "https://images.unsplash.com/photo-1517445312882-bc9910d016b7?w=800&auto=format&fit=crop&q=85",
    "bottom_05_black_running_shorts.jpg": "https://images.unsplash.com/photo-1591195853828-11db59a44f6b?w=800&auto=format&fit=crop&q=85",
    
    # Outerwear (5)
    "outerwear_01_camel_wool_overcoat.jpg": "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=800&auto=format&fit=crop&q=85",
    "outerwear_02_navy_tailored_blazer.jpg": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=800&auto=format&fit=crop&q=85",
    "outerwear_03_black_leather_jacket.jpg": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=800&auto=format&fit=crop&q=85",
    "outerwear_04_olive_quilted_vest.jpg": "https://images.unsplash.com/photo-1544441893-675973e31985?w=800&auto=format&fit=crop&q=85",
    "outerwear_05_heather_grey_hoodie.jpg": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=800&auto=format&fit=crop&q=85",
    
    # Dresses (3)
    "dress_01_navy_midi_shirt_dress.jpg": "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=800&auto=format&fit=crop&q=85",
    "dress_02_little_black_dress.jpg": "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?w=800&auto=format&fit=crop&q=85",
    "dress_03_floral_summer_maxi_dress.jpg": "https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?w=800&auto=format&fit=crop&q=85",
    
    # Footwear (4)
    "footwear_01_white_minimalist_sneakers.jpg": "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=800&auto=format&fit=crop&q=85",
    "footwear_02_brown_suede_chelsea_boots.jpg": "https://images.unsplash.com/photo-1608256246200-53e635b5b65f?w=800&auto=format&fit=crop&q=85",
    "footwear_03_black_oxford_dress_shoes.jpg": "https://images.unsplash.com/photo-1614252235316-8c857d38b5f4?w=800&auto=format&fit=crop&q=85",
    "footwear_04_olive_trail_running_shoes.jpg": "https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=800&auto=format&fit=crop&q=85",
    
    # Accessories (2)
    "accessory_01_burgundy_wool_scarf.jpg": "https://images.unsplash.com/photo-1520903920243-00d872a2d1c9?w=800&auto=format&fit=crop&q=85",
    "accessory_02_brown_leather_belt.jpg": "https://images.unsplash.com/photo-1624222247344-550fb60583dc?w=800&auto=format&fit=crop&q=85",
}


def download_and_crop(url: str, target_size: int = 600) -> Image.Image:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, timeout=12) as resp:
        data = resp.read()
    im = Image.open(io.BytesIO(data)).convert("RGB")
    # Center crop to square
    w, h = im.size
    min_dim = min(w, h)
    left = (w - min_dim) // 2
    top = (h - min_dim) // 2
    cropped = im.crop((left, top, left + min_dim, top + min_dim))
    return cropped.resize((target_size, target_size), Image.Resampling.LANCZOS)


def main():
    print("=" * 60)
    print("UPGRADING WARDROBE PHOTOS WITH REAL FASHION IMAGERY")
    print("=" * 60)

    db = SessionLocal()
    demo_user = db.query(User).filter(User.firebase_uid == "demo_user_wardrobe").first()
    if not demo_user:
        print("Demo user not found!")
        return

    items = db.query(WardrobeItem).filter(
        WardrobeItem.user_id == demo_user.id,
        WardrobeItem.is_candidate == False
    ).all()
    print(f"Found {len(items)} wardrobe items for user {demo_user.id}")

    success_count = 0
    for filename, url in PHOTO_MAP.items():
        upload_path = UPLOADS_DIR / filename
        demo_path = DEMO_DIR / filename
        print(f"Fetching photo for {filename}...")
        try:
            img = download_and_crop(url)
            img.save(upload_path, "JPEG", quality=90)
            img.save(demo_path, "JPEG", quality=90)
            print(f"  [OK] Saved {filename} ({img.size})")
            success_count += 1
        except Exception as e:
            print(f"  [FAIL] Failed {filename}: {e}")
        time.sleep(0.2)

    print(f"\nSuccessfully downloaded and saved {success_count} / {len(PHOTO_MAP)} real photos.")

    # Now update items in database & backfill embeddings
    print("\nUpdating database URLs and re-generating embeddings...")
    for item in items:
        # Match item to filename by category/spec
        item_filename = None
        for fn in PHOTO_MAP.keys():
            if fn in (item.cloudinary_url or ""):
                item_filename = fn
                break
        
        if not item_filename:
            # Fallback by attributes
            cat = item.attributes.category if item.attributes else "unknown"
            col = item.attributes.color if item.attributes else "unknown"
            for fn in PHOTO_MAP.keys():
                if cat in fn and col.split()[0] in fn:
                    item_filename = fn
                    break

        if item_filename:
            new_url = f"http://localhost:8000/api/uploads/{item_filename}"
            item.cloudinary_url = new_url
            item.cloudinary_public_id = f"local/wardrobe/{item_filename}"
            
            # Generate new CLIP embedding for the photo
            local_file_path = UPLOADS_DIR / item_filename
            if local_file_path.exists():
                try:
                    emb = generate_embedding(str(local_file_path))
                    upsert_wardrobe_embedding(
                        item_id=item.id,
                        user_id=demo_user.id,
                        category=item.attributes.category if item.attributes else "unknown",
                        embedding=emb,
                    )
                except Exception as emb_err:
                    print(f"  Warning: Embedding update failed for item {item.id}: {emb_err}")

    db.commit()
    db.close()
    print("\n[OK] Database and vector embeddings successfully updated with real photography!")


if __name__ == "__main__":
    main()
