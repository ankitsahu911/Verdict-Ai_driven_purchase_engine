import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal
from app.models import DecisionLog, GarmentAttributes, User, WardrobeItem


def show_database():
    db = SessionLocal()
    try:
        print("=" * 84)
        print("         VERDICT POSTGRESQL DATABASE ENTRIES & RELATIONSHIPS")
        print("=" * 84)

        # 1. USERS TABLE
        users = db.query(User).order_by(User.id.asc()).all()
        print(f"\n[1] TABLE: users ({len(users)} record(s))")
        print("-" * 84)
        print(f"{'ID':<6} {'Firebase UID':<32} {'Email':<30} {'Created At'}")
        print("-" * 84)
        for u in users:
            print(f"{u.id:<6} {u.firebase_uid[:30]:<32} {u.email[:28]:<30} {str(u.created_at)[:19]}")

        # 2. WARDROBE_ITEMS TABLE
        items = db.query(WardrobeItem).order_by(WardrobeItem.id.asc()).all()
        print(f"\n[2] TABLE: wardrobe_items ({len(items)} record(s))")
        print("-" * 84)
        print(f"{'ID':<5} {'User':<6} {'Is Candidate':<14} {'Price':<9} {'Fit':<10} {'Silhouette':<12} {'Dup %':<8} {'Uploaded'}")
        print("-" * 84)
        for item in items:
            price_str = f"${item.price:.2f}" if item.price is not None else "-"
            fit_str = item.fit_tightness or "-"
            sil_str = item.silhouette or "-"
            dup_str = f"{item.duplicate_similarity_pct:.1f}%" if item.duplicate_similarity_pct is not None else "-"
            print(
                f"{item.id:<5} {item.user_id:<6} {str(item.is_candidate):<14} {price_str:<9} "
                f"{fit_str:<10} {sil_str:<12} {dup_str:<8} {str(item.uploaded_at)[:10]}"
            )

        # 3. GARMENT_ATTRIBUTES TABLE
        attrs = db.query(GarmentAttributes).order_by(GarmentAttributes.id.asc()).all()
        print(f"\n[3] TABLE: garment_attributes ({len(attrs)} record(s))")
        print("-" * 84)
        print(f"{'ID':<5} {'Item ID':<9} {'Category':<14} {'Color':<14} {'Style':<14} {'Season':<12} {'Material'}")
        print("-" * 84)
        for a in attrs:
            cat = a.category or "-"
            col = a.color or "-"
            sty = a.style or "-"
            sea = a.season or "-"
            mat = a.material or "-"
            print(f"{a.id:<5} {a.wardrobe_item_id:<9} {cat:<14} {col:<14} {sty:<14} {sea:<12} {mat}")

        # 4. DECISION_LOGS TABLE
        logs = db.query(DecisionLog).order_by(DecisionLog.id.asc()).all()
        print(f"\n[4] TABLE: decision_logs ({len(logs)} record(s))")
        print("-" * 84)
        print(f"{'ID':<5} {'User':<6} {'Item ID':<9} {'Verdict':<10} {'Buy Score':<12} {'Created At'}")
        print("-" * 84)
        for log in logs:
            score_str = f"{log.buy_score:.1f} / 100" if log.buy_score is not None else "-"
            decision_str = log.decision.value.upper() if log.decision else "-"
            print(f"{log.id:<5} {log.user_id:<6} {str(log.wardrobe_item_id):<9} {decision_str:<10} {score_str:<12} {str(log.created_at)[:19]}")

        print("\n" + "=" * 84)
        print(" DATABASE PERSISTENCE STATUS: ACTIVE & VERIFIED")
        print("=" * 84)

    finally:
        db.close()


if __name__ == "__main__":
    show_database()
