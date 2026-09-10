"""
Unit and Integration Tests for Milestone 37:
Automated, Repeatable Single-Item End-to-End Test Run.
Verifies the complete 4-stage pipeline execution via actual API endpoints:
  1. Intake Flow: POST /api/candidates
  2. Outfit Matches: GET /api/candidates/{id}/outfit-matches
  3. Decision Axes: GET /api/candidates/{id}/axes
  4. Buy Score: GET /api/candidates/{id}/buy-score
"""

import io
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.auth import get_current_user
from app.db import Base, get_db
from app.models import ExtractionSource, GarmentAttributes, User, WardrobeItem
from verdict_backend.main import app


class TestMilestone37SingleItemE2E(unittest.TestCase):
    def setUp(self):
        self.test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.test_engine)
        self.TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.test_engine
        )
        def override_get_db():
            db = self.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        self.mock_user = {
            "uid": "test_m37_user",
            "email": "m37@example.com",
            "name": "M37 Tester",
        }
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = lambda: self.mock_user
        self.client = TestClient(app)

        # Seed test user and existing wardrobe items
        db = self.TestingSessionLocal()
        user = User(
            firebase_uid=self.mock_user["uid"],
            email=self.mock_user["email"],
            display_name=self.mock_user["name"],
        )
        from datetime import datetime, timezone
        user.created_at = datetime.now(timezone.utc)
        db.add(user)
        db.commit()
        db.refresh(user)
        self.user_id = user.id

        # Seed 1 owned top and 1 owned bottom
        owned_item = WardrobeItem(
            user_id=user.id,
            cloudinary_url="https://example.com/owned_jeans.jpg",
            is_candidate=False,
            price=60.0,
            uploaded_at=datetime.now(timezone.utc),
        )
        db.add(owned_item)
        db.commit()
        db.refresh(owned_item)

        attrs = GarmentAttributes(
            wardrobe_item_id=owned_item.id,
            category="bottom",
            color="blue",
            pattern="solid",
            style="casual",
            season="all-season",
            material="denim",
            extraction_source=ExtractionSource.MANUAL_OVERRIDE,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(attrs)
        db.commit()
        db.close()

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_test_candidate_images_exist(self):
        """Verify the 5 real candidate garment images exist in backend/data/test_candidates/."""
        candidates_dir = Path(__file__).resolve().parent.parent / "data" / "test_candidates"
        self.assertTrue(candidates_dir.exists(), "test_candidates directory must exist")

        expected_files = [
            "candidate_1_white_tee.jpg",
            "candidate_2_khaki_jacket.jpg",
            "candidate_3_blue_jeans.jpg",
            "candidate_4_black_dress.jpg",
            "candidate_5_leather_jacket.jpg",
        ]
        for fname in expected_files:
            p = candidates_dir / fname
            self.assertTrue(p.exists(), f"Candidate photo {fname} must exist on disk")
            self.assertGreater(p.stat().st_size, 1000, f"{fname} must be a real image > 1KB")

    @patch("app.routers.candidates.find_near_duplicate")
    @patch("app.routers.candidates.upsert_wardrobe_embedding")
    @patch("app.routers.candidates.generate_embedding")
    @patch("app.routers.candidates.generate_tryon")
    @patch("app.routers.candidates.analyze_image")
    @patch("app.routers.candidates.upload_image")
    def test_full_pipeline_api_sequence_for_single_candidate(
        self,
        mock_upload,
        mock_analyze,
        mock_tryon,
        mock_embedding,
        mock_upsert_emb,
        mock_find_dup,
    ):
        """Test full 4-stage pipeline sequence through actual HTTP API endpoints."""
        mock_upload.return_value = {
            "url": "https://example.com/candidate_jacket.jpg",
            "public_id": "cand_123",
        }
        mock_analyze.return_value = {
            "category": "outerwear",
            "color": "olive",
            "pattern": "solid",
            "style": "casual",
            "season": "all-season",
            "material": "cotton",
            "provider_used": "gemini",
        }
        mock_tryon.return_value = {
            "render_url": "https://youcam.com/render_123.jpg",
            "fit_tightness": "regular",
            "silhouette": "relaxed",
            "tryon_degraded": False,
        }
        mock_embedding.return_value = [0.05] * 512
        mock_find_dup.return_value = {
            "wardrobe_item_id": 1,
            "similarity_percentage": 25.0,
            "distance": 0.75,
            "metadata": {"category": "bottom"},
        }

        # Stage 1: Intake Flow POST /api/candidates
        img_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 200
        files = {"file": ("test_candidate.jpg", io.BytesIO(img_bytes), "image/jpeg")}
        data = {"price": "85.0"}
        resp_intake = self.client.post("/api/candidates", files=files, data=data)
        self.assertEqual(resp_intake.status_code, 201)
        intake_json = resp_intake.json()
        self.assertIn("candidate_item_id", intake_json)
        cand_id = intake_json["candidate_item_id"]
        self.assertEqual(intake_json["attributes"]["category"], "outerwear")

        # Stage 2: Outfit Matches GET /api/candidates/{id}/outfit-matches
        resp_matches = self.client.get(f"/api/candidates/{cand_id}/outfit-matches")
        self.assertEqual(resp_matches.status_code, 200)
        matches_json = resp_matches.json()
        self.assertIn("matches", matches_json)
        self.assertIn("total_matches", matches_json)

        # Stage 3: Decision Axes GET /api/candidates/{id}/axes
        resp_axes = self.client.get(f"/api/candidates/{cand_id}/axes")
        self.assertEqual(resp_axes.status_code, 200)
        axes_json = resp_axes.json()
        self.assertEqual(axes_json["total_axes"], 6)
        axes_names = [a["axis"] for a in axes_json["axes"]]
        self.assertIn("versatility", axes_names)
        self.assertIn("redundancy", axes_names)
        self.assertIn("seasonal_relevance", axes_names)
        self.assertIn("budget_impact", axes_names)
        self.assertIn("style_alignment", axes_names)
        self.assertIn("occasion_coverage", axes_names)

        # Stage 4: Final Buy Score Synthesis GET /api/candidates/{id}/buy-score
        resp_buy = self.client.get(f"/api/candidates/{cand_id}/buy-score")
        self.assertEqual(resp_buy.status_code, 200)
        buy_json = resp_buy.json()
        self.assertIn("overall_score", buy_json)
        self.assertIn("verdict", buy_json)
        self.assertIn(buy_json["verdict"], ["buy", "consider", "skip"])
        self.assertIn("confidence", buy_json)
        self.assertIn("level", buy_json["confidence"])
        self.assertIn("reasoning", buy_json["confidence"])
        self.assertIn("summary_panel", buy_json)


if __name__ == "__main__":
    unittest.main()
