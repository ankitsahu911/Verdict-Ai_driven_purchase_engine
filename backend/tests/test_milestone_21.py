"""
Unit and Integration Tests for Milestone 21: Seasonal Relevance & Budget Impact Axis Scorers.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.decision_engine.schema import AxisScore, DecisionAxis
from app.decision_engine.scorers.budget_impact import score_budget_impact
from app.decision_engine.scorers.seasonal_relevance import score_seasonal_relevance
from app.models import GarmentAttributes, User, WardrobeItem


class TestMilestone21AxisScorers(unittest.TestCase):
    def test_seasonal_relevance_distance_scoring(self):
        """Test seasonal relevance scores vary traceably based on calendar proximity to target season."""
        mock_db = MagicMock()

        # In-season item in October (Fall: Sep-Nov) -> distance 0 -> score 100.0
        fall_item = WardrobeItem(id=1, user_id=1, is_candidate=True)
        fall_item.attributes = GarmentAttributes(season="fall", category="jacket")

        # Upcoming item in October (Winter: Dec-Feb) -> distance 2 -> score 60.0
        winter_item = WardrobeItem(id=2, user_id=1, is_candidate=True)
        winter_item.attributes = GarmentAttributes(season="winter", category="coat")

        # Off-season item in January (Summer: Jun-Aug) -> distance 5 -> score 20.0
        summer_item = WardrobeItem(id=3, user_id=1, is_candidate=True)
        summer_item.attributes = GarmentAttributes(season="summer", category="dress")

        # All-season item -> flat 95.0
        all_season_item = WardrobeItem(id=4, user_id=1, is_candidate=True)
        all_season_item.attributes = GarmentAttributes(season="all-season", category="shirt")

        # 1. Fall item in October
        mock_db.query.return_value.filter.return_value.first.return_value = fall_item
        res_fall = score_seasonal_relevance(1, mock_db, current_month=10)
        self.assertEqual(res_fall.axis, DecisionAxis.SEASONAL_RELEVANCE)
        self.assertEqual(res_fall.score, 100.0)
        self.assertEqual(res_fall.source_agent, "vision_agent")
        self.assertIn("currently in season (October)", res_fall.reason)

        # 2. Winter item in October (2 months away)
        mock_db.query.return_value.filter.return_value.first.return_value = winter_item
        res_winter = score_seasonal_relevance(2, mock_db, current_month=10)
        self.assertEqual(res_winter.score, 60.0)
        self.assertIn("2 months away", res_winter.reason)

        # 3. Summer item in January (5 months away)
        mock_db.query.return_value.filter.return_value.first.return_value = summer_item
        res_summer = score_seasonal_relevance(3, mock_db, current_month=1)
        self.assertEqual(res_summer.score, 20.0)
        self.assertIn("off-season", res_summer.reason)

        # 4. All-season item
        mock_db.query.return_value.filter.return_value.first.return_value = all_season_item
        res_all_season = score_seasonal_relevance(4, mock_db, current_month=1)
        self.assertEqual(res_all_season.score, 95.0)
        self.assertIn("wearable year-round", res_all_season.reason)

        # Acceptance Criteria: Changing candidate season visibly shifts score
        self.assertNotEqual(res_fall.score, res_winter.score)
        self.assertGreater(res_fall.score, res_summer.score)

    def test_budget_impact_price_and_return_risk_blending(self):
        """Test budget impact blends CPW efficiency (60%) and inverted return risk (40%)."""
        mock_db = MagicMock()

        # Affordable Top ($60): CPW = $2.00 <= $3.50 ceiling -> CPW score = 100.0
        # Return risk (regular fit) = 20 - 5 = 15% -> Inverted = 85.0
        # Blended = 0.60 * 100 + 0.40 * 85 = 60 + 34 = 94.0
        affordable_top = WardrobeItem(
            id=10,
            user_id=1,
            is_candidate=True,
            price=60.0,
            fit_tightness="regular",
        )
        affordable_top.attributes = GarmentAttributes(category="top")

        # Expensive Top ($210): CPW = $7.00 > $3.50 ceiling (2x) -> CPW score = 0.0
        # Return risk (tight fit) = 20 + 25 = 45% -> Inverted = 55.0
        # Blended = 0.60 * 0 + 0.40 * 55 = 22.0
        expensive_top = WardrobeItem(
            id=11,
            user_id=1,
            is_candidate=True,
            price=210.0,
            fit_tightness="tight",
        )
        expensive_top.attributes = GarmentAttributes(category="top")

        mock_db.query.return_value.filter.return_value.first.return_value = affordable_top
        res_afford = score_budget_impact(10, mock_db)
        self.assertEqual(res_afford.axis, DecisionAxis.BUDGET_IMPACT)
        self.assertEqual(res_afford.score, 94.0)
        self.assertEqual(res_afford.source_agent, "economics_agent")
        self.assertIn("Efficient cost-per-wear", res_afford.reason)

        mock_db.query.return_value.filter.return_value.first.return_value = expensive_top
        res_expensive = score_budget_impact(11, mock_db)
        self.assertEqual(res_expensive.score, 22.0)
        self.assertIn("High cost-per-wear", res_expensive.reason)

        # Acceptance Criteria: Changing candidate price visibly shifts score
        self.assertGreater(res_afford.score, res_expensive.score)

    @patch("app.routers.candidates.score_budget_impact")
    @patch("app.routers.candidates.score_seasonal_relevance")
    @patch("app.routers.candidates.score_redundancy")
    @patch("app.routers.candidates.score_versatility")
    def test_get_candidate_axis_scores_returns_4_axes(
        self,
        mock_score_v,
        mock_score_r,
        mock_score_s,
        mock_score_b,
    ):
        """Test GET /api/candidates/{id}/axes returns all 4 implemented axis scores."""
        mock_score_v.return_value = AxisScore(
            axis=DecisionAxis.VERSATILITY,
            score=80.0,
            reason="Pairs into 4 outfits.",
            source_agent="outfit_composition",
        )
        mock_score_r.return_value = AxisScore(
            axis=DecisionAxis.REDUNDANCY,
            score=95.0,
            reason="Unique piece.",
            source_agent="duplicate_detection",
        )
        mock_score_s.return_value = AxisScore(
            axis=DecisionAxis.SEASONAL_RELEVANCE,
            score=100.0,
            reason="In season.",
            source_agent="vision_agent",
        )
        mock_score_b.return_value = AxisScore(
            axis=DecisionAxis.BUDGET_IMPACT,
            score=94.0,
            reason="Efficient CPW.",
            source_agent="economics_agent",
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
        self.assertGreaterEqual(res["total_axes"], 4)

        axes_returned = [a["axis"] for a in res["axes"]]
        for axis_name in ["versatility", "redundancy", "seasonal_relevance", "budget_impact"]:
            self.assertIn(axis_name, axes_returned)


if __name__ == "__main__":
    unittest.main()
