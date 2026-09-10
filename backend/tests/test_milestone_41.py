"""
Milestone 41 Unit Tests: Hardening Verdict against 5 Critical Edge Cases.
1. Empty Wardrobe (0 items): Outfit composition returns empty-but-valid response; ChromaDB duplicate search returns empty; Versatility returns 0.0 with human-readable reason.
2. Malformed Photo Upload: Corrupted image bytes fail cleanly with "couldn't read this image" error instead of 500.
3. YouCam Timeout / Outage: TryOnTimeoutError gracefully degrades to fallback with tryon_degraded=True and neutral fit signals.
4. Cart with > 5 Items: What-If Lab rejects with HTTP 400 and clear message explaining exponential combinatorial growth.
5. Cart with exactly 1 Item: What-If Lab rejects with HTTP 400 and points user to the single-item Buy Score flow.
"""

import io
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from PIL import Image

from app.auth import get_current_user
from app.db import get_db
from app.models import GarmentAttributes, User, WardrobeItem
from app.decision_engine.scorers.versatility import score_versatility
from app.decision_engine.subset_evaluator import score_subset_versatility
from app.services.chroma_service import find_near_duplicate, query_similar_items
from app.services.vision_service import analyze_image, VisionServiceError
from app.services.tryon_service import (
    DEFAULT_FALLBACK_FIT_TIGHTNESS,
    DEFAULT_FALLBACK_SILHOUETTE,
    TryOnTimeoutError,
    build_tryon_fallback,
)
from verdict_backend.main import app


class TestMilestone41EdgeCases(unittest.TestCase):
    def setUp(self):
        self.mock_user = {
            "uid": "m41_edge_user",
            "email": "m41@example.com",
            "name": "M41 Edge Tester",
        }
        app.dependency_overrides[get_current_user] = lambda: self.mock_user
        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    # =========================================================================
    # Edge Case 1: Empty Wardrobe (brand-new user, zero items uploaded)
    # =========================================================================
    def test_edge_case_1a_empty_wardrobe_outfit_compatible_items(self):
        """Empty wardrobe returns empty-but-valid compatible items response with guidance message."""
        owner = MagicMock(id=101, firebase_uid="m41_edge_user")
        candidate = WardrobeItem(id=901, user_id=101, is_candidate=True)
        candidate.attributes = GarmentAttributes(category="top", color="navy", pattern="solid")

        with patch("app.routers.candidates.get_or_create_user", return_value=owner):
            def mock_query(model):
                q = MagicMock()
                if model == WardrobeItem:
                    q.filter.return_value.first.return_value = candidate
                    q.filter.return_value.all.return_value = []
                elif model == GarmentAttributes:
                    q.filter.return_value.first.return_value = candidate.attributes
                return q

            self.mock_db.query.side_effect = mock_query

            resp = self.client.get("/api/candidates/901/outfit-matches")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["candidate_id"], 901)
            self.assertEqual(data["total_matches"], 0)
            self.assertEqual(data["matches"], [])
            self.assertIn("no compatible items found yet", data["message"].lower())

    def test_edge_case_1b_empty_wardrobe_outfit_combinations(self):
        """Empty wardrobe returns empty-but-valid outfit combinations response with guidance message."""
        owner = MagicMock(id=101, firebase_uid="m41_edge_user")
        candidate = WardrobeItem(id=901, user_id=101, is_candidate=True)
        candidate.attributes = GarmentAttributes(category="top", color="navy", pattern="solid")

        with patch("app.routers.candidates.get_or_create_user", return_value=owner):
            def mock_query(model):
                q = MagicMock()
                if model == WardrobeItem:
                    q.filter.return_value.first.return_value = candidate
                    q.filter.return_value.all.return_value = []
                elif model == GarmentAttributes:
                    q.filter.return_value.first.return_value = candidate.attributes
                return q

            self.mock_db.query.side_effect = mock_query

            resp = self.client.get("/api/candidates/901/outfit-combinations")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["candidate_id"], 901)
            self.assertEqual(data["total_combinations_found"], 0)
            self.assertEqual(data["combinations"], [])
            self.assertIn("no compatible items found yet", data["message"].lower())

    def test_edge_case_1c_empty_wardrobe_duplicate_detection_chromadb(self):
        """ChromaDB query against zero stored vectors for that user handles empty state gracefully."""
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0

        with patch("app.services.chroma_service.get_wardrobe_collection", return_value=mock_collection):
            results = query_similar_items([0.1] * 512, user_id=101, top_k=5)
            self.assertEqual(results, [])
            mock_collection.query.assert_not_called()

        with patch("app.services.chroma_service.query_similar_items", return_value=[]):
            duplicate = find_near_duplicate([0.1] * 512, user_id=101)
            self.assertIsNone(duplicate)

    def test_edge_case_1d_empty_wardrobe_versatility_score_clean_zero(self):
        """Versatility scorer returns normalized score 0.0 with clear reason for empty wardrobe."""
        mock_db = MagicMock()
        candidate = WardrobeItem(id=901, user_id=101, is_candidate=True, cloudinary_url="https://res.cloudinary.com/test.jpg")
        candidate.attributes = GarmentAttributes(category="top", color="navy", style="casual")

        def db_query_side_effect(model_cls):
            q = MagicMock()
            if model_cls == WardrobeItem:
                q.filter.return_value.first.return_value = candidate
                q.filter.return_value.all.return_value = []
            return q

        mock_db.query.side_effect = db_query_side_effect

        score = score_versatility(901, mock_db)
        self.assertEqual(score.score, 0.0)
        self.assertIn("no compatible items found yet", score.reason.lower())

    def test_edge_case_1e_empty_wardrobe_subset_versatility_clean_handling(self):
        """Subset versatility evaluator returns clean guidance when existing wardrobe is empty."""
        mock_db = MagicMock()
        cand1 = WardrobeItem(id=901, user_id=101, is_candidate=True)
        cand1.attributes = GarmentAttributes(category="top", color="white", style="casual")
        cand2 = WardrobeItem(id=902, user_id=101, is_candidate=True)
        cand2.attributes = GarmentAttributes(category="bottom", color="navy", style="casual")

        q_cand = MagicMock()
        q_cand.all.return_value = [cand1, cand2]

        q_wardrobe = MagicMock()
        q_wardrobe.all.return_value = []

        mock_filter = MagicMock(side_effect=[q_cand, q_wardrobe])
        mock_db.query.return_value.filter = mock_filter

        score_obj = score_subset_versatility([901, 902], mock_db)
        self.assertIsInstance(score_obj.score, float)
        self.assertIn("no compatible items found yet", score_obj.reason.lower())

    # =========================================================================
    # Edge Case 2: Malformed Photo Upload (.jpg/.png with corrupt/unreadable bytes)
    # =========================================================================
    def test_edge_case_2a_malformed_photo_candidate_upload_rejected(self):
        """Malformed image file uploaded to /api/candidates returns HTTP 400 Bad Request with clear message."""
        owner = MagicMock(id=101, firebase_uid="m41_edge_user")
        with patch("app.routers.candidates.get_or_create_user", return_value=owner):
            corrupt_bytes = b"NOT_A_VALID_IMAGE_HEADER_CORRUPTED_FILE_DATA"
            resp = self.client.post(
                "/api/candidates",
                files={"file": ("malformed_garment.jpg", corrupt_bytes, "image/jpeg")},
            )
            self.assertEqual(resp.status_code, 400)
            data = resp.json()
            self.assertIn("couldn't read this image", data["detail"].lower())

    def test_edge_case_2b_malformed_photo_wardrobe_upload_clean_failure_entry(self):
        """Malformed image file uploaded to /api/wardrobe/upload records clean failure reason without crashing."""
        owner = MagicMock(id=101, firebase_uid="m41_edge_user")
        with patch("app.routers.wardrobe.get_or_create_user", return_value=owner):
            corrupt_bytes = b"CORRUPTED_WARDROBE_GARMENT_PHOTO_BYTES"
            resp = self.client.post(
                "/api/wardrobe/upload",
                files=[("files", ("corrupt_photo.png", corrupt_bytes, "image/png"))],
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["uploaded_count"], 0)
            self.assertEqual(data["failed_count"], 1)
            self.assertEqual(len(data["failed"]), 1)
            self.assertEqual(data["failed"][0]["filename"], "corrupt_photo.png")
            self.assertIn("couldn't read this image", data["failed"][0]["error"].lower())

    def test_edge_case_2c_malformed_photo_vision_service_raises_clean_error(self):
        """Passing a corrupted image path to analyze_image raises VisionServiceError with clean message."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"CORRUPTED_IMAGE_BYTES_FOR_VISION_TEST")
            tmp_path = f.name

        try:
            with self.assertRaises(VisionServiceError) as ctx:
                analyze_image(tmp_path)
            self.assertIn("couldn't read this image", str(ctx.exception).lower())
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # =========================================================================
    # Edge Case 3: YouCam Timeout (M33 Graceful Degradation)
    # =========================================================================
    def test_edge_case_3a_build_tryon_fallback_on_timeout(self):
        """build_tryon_fallback produces tryon_degraded=True, neutral fit values, and valid notes."""
        class CandidateStub:
            id = 701
            tryon_render_url = None
            fit_tightness = None
            silhouette = None
            cloudinary_url = "https://res.cloudinary.com/demo/image/upload/v1/garment.jpg"

        item = CandidateStub()
        fallback = build_tryon_fallback(item, error_reason="YouCam request timed out after 15s")
        self.assertTrue(fallback["tryon_degraded"])
        self.assertEqual(fallback["fit_tightness"], DEFAULT_FALLBACK_FIT_TIGHTNESS)
        self.assertEqual(fallback["silhouette"], DEFAULT_FALLBACK_SILHOUETTE)
        self.assertEqual(fallback["render_url"], item.cloudinary_url)
        self.assertIn("timed out", fallback["notes"].lower())

    def test_edge_case_3b_candidate_intake_survives_youcam_timeout(self):
        """Candidate intake completes successfully even when YouCam times out, recording degraded status."""
        owner = MagicMock(id=101, firebase_uid="m41_edge_user", model_photo_url="https://example.com/user.jpg")
        
        valid_img = Image.new("RGB", (100, 100), color="blue")
        img_bytes = io.BytesIO()
        valid_img.save(img_bytes, format="JPEG")
        raw_valid = img_bytes.getvalue()

        with patch("app.routers.candidates.get_or_create_user", return_value=owner), \
             patch("app.routers.candidates.upload_image", return_value={"url": "https://example.com/garment.jpg", "public_id": "p1"}), \
             patch("app.routers.candidates.analyze_image", return_value={
                 "category": "top", "color": "blue", "pattern": "solid", "style": "casual", "season": "summer", "material": "cotton", "provider_used": "gemini"
             }), \
             patch("app.routers.candidates.generate_tryon", side_effect=TryOnTimeoutError("YouCam timed out")), \
             patch("app.routers.candidates.generate_embedding", return_value=[0.1]*512), \
             patch("app.routers.candidates.find_near_duplicate", return_value=None), \
             patch("app.routers.candidates.upsert_wardrobe_embedding"):

            mock_cand_item = WardrobeItem(id=777, user_id=101, is_candidate=True)
            self.mock_db.add = MagicMock()
            self.mock_db.commit = MagicMock()
            self.mock_db.refresh = MagicMock()

            resp = self.client.post(
                "/api/candidates",
                files={"file": ("valid_garment.jpg", raw_valid, "image/jpeg")},
            )
            self.assertEqual(resp.status_code, 201)
            data = resp.json()
            self.assertIsNotNone(data["tryon"])
            self.assertTrue(data["tryon"]["tryon_degraded"])
            self.assertEqual(data["tryon"]["fit_tightness"], "regular")
            self.assertEqual(data["tryon"]["silhouette"], "relaxed")
            self.assertIn("tryon", data["errors"])
            self.assertIn("unavailable", data["errors"]["tryon"].lower())

    # =========================================================================
    # Edge Case 4: Cart with > 5 items
    # =========================================================================
    def test_edge_case_4a_what_if_enumerate_rejects_more_than_5_items(self):
        """POST /api/what-if/enumerate rejects > 5 items with HTTP 400 and explains combinatorial space."""
        owner = MagicMock(id=101, firebase_uid="m41_edge_user")
        with patch("app.routers.what_if.get_or_create_user", return_value=owner):
            resp = self.client.post(
                "/api/what-if/enumerate",
                json={"item_ids": [1, 2, 3, 4, 5, 6]},
            )
            self.assertEqual(resp.status_code, 400)
            detail = resp.json()["detail"]
            self.assertIn("between 3 and 5", detail)
            self.assertIn("exponentially", detail.lower())

    def test_edge_case_4b_what_if_score_rejects_more_than_5_items(self):
        """POST /api/what-if/score rejects > 5 items with HTTP 400 and explains combinatorial space."""
        owner = MagicMock(id=101, firebase_uid="m41_edge_user")
        with patch("app.routers.what_if.get_or_create_user", return_value=owner):
            resp = self.client.post(
                "/api/what-if/score",
                json={"item_ids": [1, 2, 3, 4, 5, 6, 7]},
            )
            self.assertEqual(resp.status_code, 400)
            detail = resp.json()["detail"]
            self.assertIn("between 3 and 5", detail)
            self.assertIn("exponentially", detail.lower())

    # =========================================================================
    # Edge Case 5: Cart with exactly 1 item
    # =========================================================================
    def test_edge_case_5a_what_if_enumerate_rejects_single_item(self):
        """POST /api/what-if/enumerate rejects 1 item with HTTP 400 and points to Buy Score."""
        owner = MagicMock(id=101, firebase_uid="m41_edge_user")
        with patch("app.routers.what_if.get_or_create_user", return_value=owner):
            resp = self.client.post(
                "/api/what-if/enumerate",
                json={"item_ids": [42]},
            )
            self.assertEqual(resp.status_code, 400)
            detail = resp.json()["detail"]
            self.assertIn("cart-level reasoning does not apply to a single item", detail.lower())
            self.assertIn("buy score", detail.lower())
            self.assertIn("between 3 and 5", detail)

    def test_edge_case_5b_what_if_score_rejects_single_item(self):
        """POST /api/what-if/score rejects 1 item with HTTP 400 and points to Buy Score."""
        owner = MagicMock(id=101, firebase_uid="m41_edge_user")
        with patch("app.routers.what_if.get_or_create_user", return_value=owner):
            resp = self.client.post(
                "/api/what-if/score",
                json={"item_ids": [42]},
            )
            self.assertEqual(resp.status_code, 400)
            detail = resp.json()["detail"]
            self.assertIn("cart-level reasoning does not apply to a single item", detail.lower())
            self.assertIn("buy score", detail.lower())
            self.assertIn("between 3 and 5", detail)


if __name__ == "__main__":
    unittest.main()
