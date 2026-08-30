"""
Unit and Integration Tests for Milestone 22: Style Alignment & Occasion Coverage Axis Scorers.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.decision_engine.schema import AxisScore, DecisionAxis
from app.decision_engine.scorers.occasion_coverage import score_occasion_coverage
from app.decision_engine.scorers.style_alignment import score_style_alignment
from app.decision_engine.scorers.style_distribution import get_wardrobe_style_distribution
from app.models import GarmentAttributes, User, WardrobeItem


class TestMilestone22AxisScorers(unittest.TestCase):
    def test_wardrobe_style_distribution_helper(self):
        """Test calculation of wardrobe style percentages."""
        mock_db = MagicMock()

        # 10 items: 6 casual, 3 smart-casual, 1 formal
        items = []
        for i in range(6):
            w = WardrobeItem(id=i + 1, user_id=1, is_candidate=False)
            w.attributes = GarmentAttributes(style="casual")
            items.append(w)
        for i in range(3):
            w = WardrobeItem(id=i + 7, user_id=1, is_candidate=False)
            w.attributes = GarmentAttributes(style="smart-casual")
            items.append(w)
        w_formal = WardrobeItem(id=10, user_id=1, is_candidate=False)
        w_formal.attributes = GarmentAttributes(style="formal")
        items.append(w_formal)

        mock_db.query.return_value.filter.return_value.all.return_value = items
        dist = get_wardrobe_style_distribution(user_id=1, db=mock_db)

        self.assertEqual(dist["casual"], 60.0)
        self.assertEqual(dist["smart-casual"], 30.0)
        self.assertEqual(dist["formal"], 10.0)

    def test_style_alignment_and_occasion_coverage_tension(self):
        """Test the inverse relationship (design tension) between style alignment and occasion coverage."""
        mock_db = MagicMock()

        # Distribution: 60% casual, 10% formal
        candidate_casual = WardrobeItem(id=100, user_id=1, is_candidate=True)
        candidate_casual.attributes = GarmentAttributes(style="casual")

        candidate_formal = WardrobeItem(id=101, user_id=1, is_candidate=True)
        candidate_formal.attributes = GarmentAttributes(style="formal")

        with patch(
            "app.decision_engine.scorers.style_alignment.get_wardrobe_style_distribution",
            return_value={"casual": 60.0, "formal": 10.0},
        ), patch(
            "app.decision_engine.scorers.occasion_coverage.get_wardrobe_style_distribution",
            return_value={"casual": 60.0, "formal": 10.0},
        ):
            # 1. Casual Item:
            # - Style Alignment: 60.0 (high alignment with established casual style)
            # - Occasion Coverage: 40.0 (100 - 60 = 40.0, low gap-filling benefit)
            mock_db.query.return_value.filter.return_value.first.return_value = candidate_casual
            sa_casual = score_style_alignment(100, mock_db)
            oc_casual = score_occasion_coverage(100, mock_db)

            self.assertEqual(sa_casual.axis, DecisionAxis.STYLE_ALIGNMENT)
            self.assertEqual(sa_casual.score, 60.0)
            self.assertEqual(sa_casual.source_agent, "style_analysis")
            self.assertIn("60.0% of your wardrobe is already casual", sa_casual.reason)

            self.assertEqual(oc_casual.axis, DecisionAxis.OCCASION_COVERAGE)
            self.assertEqual(oc_casual.score, 40.0)
            self.assertEqual(oc_casual.source_agent, "occasion_analysis")
            self.assertIn("adds little new occasion coverage", oc_casual.reason)

            # 2. Formal Item:
            # - Style Alignment: 10.0 (low alignment with everyday style)
            # - Occasion Coverage: 90.0 (100 - 10 = 90.0, high gap-filling benefit)
            mock_db.query.return_value.filter.return_value.first.return_value = candidate_formal
            sa_formal = score_style_alignment(101, mock_db)
            oc_formal = score_occasion_coverage(101, mock_db)

            self.assertEqual(sa_formal.score, 10.0)
            self.assertEqual(oc_formal.score, 90.0)
            self.assertIn("fills a real occasion coverage gap", oc_formal.reason)

            # Inverse relationship proof:
            self.assertGreater(sa_casual.score, sa_formal.score)
            self.assertGreater(oc_formal.score, oc_casual.score)

    def test_empty_wardrobe_fallback_handling(self):
        """Test neutral fallback score (50.0) when wardrobe has no existing items."""
        mock_db = MagicMock()
        candidate = WardrobeItem(id=102, user_id=1, is_candidate=True)
        candidate.attributes = GarmentAttributes(style="casual")

        with patch(
            "app.decision_engine.scorers.style_alignment.get_wardrobe_style_distribution",
            return_value={},
        ), patch(
            "app.decision_engine.scorers.occasion_coverage.get_wardrobe_style_distribution",
            return_value={},
        ):
            mock_db.query.return_value.filter.return_value.first.return_value = candidate
            sa = score_style_alignment(102, mock_db)
            oc = score_occasion_coverage(102, mock_db)

            self.assertEqual(sa.score, 50.0)
            self.assertEqual(oc.score, 50.0)
            self.assertIn("default baseline", sa.reason)
            self.assertIn("default baseline", oc.reason)

    @patch("app.routers.candidates.score_occasion_coverage")
    @patch("app.routers.candidates.score_style_alignment")
    @patch("app.routers.candidates.score_budget_impact")
    @patch("app.routers.candidates.score_seasonal_relevance")
    @patch("app.routers.candidates.score_redundancy")
    @patch("app.routers.candidates.score_versatility")
    def test_get_candidate_axis_scores_returns_all_6_axes(
        self,
        mock_v,
        mock_r,
        mock_s,
        mock_b,
        mock_sa,
        mock_oc,
    ):
        """Test GET /api/candidates/{id}/axes returns all 6 decision axes."""
        mock_v.return_value = AxisScore(
            axis=DecisionAxis.VERSATILITY,
            score=80.0,
            reason="Pairs into 4 outfits.",
            source_agent="outfit_composition",
        )
        mock_r.return_value = AxisScore(
            axis=DecisionAxis.REDUNDANCY,
            score=95.0,
            reason="Unique piece.",
            source_agent="duplicate_detection",
        )
        mock_s.return_value = AxisScore(
            axis=DecisionAxis.SEASONAL_RELEVANCE,
            score=100.0,
            reason="In season.",
            source_agent="vision_agent",
        )
        mock_b.return_value = AxisScore(
            axis=DecisionAxis.BUDGET_IMPACT,
            score=94.0,
            reason="Efficient CPW.",
            source_agent="economics_agent",
        )
        mock_sa.return_value = AxisScore(
            axis=DecisionAxis.STYLE_ALIGNMENT,
            score=60.0,
            reason="Fits casual style.",
            source_agent="style_analysis",
        )
        mock_oc.return_value = AxisScore(
            axis=DecisionAxis.OCCASION_COVERAGE,
            score=40.0,
            reason="Low gap filling.",
            source_agent="occasion_analysis",
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
        self.assertEqual(res["total_axes"], 6)
        self.assertEqual(len(res["axes"]), 6)

        axes_returned = [a["axis"] for a in res["axes"]]
        expected_axes = [
            "versatility",
            "redundancy",
            "seasonal_relevance",
            "budget_impact",
            "style_alignment",
            "occasion_coverage",
        ]
        self.assertEqual(axes_returned, expected_axes)


if __name__ == "__main__":
    unittest.main()
