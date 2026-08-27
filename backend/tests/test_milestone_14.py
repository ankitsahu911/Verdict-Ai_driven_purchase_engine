"""
Unit and Integration Tests for Milestone 14: Candidate Evaluation Orchestration Flow.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import ExtractionSource, GarmentAttributes, User, WardrobeItem
from app.services.tryon_service import TryOnServiceError
from app.services.vision_service import VisionServiceError


class TestMilestone14CandidateOrchestration(unittest.TestCase):
    @patch("app.routers.candidates.find_near_duplicate")
    @patch("app.routers.candidates.upsert_wardrobe_embedding")
    @patch("app.routers.candidates.generate_embedding")
    @patch("app.routers.candidates.generate_tryon")
    @patch("app.routers.candidates.analyze_image")
    @patch("app.routers.candidates.upload_image")
    @patch("app.routers.candidates._stream_to_temp")
    @patch("app.routers.candidates._file_is_allowed")
    def test_evaluate_candidate_success_flow(
        self,
        mock_file_allowed,
        mock_stream_temp,
        mock_upload_image,
        mock_analyze_image,
        mock_generate_tryon,
        mock_generate_embedding,
        mock_upsert_embedding,
        mock_find_duplicate,
    ):
        """Test full successful candidate evaluation orchestration flow."""
        mock_file_allowed.return_value = True
        mock_stream_temp.return_value = ("/tmp/dummy.jpg", 1024)
        mock_upload_image.return_value = {
            "url": "https://res.cloudinary.com/test/candidate.jpg",
            "public_id": "verdict/candidates/uid123/abc",
        }
        mock_analyze_image.return_value = {
            "category": "hoodie",
            "color": "black",
            "pattern": "solid",
            "style": "casual",
            "season": "fall",
            "material": "cotton",
        }
        mock_generate_tryon.return_value = {
            "render_url": "https://youcam.com/render.jpg",
            "fit_tightness": "regular",
            "silhouette": "relaxed",
            "notes": "Looks great",
        }
        mock_generate_embedding.return_value = [0.1] * 512
        mock_find_duplicate.return_value = {
            "wardrobe_item_id": 42,
            "similarity_percentage": 93.0,
            "distance": 0.07,
            "metadata": {"category": "hoodie", "cloudinary_url": "https://res.cloudinary.com/test/existing.jpg"},
        }

        # Mock DB, owner user, and matched item
        mock_owner = User(id=1, firebase_uid="uid123", email="user@test.com")
        mock_matched_item = WardrobeItem(
            id=42,
            user_id=1,
            cloudinary_url="https://res.cloudinary.com/test/existing.jpg",
            is_candidate=False,
        )
        mock_matched_item.attributes = GarmentAttributes(category="hoodie")

        def db_query_side_effect(model_cls):
            query_mock = MagicMock()
            if model_cls == User:
                query_mock.filter.return_value.first.return_value = mock_owner
            elif model_cls == WardrobeItem:
                query_mock.filter.return_value.first.return_value = mock_matched_item
            else:
                query_mock.filter.return_value.first.return_value = None
            return query_mock

        mock_db = MagicMock()
        mock_db.query.side_effect = db_query_side_effect

        mock_file = MagicMock()
        mock_file.filename = "candidate_photo.jpg"
        mock_file.content_type = "image/jpeg"
        mock_user = {"uid": "uid123", "email": "user@test.com"}

        import asyncio
        from app.routers.candidates import evaluate_candidate_item

        response = asyncio.run(
            evaluate_candidate_item(
                file=mock_file,
                user=mock_user,
                db=mock_db,
            )
        )

        self.assertIn("candidate_item_id", response)
        self.assertEqual(response["cloudinary_url"], "https://res.cloudinary.com/test/candidate.jpg")
        self.assertEqual(response["attributes"]["category"], "hoodie")
        self.assertEqual(response["tryon"]["render_url"], "https://youcam.com/render.jpg")
        self.assertEqual(response["duplicate"]["similarity_percentage"], 93.0)
        self.assertIsNone(response["errors"])

    @patch("app.routers.candidates.find_near_duplicate")
    @patch("app.routers.candidates.upsert_wardrobe_embedding")
    @patch("app.routers.candidates.generate_embedding")
    @patch("app.routers.candidates.generate_tryon")
    @patch("app.routers.candidates.analyze_image")
    @patch("app.routers.candidates.upload_image")
    @patch("app.routers.candidates._stream_to_temp")
    @patch("app.routers.candidates._file_is_allowed")
    def test_evaluate_candidate_tryon_graceful_error(
        self,
        mock_file_allowed,
        mock_stream_temp,
        mock_upload_image,
        mock_analyze_image,
        mock_generate_tryon,
        mock_generate_embedding,
        mock_upsert_embedding,
        mock_find_duplicate,
    ):
        """Test graceful degradation when Try-On fails due to missing model photo."""
        mock_file_allowed.return_value = True
        mock_stream_temp.return_value = ("/tmp/dummy.jpg", 1024)
        mock_upload_image.return_value = {
            "url": "https://res.cloudinary.com/test/candidate.jpg",
            "public_id": "verdict/candidates/uid123/abc",
        }
        mock_analyze_image.return_value = {
            "category": "jacket",
            "color": "blue",
            "pattern": "solid",
            "style": "denim",
            "season": "all",
            "material": "denim",
        }
        # Try-On fails because model photo is missing
        mock_generate_tryon.side_effect = TryOnServiceError(
            "No model/user photo URL provided. Set YOUCAM_SRC_URL in .env or pass user_photo_url."
        )
        mock_generate_embedding.return_value = [0.2] * 512
        mock_find_duplicate.return_value = None

        mock_owner = User(id=1, firebase_uid="uid123", email="user@test.com")

        def db_query_side_effect(model_cls):
            query_mock = MagicMock()
            if model_cls == User:
                query_mock.filter.return_value.first.return_value = mock_owner
            else:
                query_mock.filter.return_value.first.return_value = None
            return query_mock

        mock_db = MagicMock()
        mock_db.query.side_effect = db_query_side_effect

        mock_file = MagicMock()
        mock_file.filename = "denim_jacket.jpg"
        mock_file.content_type = "image/jpeg"
        mock_user = {"uid": "uid123", "email": "user@test.com"}

        import asyncio
        from app.routers.candidates import evaluate_candidate_item

        response = asyncio.run(
            evaluate_candidate_item(
                file=mock_file,
                user=mock_user,
                db=mock_db,
            )
        )

        self.assertIn("candidate_item_id", response)
        self.assertEqual(response["attributes"]["category"], "jacket")
        self.assertIsNone(response["tryon"])
        self.assertIsNotNone(response["errors"])
        self.assertIn("tryon", response["errors"])
        self.assertIn("No model/user photo URL", response["errors"]["tryon"])


if __name__ == "__main__":
    unittest.main()
