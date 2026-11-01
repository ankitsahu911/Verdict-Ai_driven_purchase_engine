import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.decision_engine.orchestrator import synthesize_buy_score
from app.decision_engine.schema import AxisScore, DecisionAxis
from app.models import GarmentAttributes, WardrobeItem
from app.routers.candidates import _reconcile_duplicate_match
from app.services.duplicate_matching import (
    attribute_duplicate_score,
    attributes_are_duplicate_compatible,
    color_family,
)
from app.services.image_color import photos_have_compatible_colours


class TestDuplicateGuardrails(unittest.TestCase):
    def test_same_colour_footwear_sets_a_high_duplicate_floor(self):
        score, reason = attribute_duplicate_score(
            {"category": "shoes", "color": "navy blue", "style": "casual"},
            {"category": "sneakers", "color": "blue", "style": "casual"},
        )
        self.assertGreaterEqual(score, 85.0)
        self.assertIn("same blue footwear", reason)
        self.assertEqual(color_family("navy blue"), "blue")

    def test_colour_conflict_rejects_false_visual_duplicate(self):
        self.assertFalse(
            attributes_are_duplicate_compatible(
                {"category": "bottom", "color": "brown"},
                {"category": "jeans", "color": "black"},
            )
        )
        score, reason = attribute_duplicate_score(
            {"category": "bottom", "color": "brown"},
            {"category": "jeans", "color": "black"},
        )
        self.assertEqual(score, 0.0)
        self.assertIsNone(reason)

    def test_black_trousers_and_black_jeans_remain_duplicate_candidates(self):
        score, reason = attribute_duplicate_score(
            {"category": "bottom", "color": "black", "style": "smart-casual"},
            {"category": "jeans", "color": "black", "style": "smart-casual"},
        )
        self.assertGreaterEqual(score, 85.0)
        self.assertIn("same black bottom", reason)

    def test_attribute_match_beats_wrong_colour_visual_hit(self):
        black_jeans = WardrobeItem(id=21, user_id=1, is_candidate=False)
        black_jeans.attributes = GarmentAttributes(category="bottom", color="black")
        brown_jeans = WardrobeItem(id=22, user_id=1, is_candidate=False)
        brown_jeans.attributes = GarmentAttributes(category="bottom", color="brown")

        db = MagicMock()
        query = db.query.return_value
        query.filter.return_value.all.return_value = [black_jeans, brown_jeans]
        query.filter.return_value.first.return_value = brown_jeans

        result = _reconcile_duplicate_match(
            {"category": "bottom", "color": "black", "style": "casual"},
            {
                "wardrobe_item_id": 22,
                "similarity_percentage": 93.0,
                "distance": 0.07,
                "metadata": {},
            },
            1,
            db,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["wardrobe_item_id"], 21)
        self.assertLess(result["similarity_percentage"], 93.0)

    @patch("app.services.image_color.dominant_colour_families")
    def test_photo_colour_check_rejects_black_and_blue_garments(self, mock_colours):
        mock_colours.side_effect = [{"black"}, {"blue"}]
        self.assertFalse(photos_have_compatible_colours("candidate.jpg", "existing.jpg"))

    @patch("app.services.image_color._open_image")
    def test_real_photo_colour_check_rejects_black_and_blue_images(self, mock_open_image):
        mock_open_image.side_effect = [
            Image.new("RGB", (100, 140), (15, 15, 15)),
            Image.new("RGB", (100, 140), (25, 85, 190)),
        ]
        self.assertFalse(photos_have_compatible_colours("black.jpg", "blue.jpg"))

    @patch("app.routers.candidates.photos_have_compatible_colours", return_value=False)
    def test_photo_colour_conflict_suppresses_attribute_duplicate(self, _mock_colours):
        black_trousers = WardrobeItem(id=24, user_id=1, is_candidate=False)
        black_trousers.cloudinary_url = "http://example.test/black-trousers.jpg"
        black_trousers.attributes = GarmentAttributes(category="bottom", color="black")

        db = MagicMock()
        query = db.query.return_value
        query.filter.return_value.all.return_value = [black_trousers]
        query.filter.return_value.first.return_value = black_trousers

        result = _reconcile_duplicate_match(
            {"category": "bottom", "color": "black"},
            None,
            1,
            db,
            "http://example.test/blue-shorts.jpg",
        )

        self.assertIsNone(result)

    def test_missing_attributes_never_exposes_a_visual_only_duplicate(self):
        result = _reconcile_duplicate_match(
            None,
            {"wardrobe_item_id": 31, "similarity_percentage": 96.0, "distance": 0.04},
            1,
            MagicMock(),
        )
        self.assertIsNone(result)

    @patch("app.decision_engine.orchestrator.score_occasion_coverage")
    @patch("app.decision_engine.orchestrator.score_style_alignment")
    @patch("app.decision_engine.orchestrator.score_budget_impact")
    @patch("app.decision_engine.orchestrator.score_seasonal_relevance")
    @patch("app.decision_engine.orchestrator.score_redundancy")
    @patch("app.decision_engine.orchestrator.score_versatility")
    def test_high_duplicate_risk_cannot_be_a_buy(
        self, mock_v, mock_r, mock_s, mock_b, mock_sa, mock_oc
    ):
        def axis(axis_name, score):
            return AxisScore(axis=axis_name, score=score, reason="test", source_agent="test")

        mock_v.return_value = axis(DecisionAxis.VERSATILITY, 95.0)
        mock_r.return_value = axis(DecisionAxis.REDUNDANCY, 15.0)
        mock_s.return_value = axis(DecisionAxis.SEASONAL_RELEVANCE, 95.0)
        mock_b.return_value = axis(DecisionAxis.BUDGET_IMPACT, 95.0)
        mock_sa.return_value = axis(DecisionAxis.STYLE_ALIGNMENT, 95.0)
        mock_oc.return_value = axis(DecisionAxis.OCCASION_COVERAGE, 95.0)

        candidate = WardrobeItem(id=1, user_id=1, is_candidate=True)
        candidate.attributes = None
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = candidate

        result = synthesize_buy_score(1, db, persist=False)
        self.assertEqual(result.verdict, "skip")
        self.assertLess(result.overall_score, 45.0)


if __name__ == "__main__":
    unittest.main()
