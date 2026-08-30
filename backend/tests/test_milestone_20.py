"""
Unit and Integration Tests for Milestone 20: Versatility & Redundancy Axis Scorers.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.decision_engine.schema import AxisScore, DecisionAxis
from app.decision_engine.scorers.redundancy import score_redundancy
from app.decision_engine.scorers.versatility import score_versatility
from app.models import GarmentAttributes, User, WardrobeItem


class TestMilestone20AxisScorers(unittest.TestCase):
    @patch("app.decision_engine.scorers.versatility.build_ranked_outfit_combinations")
    def test_versatility_scorer_traceable(self, mock_outfit_builder):
        """Test versatility score changes traceably with outfit combinations count."""
        mock_db = MagicMock()

        candidate = WardrobeItem(id=10, user_id=1, is_candidate=True, cloudinary_url="https://res.cloudinary.com/test.jpg")
        candidate.attributes = GarmentAttributes(category="top", color="navy", style="casual")

        def db_query_side_effect(model_cls):
            q = MagicMock()
            if model_cls == WardrobeItem:
                q.filter.return_value.first.return_value = candidate
                q.filter.return_value.all.return_value = []
            return q

        mock_db.query.side_effect = db_query_side_effect

        # Test 1: 0 combinations -> 0.0 versatility score
        mock_outfit_builder.return_value = []
        score_0 = score_versatility(10, mock_db)
        self.assertEqual(score_0.axis, DecisionAxis.VERSATILITY)
        self.assertEqual(score_0.score, 0.0)
        self.assertEqual(score_0.source_agent, "outfit_composition")
        self.assertIn("Does not pair", score_0.reason)

        # Test 2: 3 combinations -> 60.0 versatility score
        mock_outfit_builder.return_value = [
            {"outfit_id": "outfit_1", "total_score": 50},
            {"outfit_id": "outfit_2", "total_score": 45},
            {"outfit_id": "outfit_3", "total_score": 40},
        ]
        score_3 = score_versatility(10, mock_db)
        self.assertEqual(score_3.score, 60.0)
        self.assertIn("Pairs into 3 complete outfits", score_3.reason)

        # Test 3: 5 combinations -> 100.0 versatility score
        mock_outfit_builder.return_value = [{"outfit_id": f"outfit_{i}", "total_score": 50} for i in range(5)]
        score_5 = score_versatility(10, mock_db)
        self.assertEqual(score_5.score, 100.0)

    def test_redundancy_scorer_traceable(self):
        """Test redundancy score inverts duplicate similarity pct (higher = more unique)."""
        mock_db = MagicMock()

        # Item 1: No duplicate match -> 100.0 score (favorable / unique)
        item_unique = WardrobeItem(id=20, user_id=1, is_candidate=True, duplicate_similarity_pct=None)

        # Item 2: 87.0% duplicate match -> 13.0 score (largely redundant)
        item_dup = WardrobeItem(id=21, user_id=1, is_candidate=True, duplicate_similarity_pct=87.0, duplicate_match_item_id=99)

        def db_query_side_effect(target_id):
            q = MagicMock()
            if target_id == 20:
                q.filter.return_value.first.return_value = item_unique
            else:
                q.filter.return_value.first.return_value = item_dup
            return q

        mock_db.query.side_effect = lambda model_cls: db_query_side_effect(20 if model_cls == WardrobeItem else 20)

        # Query unique item
        res_unique = score_redundancy(20, mock_db)
        self.assertEqual(res_unique.axis, DecisionAxis.REDUNDANCY)
        self.assertEqual(res_unique.score, 100.0)
        self.assertEqual(res_unique.source_agent, "duplicate_detection")
        self.assertIn("No close match", res_unique.reason)

        # Query duplicate item
        mock_db.query.side_effect = lambda model_cls: db_query_side_effect(21)
        res_dup = score_redundancy(21, mock_db)
        self.assertEqual(res_dup.score, 13.0)  # 100.0 - 87.0 = 13.0
        self.assertIn("87.0% similar to an item you already own", res_dup.reason)

        # Acceptance Criteria: changing candidate duplicate match visibly changes axis score
        self.assertGreater(res_unique.score, res_dup.score)

    @patch("app.routers.candidates.score_redundancy")
    @patch("app.routers.candidates.score_versatility")
    def test_get_candidate_axis_scores_endpoint(self, mock_score_v, mock_score_r):
        """Test GET /api/candidates/{id}/axes returns extensible list of implemented axis scores."""
        mock_score_v.return_value = AxisScore(
            axis=DecisionAxis.VERSATILITY,
            score=80.0,
            reason="Pairs into 4 outfits.",
            source_agent="outfit_composition",
        )
        mock_score_r.return_value = AxisScore(
            axis=DecisionAxis.REDUNDANCY,
            score=100.0,
            reason="No duplicate.",
            source_agent="duplicate_detection",
        )

        mock_owner = User(id=1, firebase_uid="uid123", email="user@test.com")
        candidate = WardrobeItem(id=50, user_id=1, is_candidate=True)

        def db_query_side_effect(model_cls):
            q = MagicMock()
            if model_cls == User:
                q.filter.return_value.first.return_value = mock_owner
            else:
                q.filter.return_value.first.return_value = candidate
            return q

        mock_db = MagicMock()
        mock_db.query.side_effect = db_query_side_effect
        mock_user = {"uid": "uid123", "email": "user@test.com"}

        import asyncio
        from app.routers.candidates import get_candidate_axis_scores

        res = asyncio.run(
            get_candidate_axis_scores(
                candidate_id=50,
                user=mock_user,
                db=mock_db,
            )
        )

        self.assertEqual(res["candidate_id"], 50)
        self.assertGreaterEqual(res["total_axes"], 2)
        axes_by_name = {a["axis"]: a for a in res["axes"]}
        self.assertIn("versatility", axes_by_name)
        self.assertEqual(axes_by_name["versatility"]["score"], 80.0)
        self.assertIn("redundancy", axes_by_name)
        self.assertEqual(axes_by_name["redundancy"]["score"], 100.0)


if __name__ == "__main__":
    unittest.main()
