"""
Unit and Integration Tests for Milestone 15: Rule-Based Outfit Pairing v1.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import GarmentAttributes, User, WardrobeItem
from app.services.outfit_service import (
    check_category_compatibility,
    check_color_harmony,
    find_compatible_items,
)


class TestMilestone15OutfitRules(unittest.TestCase):
    def test_category_compatibility_rules(self):
        """Test classical category compatibility table lookups."""
        # Top pairs with bottom, footwear, outerwear
        self.assertTrue(check_category_compatibility("top", "bottom")[0])
        self.assertTrue(check_category_compatibility("shirt", "pants")[0])
        self.assertTrue(check_category_compatibility("hoodie", "sneakers")[0])
        self.assertTrue(check_category_compatibility("top", "jacket")[0])

        # Dress pairs with footwear and outerwear, but NOT bottoms
        self.assertTrue(check_category_compatibility("dress", "heels")[0])
        self.assertTrue(check_category_compatibility("dress", "blazer")[0])
        self.assertFalse(check_category_compatibility("dress", "jeans")[0])

    def test_color_harmony_rules(self):
        """Test color harmony rules (neutrals vs non-neutrals)."""
        # Neutral candidate (navy) pairs with non-neutral wardrobe item (red)
        compat, reason = check_color_harmony("navy", "red")
        self.assertTrue(compat)
        self.assertEqual(reason, "color: candidate navy is neutral")

        # Neutral wardrobe item (black) pairs with non-neutral candidate (yellow)
        compat, reason = check_color_harmony("yellow", "black")
        self.assertTrue(compat)
        self.assertEqual(reason, "color: wardrobe black is neutral")

        # Non-neutrals in same color family (sky blue & royal blue)
        compat, reason = check_color_harmony("sky blue", "royal blue")
        self.assertTrue(compat)
        self.assertIn("same color family", reason)

        # Incompatible non-neutrals (red & green)
        compat, reason = check_color_harmony("red", "green")
        self.assertFalse(compat)
        self.assertIsNone(reason)

    def test_find_compatible_items_with_reasons(self):
        """Test find_compatible_items populates traceable matched_because rules."""
        candidate_attrs = {"category": "top", "color": "black"}

        # Wardrobe item 1: Bottom, Navy (compatible on category & neutral color)
        item1 = WardrobeItem(id=101, user_id=1, cloudinary_url="https://res.cloudinary.com/test/bottom1.jpg")
        item1.attributes = GarmentAttributes(category="bottom", color="navy")

        # Wardrobe item 2: Top, White (incompatible category: top does not pair with top)
        item2 = WardrobeItem(id=102, user_id=1, cloudinary_url="https://res.cloudinary.com/test/top2.jpg")
        item2.attributes = GarmentAttributes(category="top", color="white")

        # Wardrobe item 3: Footwear, Red (compatible on category & neutral candidate color)
        item3 = WardrobeItem(id=103, user_id=1, cloudinary_url="https://res.cloudinary.com/test/shoes3.jpg")
        item3.attributes = GarmentAttributes(category="footwear", color="red")

        wardrobe = [item1, item2, item3]

        matches = find_compatible_items(candidate_attrs, wardrobe)

        # Item 1 and Item 3 match, Item 2 is excluded
        self.assertEqual(len(matches), 2)
        matched_ids = [m["wardrobe_item_id"] for m in matches]
        self.assertIn(101, matched_ids)
        self.assertIn(103, matched_ids)
        self.assertNotIn(102, matched_ids)

        # Verify traceable matched_because reasons
        item1_match = next(m for m in matches if m["wardrobe_item_id"] == 101)
        self.assertIn("category: top pairs with bottom", item1_match["matched_because"])
        self.assertIn("color: candidate black is neutral", item1_match["matched_because"])

    def test_outfit_matches_api_endpoint(self):
        """Test GET /api/candidates/{id}/outfit-matches endpoint."""
        candidate_item = WardrobeItem(id=50, user_id=1, is_candidate=True)
        candidate_item.attributes = GarmentAttributes(category="top", color="navy")

        bottom_item = WardrobeItem(id=51, user_id=1, cloudinary_url="https://res.cloudinary.com/test/pants.jpg", is_candidate=False)
        bottom_item.attributes = GarmentAttributes(category="pants", color="white")

        mock_owner = User(id=1, firebase_uid="uid123", email="user@test.com")

        def db_query_side_effect(model_cls):
            query_mock = MagicMock()
            if model_cls == User:
                query_mock.filter.return_value.first.return_value = mock_owner
            elif model_cls == WardrobeItem:
                filter_mock = MagicMock()
                # Return candidate when querying by candidate ID, return list when querying existing items
                filter_mock.first.return_value = candidate_item
                filter_mock.all.return_value = [bottom_item]
                query_mock.filter.return_value = filter_mock
            return query_mock

        mock_db = MagicMock()
        mock_db.query.side_effect = db_query_side_effect
        mock_user = {"uid": "uid123", "email": "user@test.com"}

        import asyncio
        from app.routers.candidates import get_candidate_outfit_matches

        response = asyncio.run(
            get_candidate_outfit_matches(
                candidate_id=50,
                user=mock_user,
                db=mock_db,
            )
        )

        self.assertEqual(response["candidate_id"], 50)
        self.assertEqual(response["total_matches"], 1)
        self.assertEqual(response["matches"][0]["wardrobe_item_id"], 51)
        self.assertTrue(len(response["matches"][0]["matched_because"]) > 0)


if __name__ == "__main__":
    unittest.main()
