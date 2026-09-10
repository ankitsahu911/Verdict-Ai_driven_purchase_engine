import sys
from pathlib import Path
from collections import Counter

# Ensure backend directory is in python path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.db import SessionLocal
from app.models import User, WardrobeItem
from app.services.chroma_service import get_wardrobe_collection, has_wardrobe_embedding

REQUIRED_ATTRS = ["category", "color", "pattern", "style", "season", "material"]

def verify_demo_wardrobe() -> bool:
    print("=================================================================")
    print("MILESTONE 39: CURATED DEMO WARDROBE STRICT VERIFICATION AUDIT")
    print("=================================================================")
    
    db = SessionLocal()
    demo_user = db.query(User).filter(User.firebase_uid == "demo_user_wardrobe").first()
    
    if not demo_user:
        print("[FAIL] Demo user 'demo_user_wardrobe' (demo@verdict.engine) not found in database!")
        db.close()
        return False

    items = (
        db.query(WardrobeItem)
        .filter(WardrobeItem.user_id == demo_user.id, WardrobeItem.is_candidate == False)
        .order_by(WardrobeItem.id.asc())
        .all()
    )
    total_count = len(items)
    print(f"Demo User ID: {demo_user.id} ({demo_user.email})")
    print(f"Total Wardrobe Items Found: {total_count}")

    if total_count < 20 or total_count > 30:
        print(f"[FAIL] Expected 20-30 demo items, but found {total_count}!")
        db.close()
        return False
    else:
        print(f"[PASS] Wardrobe size is within required range (20–30 items).")

    collection = get_wardrobe_collection()
    flagged_items = []
    
    categories = Counter()
    seasons = Counter()
    styles = Counter()
    total_value = 0.0

    print("\nAuditing individual item integrity:")
    print("-----------------------------------------------------------------")
    print(f"{'ID':<6} {'Category':<12} {'Color':<14} {'Season':<12} {'Style':<14} {'ChromaDB':<10} {'Status'}")
    print("-----------------------------------------------------------------")

    for itm in items:
        issues = []
        attrs = itm.attributes

        # 1. Attribute completeness check
        if attrs is None:
            issues.append("Missing GarmentAttributes record")
        else:
            for attr_name in REQUIRED_ATTRS:
                val = getattr(attrs, attr_name, None)
                if val is None or str(val).strip() == "" or str(val).lower() == "null":
                    issues.append(f"Null/empty field: '{attr_name}'")

        # 2. ChromaDB embedding check
        has_emb = False
        try:
            res = collection.get(ids=[str(itm.id)], include=["embeddings"])
            if res and res.get("ids") and len(res["ids"]) > 0:
                has_emb = True
                emb = res.get("embeddings")
                if emb is None or len(emb) == 0 or len(emb[0]) != 512:
                    issues.append(f"Invalid embedding dimension in ChromaDB: {len(emb[0]) if emb else 0}")
            else:
                issues.append("ChromaDB embedding not found")
        except Exception as e:
            issues.append(f"ChromaDB lookup error: {e}")

        # 3. Photo check
        if not itm.cloudinary_url:
            issues.append("Missing cloudinary_url")

        # Summary for table
        cat_disp = attrs.category if attrs and attrs.category else "UNKNOWN"
        col_disp = attrs.color if attrs and attrs.color else "UNKNOWN"
        sea_disp = attrs.season if attrs and attrs.season else "UNKNOWN"
        sty_disp = attrs.style if attrs and attrs.style else "UNKNOWN"
        chroma_disp = "512-dim" if has_emb else "MISSING"

        if issues:
            flagged_items.append((itm.id, issues))
            status_disp = f"FLAGGED ({len(issues)} issues)"
        else:
            status_disp = "VERIFIED"
            if attrs:
                categories[attrs.category] += 1
                seasons[attrs.season] += 1
                styles[attrs.style] += 1
            if itm.price:
                total_value += itm.price

        print(f"#{itm.id:<5} {cat_disp:<12} {col_disp:<14} {sea_disp:<12} {sty_disp:<14} {chroma_disp:<10} {status_disp}")

    print("-----------------------------------------------------------------")

    # Taxonomic Balance Reporting
    print("\nTAXONOMIC BALANCE REPORT:")
    print("  Category Distribution:")
    for cat, count in sorted(categories.items()):
        print(f"    - {cat.capitalize():<12}: {count} items")
    print("  Seasonal Coverage:")
    for sea, count in sorted(seasons.items()):
        print(f"    - {sea.capitalize():<12}: {count} items")
    print("  Style Coverage:")
    for sty, count in sorted(styles.items()):
        print(f"    - {sty.capitalize():<12}: {count} items")
    print(f"  Total Wardrobe Value: ${total_value:.2f} (Avg ${total_value/total_count:.2f} per item)")

    # Category coverage check: Must span tops, bottoms, outerwear, dresses, footwear, accessories
    expected_categories = {"top", "bottom", "outerwear", "dress", "footwear", "accessory"}
    missing_cats = expected_categories - set(categories.keys())
    if missing_cats:
        print(f"\n[WARNING] Wardrobe missing coverage in categories: {missing_cats}")
    else:
        print(f"\n[PASS] Multi-category coverage verified across all 6 core apparel types.")

    db.close()

    if flagged_items:
        print(f"\n[FAIL] {len(flagged_items)} item(s) flagged with integrity errors:")
        for itm_id, issues in flagged_items:
            print(f"  Item #{itm_id}: {', '.join(issues)}")
        return False
    else:
        print(f"\n[SUCCESS] 100% of {total_count} demo wardrobe items verified correct!")
        print("Zero null fields, 100% ChromaDB embeddings present, zero live AI extraction needed on stage.")
        print("=================================================================\n")
        return True

if __name__ == "__main__":
    success = verify_demo_wardrobe()
    sys.exit(0 if success else 1)
