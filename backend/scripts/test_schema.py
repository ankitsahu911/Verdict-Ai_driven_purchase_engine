"""
Verify the v1 database schema exists and works (MILESTONE 5).

Checks:
  1. Connect to Postgres (DATABASE_URL from .env)
  2. All 4 business tables exist (users, wardrobe_items, garment_attributes,
     decision_logs) — alembic_version is expected too
  3. Each table has the expected columns and key constraints
  4. A round-trip insert + relationship walk works, then cleans up after itself

Usage:
  python scripts/test_schema.py
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect

from app.db import SessionLocal, engine
from app.models import (
    Decision,
    DecisionLog,
    ExtractionSource,
    GarmentAttributes,
    User,
    WardrobeItem,
)

EXPECTED_TABLES = {
    "users",
    "wardrobe_items",
    "garment_attributes",
    "decision_logs",
}

EXPECTED_COLUMNS = {
    "users": {"id", "firebase_uid", "email", "display_name", "created_at"},
    "wardrobe_items": {
        "id",
        "user_id",
        "cloudinary_url",
        "cloudinary_public_id",
        "is_candidate",
        "uploaded_at",
    },
    "garment_attributes": {
        "id",
        "wardrobe_item_id",
        "category",
        "color",
        "pattern",
        "style",
        "season",
        "material",
        "extraction_source",
        "updated_at",
    },
    "decision_logs": {
        "id",
        "user_id",
        "wardrobe_item_id",
        "decision",
        "buy_score",
        "raw_payload",
        "created_at",
    },
}

EXPECTED_FKS = {
    "wardrobe_items": {("user_id", "users", "id")},
    "garment_attributes": {("wardrobe_item_id", "wardrobe_items", "id")},
    "decision_logs": {
        ("user_id", "users", "id"),
        ("wardrobe_item_id", "wardrobe_items", "id"),
    },
}

# ---------------------------------------------------------------------------
#  Step 1 – Tables exist
# ---------------------------------------------------------------------------
print("=== Step 1: Connect and list tables ===")
insp = inspect(engine)
tables = set(insp.get_table_names())
print(f"  Tables in DB: {sorted(tables)}")

missing = EXPECTED_TABLES - tables
if missing:
    print(f"  FAILED — missing tables: {sorted(missing)}")
    sys.exit(1)
print(f"  All {len(EXPECTED_TABLES)} expected tables present")

# ---------------------------------------------------------------------------
#  Step 2 – Columns and constraints
# ---------------------------------------------------------------------------
print("\n=== Step 2: Columns + constraints ===")
for table in sorted(EXPECTED_TABLES):
    cols = {c["name"] for c in insp.get_columns(table)}
    missing_cols = EXPECTED_COLUMNS[table] - cols
    if missing_cols:
        print(f"  FAILED — {table} missing columns: {sorted(missing_cols)}")
        sys.exit(1)

    fk_set = {
        (c, fk["referred_table"], fk["referred_columns"][0])
        for fk in insp.get_foreign_keys(table)
        for c in fk["constrained_columns"]
    }
    expected_fks = EXPECTED_FKS.get(table, set())
    if fk_set != expected_fks:
        got = sorted(fk_set)
        want = sorted(expected_fks)
        print(f"  FAILED — {table} FKs: got {got}, want {want}")
        sys.exit(1)

    unique_ids = [
        u["column_names"]
        for u in insp.get_unique_constraints(table)
        if "id" not in u["column_names"] or u["name"] == "uq_garment_attributes_item"
    ]
    print(f"  OK — {table}: columns={sorted(cols)}")
    print(f"      FKs={sorted(fk_set)} uniques={unique_ids}")

# garment_attributes must enforce one-to-one via unique constraint
ga_uniques = {
    tuple(sorted(u["column_names"]))
    for u in insp.get_unique_constraints("garment_attributes")
}
if ("wardrobe_item_id",) not in ga_uniques:
    print("  FAILED — garment_attributes missing unique constraint on wardrobe_item_id")
    sys.exit(1)
print("  OK — garment_attributes unique on wardrobe_item_id (one-to-one enforced)")

# ---------------------------------------------------------------------------
#  Step 3 – Round-trip insert + relationship walk
# ---------------------------------------------------------------------------
print("\n=== Step 3: Round-trip insert ===")
db = SessionLocal()
now = datetime.now(timezone.utc)
test_uid = f"schema-test-{uuid.uuid4()}"
user = None
try:
    user = User(firebase_uid=test_uid, email="schema-test@example.com", created_at=now)
    db.add(user)
    db.flush()

    item = WardrobeItem(
        user_id=user.id,
        cloudinary_url="https://res.cloudinary.com/x/image/upload/v1/t.jpg",
        cloudinary_public_id="x/t",
        is_candidate=False,
        uploaded_at=now,
    )
    db.add(item)
    db.flush()

    attrs = GarmentAttributes(
        wardrobe_item_id=item.id,
        category="upper_body",
        color="navy",
        extraction_source=ExtractionSource.AI,
        updated_at=now,
    )
    db.add(attrs)

    log = DecisionLog(
        user_id=user.id,
        wardrobe_item_id=item.id,
        decision=Decision.BUY,
        buy_score=0.87,
        raw_payload={"axes": {"fit": 0.9}},
        created_at=now,
    )
    db.add(log)
    db.commit()

    db.refresh(user)
    db.refresh(item)

    assert [i.id for i in user.wardrobe_items] == [item.id]
    assert user.decision_logs[0].decision == Decision.BUY
    assert item.attributes.color == "navy"
    assert item.attributes.extraction_source == ExtractionSource.AI
    assert log.raw_payload["axes"]["fit"] == 0.9
    print("  Relationships OK (user->items, user->logs, item->attributes, log FK)")
    print("  Round-trip PASSED")
finally:
    if user and user.id:
        db.query(DecisionLog).filter(DecisionLog.user_id == user.id).delete()
        db.query(GarmentAttributes).filter(
            GarmentAttributes.wardrobe_item.has(user_id=user.id)
        ).delete(synchronize_session=False)
        db.query(WardrobeItem).filter(WardrobeItem.user_id == user.id).delete()
        db.query(User).filter(User.id == user.id).delete()
        db.commit()
    db.close()

print("\nSchema verification PASSED")
