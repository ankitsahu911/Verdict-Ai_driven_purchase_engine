#!/usr/bin/env python3
"""
Verification Script for Milestone 41: Hardening 5 Edge Cases in Verdict.

Tests each of the 5 edge cases directly and prints human-readable verification results:
1. Empty wardrobe (brand-new user, zero items uploaded)
2. Malformed photo upload (corrupted bytes)
3. YouCam timeout (graceful degradation)
4. Cart with > 5 items (exponential combinatorial space guard)
5. Cart with exactly 1 item (redirects to single-item Buy Score)
"""

import io
import os
import sys
from unittest.mock import MagicMock, patch
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.auth import get_current_user
from app.db import get_db
from app.models import GarmentAttributes, User, WardrobeItem
from app.decision_engine.scorers.versatility import score_versatility
from app.services.chroma_service import query_similar_items, find_near_duplicate
from app.services.vision_service import analyze_image, VisionServiceError
from app.services.tryon_service import TryOnTimeoutError, build_tryon_fallback
from verdict_backend.main import app

DIVIDER = "=" * 80


def run_verification():
    print(DIVIDER)
    print(" VERDICT MILESTONE 41: SYSTEMATIC EDGE CASE HARDENING VERIFICATION")
    print(DIVIDER)

    client = TestClient(app)
    mock_user = {
        "uid": "demo_edge_user",
        "email": "demo_edge@verdict.style",
        "name": "Demo Edge User",
    }
    mock_db = MagicMock()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db

    passed = 0
    total = 5

    # -------------------------------------------------------------------------
    # 1. Empty Wardrobe
    # -------------------------------------------------------------------------
    print("\n[Case 1/5] Testing Empty Wardrobe (0 items uploaded)...")
    owner = MagicMock(id=99, firebase_uid="demo_edge_user")
    cand = WardrobeItem(id=1, user_id=99, is_candidate=True, cloudinary_url="https://res.cloudinary.com/cand.jpg")
    cand.attributes = GarmentAttributes(category="top", color="black", pattern="solid")

    def mock_query(model):
        q = MagicMock()
        if model == WardrobeItem:
            q.filter.return_value.first.return_value = cand
            q.filter.return_value.all.return_value = []
        elif model == GarmentAttributes:
            q.filter.return_value.first.return_value = cand.attributes
        return q

    mock_db.query.side_effect = mock_query

    with patch("app.routers.candidates.get_or_create_user", return_value=owner):
        res_matches = client.get("/api/candidates/1/outfit-matches")
        res_combos = client.get("/api/candidates/1/outfit-combinations")

    mock_coll = MagicMock()
    mock_coll.count.return_value = 0
    with patch("app.services.chroma_service.get_wardrobe_collection", return_value=mock_coll):
        chroma_res = query_similar_items([0.1] * 512, user_id=99)

    score_res = score_versatility(1, mock_db)

    print(f"  • Outfit matches response: status={res_matches.status_code}, matches={res_matches.json()['total_matches']}")
    print(f"    Message: \"{res_matches.json()['message']}\"")
    print(f"  • Outfit combos response:  status={res_combos.status_code}, combos={res_combos.json()['total_combinations_found']}")
    print(f"    Message: \"{res_combos.json()['message']}\"")
    print(f"  • ChromaDB empty vectors:  count={len(chroma_res)} (handled gracefully without query error)")
    print(f"  • Versatility axis score:  {score_res.score} / 100.0 (clean zero, no div-by-zero)")
    print(f"    Reason: \"{score_res.reason}\"")

    if (
        res_matches.status_code == 200
        and res_combos.status_code == 200
        and "no compatible items found yet" in res_matches.json()["message"]
        and chroma_res == []
        and score_res.score == 0.0
    ):
        print("  --> PASS: Empty wardrobe handled gracefully across all subsystems.")
        passed += 1
    else:
        print("  --> FAIL: Unexpected behavior in empty wardrobe handling.")

    # -------------------------------------------------------------------------
    # 2. Malformed Photo Upload
    # -------------------------------------------------------------------------
    print("\n[Case 2/5] Testing Malformed Photo Upload (corrupted bytes)...")
    corrupt_payload = b"RIFF\x00\x00\x00\x00CORRUPT_NOT_AN_IMAGE_DATA_BYTES"
    with patch("app.routers.candidates.get_or_create_user", return_value=owner):
        res_cand = client.post(
            "/api/candidates",
            files={"file": ("corrupted_item.jpg", corrupt_payload, "image/jpeg")},
        )
        res_wardrobe = client.post(
            "/api/wardrobe/upload",
            files=[("files", ("bad_photo.png", corrupt_payload, "image/png"))],
        )

    print(f"  • Candidate intake: status={res_cand.status_code}")
    print(f"    Detail: \"{res_cand.json().get('detail')}\"")
    print(f"  • Wardrobe bulk upload: status={res_wardrobe.status_code}, failed_count={res_wardrobe.json().get('failed_count')}")
    print(f"    Error: \"{res_wardrobe.json().get('failed', [{}])[0].get('error')}\"")

    if (
        res_cand.status_code == 400
        and "couldn't read this image" in res_cand.json().get("detail", "").lower()
        and res_wardrobe.status_code == 200
        and "couldn't read this image" in res_wardrobe.json()["failed"][0]["error"].lower()
    ):
        print("  --> PASS: Corrupted image rejected cleanly with human-readable error.")
        passed += 1
    else:
        print("  --> FAIL: Malformed photo handling did not produce expected error messages.")

    # -------------------------------------------------------------------------
    # 3. YouCam Timeout / Outage
    # -------------------------------------------------------------------------
    print("\n[Case 3/5] Testing YouCam Timeout (Graceful Degradation)...")
    valid_img = Image.new("RGB", (64, 64), color="green")
    buf = io.BytesIO()
    valid_img.save(buf, format="JPEG")
    valid_bytes = buf.getvalue()

    with patch("app.routers.candidates.get_or_create_user", return_value=owner), \
         patch("app.routers.candidates.upload_image", return_value={"url": "https://res.cloudinary.com/test.jpg", "public_id": "p"}), \
         patch("app.routers.candidates.analyze_image", return_value={"category": "top", "color": "green", "pattern": "solid", "style": "casual", "season": "summer", "material": "cotton", "provider_used": "gemini"}), \
         patch("app.routers.candidates.generate_tryon", side_effect=TryOnTimeoutError("YouCam connection timed out after 15000ms")), \
         patch("app.routers.candidates.generate_embedding", return_value=[0.1]*512), \
         patch("app.routers.candidates.find_near_duplicate", return_value=None), \
         patch("app.routers.candidates.upsert_wardrobe_embedding"):

        res_tryon_degrade = client.post(
            "/api/candidates",
            files={"file": ("garment.jpg", valid_bytes, "image/jpeg")},
        )

    data_tryon = res_tryon_degrade.json()
    tryon_block = data_tryon.get("tryon", {})
    print(f"  • Candidate intake status: {res_tryon_degrade.status_code} (completed without 500 error)")
    print(f"  • tryon_degraded flag:     {tryon_block.get('tryon_degraded')}")
    print(f"  • Fit tightness fallback:  {tryon_block.get('fit_tightness')} (neutral)")
    print(f"  • Silhouette fallback:     {tryon_block.get('silhouette')} (neutral)")
    print(f"  • Render URL fallback:     {tryon_block.get('render_url')}")
    print(f"  • Errors recorded:         \"{data_tryon.get('errors', {}).get('tryon')}\"")

    if (
        res_tryon_degrade.status_code == 201
        and tryon_block.get("tryon_degraded") is True
        and tryon_block.get("fit_tightness") == "regular"
        and tryon_block.get("silhouette") == "relaxed"
    ):
        print("  --> PASS: YouCam timeout degraded cleanly without session crash.")
        passed += 1
    else:
        print("  --> FAIL: YouCam degradation did not return expected fallback values.")

    # -------------------------------------------------------------------------
    # 4. Cart with > 5 items
    # -------------------------------------------------------------------------
    print("\n[Case 4/5] Testing What-If Lab with > 5 items (6 items)...")
    with patch("app.routers.what_if.get_or_create_user", return_value=owner):
        res_enum_6 = client.post("/api/what-if/enumerate", json={"item_ids": [10, 20, 30, 40, 50, 60]})
        res_score_6 = client.post("/api/what-if/score", json={"item_ids": [10, 20, 30, 40, 50, 60]})

    print(f"  • What-If enumerate status: {res_enum_6.status_code}")
    print(f"    Detail: \"{res_enum_6.json().get('detail')}\"")
    print(f"  • What-If score status:     {res_score_6.status_code}")
    print(f"    Detail: \"{res_score_6.json().get('detail')}\"")

    if (
        res_enum_6.status_code == 400
        and res_score_6.status_code == 400
        and "between 3 and 5" in res_enum_6.json().get("detail", "")
        and "exponentially" in res_enum_6.json().get("detail", "").lower()
    ):
        print("  --> PASS: Cart with > 5 items rejected cleanly explaining exponential growth.")
        passed += 1
    else:
        print("  --> FAIL: Cart with > 5 items did not reject with expected explanation.")

    # -------------------------------------------------------------------------
    # 5. Cart with exactly 1 item
    # -------------------------------------------------------------------------
    print("\n[Case 5/5] Testing What-If Lab with exactly 1 item...")
    with patch("app.routers.what_if.get_or_create_user", return_value=owner):
        res_enum_1 = client.post("/api/what-if/enumerate", json={"item_ids": [42]})
        res_score_1 = client.post("/api/what-if/score", json={"item_ids": [42]})

    print(f"  • What-If enumerate status: {res_enum_1.status_code}")
    print(f"    Detail: \"{res_enum_1.json().get('detail')}\"")
    print(f"  • What-If score status:     {res_score_1.status_code}")
    print(f"    Detail: \"{res_score_1.json().get('detail')}\"")

    if (
        res_enum_1.status_code == 400
        and res_score_1.status_code == 400
        and "cart-level reasoning does not apply to a single item" in res_enum_1.json().get("detail", "").lower()
        and "buy score" in res_enum_1.json().get("detail", "").lower()
    ):
        print("  --> PASS: Cart with 1 item rejected cleanly with guidance pointing to Buy Score.")
        passed += 1
    else:
        print("  --> FAIL: Cart with 1 item did not reject with guidance message.")

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print("\n" + DIVIDER)
    print(f" VERIFICATION SUMMARY: {passed}/{total} Edge Cases Hardened & Verified Successfully")
    print(DIVIDER)

    app.dependency_overrides.clear()
    return passed == total


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
