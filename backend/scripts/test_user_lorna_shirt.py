import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal
from app.models import WardrobeItem, GarmentAttributes, User, ExtractionSource
from app.services.vision_service import analyze_image
from app.services.embedding_service import generate_embedding
from app.services.chroma_service import find_near_duplicate, query_similar_items
from app.services.outfit_service import find_compatible_items
from app.decision_engine.orchestrator import synthesize_buy_score

img_path = str(Path(__file__).resolve().parent.parent / "data" / "test_candidates" / "lorna_shore_tee.png")
print("Evaluating User Image:", img_path)

db = SessionLocal()
owner = db.query(User).filter(User.id == 16).first()

# 1. Vision Analysis
print("\n--- 1. VISION AI (GEMINI) ATTRIBUTE EXTRACTION ---")
vision_res = analyze_image(img_path)
print("Extracted Attributes:", vision_res)

# 2. Embedding Generation
print("\n--- 2. CLIP 512-DIM VECTOR EMBEDDING ---")
emb = generate_embedding(img_path)
print(f"Generated 512-dim embedding. Sample: {emb[:5]}")

# 3. ChromaDB Duplicate & Similarity Search
print("\n--- 3. CHROMADB VECTOR CLOSET MATCHING ---")
similar = query_similar_items(query_embedding=emb, top_k=3, user_id=16)
for s in similar:
    print(f"- Item ID: {s.get('item_id')}, Cosine Distance: {s.get('distance'):.4f}, Similarity: {(1.0 - (s.get('distance') or 0.0))*100:.1f}%")

dup = find_near_duplicate(query_embedding=emb, user_id=16)
print("\nDuplicate Check Result:")
print("Is Duplicate?:", dup.get("is_duplicate"))
print("Similarity Pct:", dup.get("similarity_pct"))

# 4. Insert Candidate Item into DB for Scoring
cand = WardrobeItem(
    user_id=16,
    cloudinary_url="/uploads/lorna_shore_tee.png",
    is_candidate=True,
    price=35.0,
    duplicate_similarity_pct=dup.get("similarity_pct", 38.8),
    duplicate_match_item_id=dup.get("match_item_id"),
    uploaded_at=datetime.now(timezone.utc),
)
db.add(cand)
db.commit()
db.refresh(cand)

cand_attrs = GarmentAttributes(
    wardrobe_item_id=cand.id,
    category=vision_res.get("category", "top"),
    color=vision_res.get("color", "dark grey"),
    pattern=vision_res.get("pattern", "graphic"),
    style=vision_res.get("style", "streetwear"),
    season=vision_res.get("season", "all-season"),
    material=vision_res.get("material", "cotton"),
    extraction_source=ExtractionSource.AI,
    updated_at=datetime.now(timezone.utc),
)
db.add(cand_attrs)
db.commit()

# 5. Compatible Wardrobe Pieces
wardrobe_items = db.query(WardrobeItem).filter(WardrobeItem.user_id == 16, WardrobeItem.is_candidate == False).all()
compat = find_compatible_items({"category": cand_attrs.category, "color": cand_attrs.color}, wardrobe_items)
print(f"\n--- 4. COMPATIBLE OUTFIT MATCHES ({len(compat)} found) ---")
for c in compat[:6]:
    w_item = db.query(WardrobeItem).filter(WardrobeItem.id == c["wardrobe_item_id"]).first()
    reasons = c.get("compatibility_reasons", [])
    print(f"- Matches {w_item.attributes.category.upper()} (ID {w_item.id}): {w_item.attributes.color} {w_item.attributes.style} ({', '.join(reasons)})")

# 6. Full 6-Axis Decision Synthesis
print("\n--- 5. FULL 6-AXIS DECISION SYNTHESIS ---")
verdict_res = synthesize_buy_score(candidate_item_id=cand.id, db=db, persist=False)
print(f"Overall Buy Score: {verdict_res.overall_score} / 100")
print(f"Verdict: {verdict_res.verdict.upper()}")
print(f"Headline: {verdict_res.headline_reason}")
print("\nAxis Scores:")
for a in verdict_res.axes:
    print(f"  • {a.axis.value.capitalize():<20}: {a.score:>5.1f} / 100  -->  {a.reason}")
