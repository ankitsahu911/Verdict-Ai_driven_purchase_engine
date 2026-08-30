"""
Unit and Integration Tests for Milestone 16: Complete Ranked Outfits Engine.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import GarmentAttributes, User, WardrobeItem
from app.services.outfit_service import (
    are_items_pairwise_compatible,
    build_ranked_outfit_combinations,
    check_season_compatibility,
    check_style_compatibility,
    generate_templated_reason,
)


class TestMilestone16RankedOutfits(unittest.TestCase):
    def test_season_compatibility_rules(self):
        """Test season compatibility and seasonal mismatch rejection."""
        # Exact season match
        compat, reason, score = check_season_compatibility("summer", "summer")
        self.assertTrue(compat)
        self.assertIn("exact summer season match", reason)
        self.assertEqual(score, 10)

        # All-season versatile match
        compat, reason, score = check_season_compatibility("all-season", "winter")
        self.assertTrue(compat)
        self.assertIn("all-season", reason)
        self.assertEqual(score, 5)

        # Incompatible mismatch (winter vs summer)
        compat, reason, score = check_season_compatibility("winter", "summer")
        self.assertFalse(compat)
        self.assertIsNone(reason)

    def test_style_adjacency_rules(self):
        """Test style/occasion adjacency rules."""
        # Exact style match
        compat, reason, score = check_style_compatibility("casual", "casual")
        self.assertTrue(compat)
        self.assertEqual(score, 10)

        # Adjacent style match (casual & smart-casual)
        compat, reason, score = check_style_compatibility("casual", "smart-casual")
        self.assertTrue(compat)
        self.assertEqual(score, 5)

        # Incompatible non-adjacent styles (athletic & formal)
        compat, reason, score = check_style_compatibility("athletic", "formal")
        self.assertFalse(compat)

    def test_pairwise_item_compatibility(self):
        """Test full pairwise validation across category, color, season, and style."""
        item1 = {
            "attributes": {"category": "top", "color": "navy", "season": "all-season", "style": "casual"}
        }
        item2 = {
            "attributes": {"category": "bottom", "color": "beige", "season": "all-season", "style": "casual"}
        }
        item3 = {
            "attributes": {"category": "bottom", "color": "neon pink", "season": "winter", "style": "formal"}
        }

        # Item 1 and Item 2 are compatible across all axes
        compat12, reasons12, score12 = are_items_pairwise_compatible(item1, item2)
        self.assertTrue(compat12)
        self.assertTrue(len(reasons12) >= 3)
        self.assertTrue(score12 > 0)

        # Item 1 and Item 3 are incompatible due to style/season mismatch
        compat13, reasons13, score13 = are_items_pairwise_compatible(item1, item3)
        self.assertFalse(compat13)

    def test_build_ranked_outfit_combinations(self):
        """Test multi-piece combination building, pairwise validation, scoring, and ranking."""
        candidate = {
            "wardrobe_item_id": 1,
            "cloudinary_url": "https://res.cloudinary.com/test/navy_top.jpg",
            "attributes": {"category": "top", "color": "navy", "season": "all-season", "style": "casual"},
        }

        # Wardrobe Item 1: Bottom (Beige, all-season, casual)
        bottom1 = WardrobeItem(id=101, user_id=1, cloudinary_url="https://res.cloudinary.com/test/chinos.jpg")
        bottom1.attributes = GarmentAttributes(category="bottom", color="beige", season="all-season", style="casual")

        # Wardrobe Item 2: Footwear (White, all-season, casual)
        shoes1 = WardrobeItem(id=102, user_id=1, cloudinary_url="https://res.cloudinary.com/test/sneakers.jpg")
        shoes1.attributes = GarmentAttributes(category="footwear", color="white", season="all-season", style="casual")

        # Wardrobe Item 3: Incompatible Bottom (Winter-only formal velvet pants)
        bottom2 = WardrobeItem(id=103, user_id=1, cloudinary_url="https://res.cloudinary.com/test/formal.jpg")
        bottom2.attributes = GarmentAttributes(category="bottom", color="purple", season="winter", style="formal")

        wardrobe = [bottom1, shoes1, bottom2]

        combos = build_ranked_outfit_combinations(candidate, wardrobe, top_n=5)

        # Must find at least 1 valid complete outfit (top + bottom1 + shoes1)
        self.assertTrue(len(combos) >= 1)
        top_combo = combos[0]

        # Verify outfit structure
        self.assertIn("total_score", top_combo)
        self.assertIn("reason_summary", top_combo)
        self.assertIn("navy top", top_combo["reason_summary"])
        self.assertTrue(len(top_combo["items"]) == 2)  # bottom + footwear

        # Ensure formal bottom2 was rejected from all valid combinations
        combo_item_ids = [item["wardrobe_item_id"] for item in top_combo["items"]]
        self.assertIn(101, combo_item_ids)
        self.assertIn(102, combo_item_ids)
        self.assertNotIn(103, combo_item_ids)

    def test_outfit_combinations_api_endpoint(self):
        """Test GET /api/candidates/{id}/outfit-combinations endpoint."""
        candidate_item = WardrobeItem(id=60, user_id=1, is_candidate=True, cloudinary_url="https://res.cloudinary.com/test/top.jpg")
        candidate_item.attributes = GarmentAttributes(category="top", color="black", season="all-season", style="casual")

        bottom_item = WardrobeItem(id=61, user_id=1, is_candidate=False, cloudinary_url="https://res.cloudinary.com/test/bottom.jpg")
        bottom_item.attributes = GarmentAttributes(category="bottom", color="denim", season="all-season", style="casual")

        shoes_item = WardrobeItem(id=62, user_id=1, is_candidate=False, cloudinary_url="https://res.cloudinary.com/test/shoes.jpg")
        shoes_item.attributes = GarmentAttributes(category="footwear", color="white", season="all-season", style="casual")

        mock_owner = User(id=1, firebase_uid="uid123", email="user@test.com")

        def db_query_side_effect(model_cls):
            query_mock = MagicMock()
            if model_cls == User:
                query_mock.filter.return_value.first.return_value = mock_owner
            elif model_cls == WardrobeItem:
                filter_mock = MagicMock()
                filter_mock.first.return_value = candidate_item
                filter_mock.all.return_value = [bottom_item, shoes_item]
                query_mock.filter.return_value = filter_mock
            return query_mock

        mock_db = MagicMock()
        mock_db.query.side_effect = db_query_side_effect
        mock_user = {"uid": "uid123", "email": "user@test.com"}

        import asyncio
        from app.routers.candidates import get_candidate_outfit_combinations

        response = asyncio.run(
            get_candidate_outfit_combinations(
                candidate_id=60,
                user=mock_user,
                db=mock_db,
            )
        )

        self.assertEqual(response["candidate_id"], 60)
        self.assertTrue(response["total_combinations_found"] >= 1)
        first_combo = response["combinations"][0]
        self.assertIn("reason_summary", first_combo)
        self.assertIn("total_score", first_combo)
        self.assertTrue(len(first_combo["items"]) >= 2)


if __name__ == "__main__":
    unittest.main()
