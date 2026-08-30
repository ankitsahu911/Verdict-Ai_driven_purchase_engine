"""
Unit and Integration Tests for Milestone 17: Persistence Catch-Up & Economics Agent (Cost-Per-Wear).
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import GarmentAttributes, User, WardrobeItem
from app.services.economics_service import calculate_cost_per_wear


class TestMilestone17Economics(unittest.TestCase):
    def test_calculate_cost_per_wear_division(self):
        """Test cost-per-wear division: price / baseline_wears."""
        # Top: 30 wears baseline. $150 / 30 = $5.00/wear
        res_top = calculate_cost_per_wear(category="top", price=150.0)
        self.assertEqual(res_top["cost_per_wear"], 5.00)
        self.assertEqual(res_top["baseline_wears_used"], 30)
        self.assertEqual(res_top["category"], "top")

        # Bottom: 35 wears baseline. $100 / 35 = $2.86/wear
        res_bottom = calculate_cost_per_wear(category="jeans", price=100.0)
        self.assertEqual(res_bottom["cost_per_wear"], 2.86)
        self.assertEqual(res_bottom["baseline_wears_used"], 35)

        # Outerwear: 15 wears baseline. $150 / 15 = $10.00/wear
        res_coat = calculate_cost_per_wear(category="jacket", price=150.0)
        self.assertEqual(res_coat["cost_per_wear"], 10.00)
        self.assertEqual(res_coat["baseline_wears_used"], 15)

    def test_calculate_cost_per_wear_missing_price(self):
        """Test calculate_cost_per_wear raises ValueError if price is None or <= 0."""
        with self.assertRaises(ValueError):
            calculate_cost_per_wear("top", price=None)

        with self.assertRaises(ValueError):
            calculate_cost_per_wear("top", price=0.0)

    @patch("app.routers.candidates.find_near_duplicate")
    @patch("app.routers.candidates.upsert_wardrobe_embedding")
    @patch("app.routers.candidates.generate_embedding")
    @patch("app.routers.candidates.generate_tryon")
    @patch("app.routers.candidates.analyze_image")
    @patch("app.routers.candidates.upload_image")
    @patch("app.routers.candidates._stream_to_temp")
    @patch("app.routers.candidates._file_is_allowed")
    def test_candidate_intake_persists_evaluation_fields(
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
        """Test POST /api/candidates writes evaluation fields to DB row."""
        mock_file_allowed.return_value = True
        mock_stream_temp.return_value = ("/tmp/dummy.jpg", 1024)
        mock_upload_image.return_value = {
            "url": "https://res.cloudinary.com/test/candidate.jpg",
            "public_id": "verdict/candidates/uid123/abc",
        }
        mock_analyze_image.return_value = {
            "category": "top",
            "color": "black",
            "pattern": "solid",
            "style": "casual",
            "season": "fall",
            "material": "cotton",
        }
        mock_generate_tryon.return_value = {
            "render_url": "https://youcam.com/render_123.jpg",
            "fit_tightness": "regular",
            "silhouette": "relaxed",
            "notes": "Good fit",
        }
        mock_generate_embedding.return_value = [0.1] * 512
        mock_find_duplicate.return_value = {
            "wardrobe_item_id": 99,
            "similarity_percentage": 92.5,
            "distance": 0.075,
            "metadata": {"category": "top"},
        }

        mock_db = MagicMock()
        mock_owner = User(id=1, firebase_uid="uid123", email="user@test.com")
        mock_dup_item = WardrobeItem(id=99, user_id=1, is_candidate=False, cloudinary_url="https://res.cloudinary.com/test/dup.jpg")
        mock_dup_item.attributes = GarmentAttributes(category="top")

        def db_query_side_effect(model_cls):
            query_mock = MagicMock()
            if model_cls == User:
                query_mock.filter.return_value.first.return_value = mock_owner
            elif model_cls == WardrobeItem:
                query_mock.filter.return_value.first.return_value = mock_dup_item
            return query_mock

        mock_db.query.side_effect = db_query_side_effect

        mock_file = MagicMock()
        mock_file.filename = "candidate.jpg"
        mock_file.content_type = "image/jpeg"
        mock_user = {"uid": "uid123", "email": "user@test.com"}

        import asyncio
        from app.routers.candidates import evaluate_candidate_item

        response = asyncio.run(
            evaluate_candidate_item(
                file=mock_file,
                price=120.0,
                user=mock_user,
                db=mock_db,
            )
        )

        self.assertEqual(response["price"], 120.0)

        # Verify WardrobeItem was added with evaluation fields persisted
        added_objects = [call[0][0] for call in mock_db.add.call_args_list]
        candidate_item = next(obj for obj in added_objects if isinstance(obj, WardrobeItem))
        self.assertEqual(candidate_item.price, 120.0)
        self.assertEqual(candidate_item.tryon_render_url, "https://youcam.com/render_123.jpg")
        self.assertEqual(candidate_item.fit_tightness, "regular")
        self.assertEqual(candidate_item.silhouette, "relaxed")
        self.assertEqual(candidate_item.duplicate_match_item_id, 99)
        self.assertEqual(candidate_item.duplicate_similarity_pct, 92.5)

    def test_update_candidate_price_endpoint(self):
        """Test PATCH /api/candidates/{id}/price endpoint."""
        candidate_item = WardrobeItem(id=70, user_id=1, is_candidate=True, price=None)
        mock_owner = User(id=1, firebase_uid="uid123", email="user@test.com")

        mock_db = MagicMock()
        filter_mock = MagicMock()
        filter_mock.first.return_value = candidate_item
        mock_db.query.return_value.filter.return_value = filter_mock

        def db_query_side_effect(model_cls):
            q_mock = MagicMock()
            if model_cls == User:
                q_mock.filter.return_value.first.return_value = mock_owner
            else:
                q_mock.filter.return_value.first.return_value = candidate_item
            return q_mock

        mock_db.query.side_effect = db_query_side_effect
        mock_user = {"uid": "uid123", "email": "user@test.com"}

        import asyncio
        from app.routers.candidates import PriceUpdateRequest, update_candidate_price

        res = asyncio.run(
            update_candidate_price(
                candidate_id=70,
                payload=PriceUpdateRequest(price=85.50),
                user=mock_user,
                db=mock_db,
            )
        )

        self.assertEqual(res["candidate_id"], 70)
        self.assertEqual(res["price"], 85.50)
        self.assertEqual(candidate_item.price, 85.50)

    def test_get_candidate_economics_endpoint(self):
        """Test GET /api/candidates/{id}/economics endpoint."""
        candidate_item = WardrobeItem(id=80, user_id=1, is_candidate=True, price=120.0)
        candidate_item.attributes = GarmentAttributes(category="top")
        mock_owner = User(id=1, firebase_uid="uid123", email="user@test.com")

        def db_query_side_effect(model_cls):
            q_mock = MagicMock()
            if model_cls == User:
                q_mock.filter.return_value.first.return_value = mock_owner
            else:
                q_mock.filter.return_value.first.return_value = candidate_item
            return q_mock

        mock_db = MagicMock()
        mock_db.query.side_effect = db_query_side_effect
        mock_user = {"uid": "uid123", "email": "user@test.com"}

        import asyncio
        from app.routers.candidates import get_candidate_economics

        res = asyncio.run(
            get_candidate_economics(
                candidate_id=80,
                user=mock_user,
                db=mock_db,
            )
        )

        self.assertEqual(res["candidate_id"], 80)
        self.assertEqual(res["price"], 120.0)
        self.assertEqual(res["cost_per_wear"], 4.00)  # 120 / 30 = 4.00
        self.assertEqual(res["baseline_wears_used"], 30)
        self.assertEqual(res["category"], "top")
        self.assertIsNotNone(res["return_risk"])
        self.assertEqual(res["return_risk"]["score"], 20)


if __name__ == "__main__":
    unittest.main()
