import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.auth import get_current_user
from app.db import get_db
from app.decision_engine.schema import AxisScore, BuyScoreResult, DecisionAxis
from app.models import WardrobeItem
from verdict_backend.main import app


class TestMilestone27OpportunityCost(unittest.TestCase):
    def setUp(self):
        self.mock_user = {
            "uid": "test_m27_uid",
            "email": "m27@example.com",
            "name": "Test M27 User",
        }
        app.dependency_overrides[get_current_user] = lambda: self.mock_user
        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_opportunity_cost_compare_success(self):
        mock_owner = MagicMock(id=42, firebase_uid="test_m27_uid")

        cand = MagicMock(id=101, user_id=42, price=150.0, is_candidate=True)
        alt1 = MagicMock(id=201, user_id=42, price=60.0, is_candidate=True)
        alt2 = MagicMock(id=202, user_id=42, price=75.0, is_candidate=True)

        items_map = {101: cand, 201: alt1, 202: alt2}

        def mock_query(model):
            q = MagicMock()
            def mock_filter(*args, **kwargs):
                f = MagicMock()
                f.all.return_value = [cand, alt1, alt2]
                f.first.return_value = cand
                return f
            q.filter.side_effect = mock_filter
            return q

        self.mock_db.query.side_effect = mock_query

        # Mock M23 synthesize_buy_score
        mock_cand_buy_score = BuyScoreResult(
            candidate_id=101,
            verdict="buy",
            overall_score=78.0,
            headline_reason="BUY: High versatility standalone piece.",
            axes=[
                AxisScore(axis=DecisionAxis.VERSATILITY, score=40.0, reason="Pairs into 2 outfits", source_agent="outfit_composition"),
                AxisScore(axis=DecisionAxis.REDUNDANCY, score=90.0, reason="Unique", source_agent="duplicate_detection"),
                AxisScore(axis=DecisionAxis.SEASONAL_RELEVANCE, score=100.0, reason="In season", source_agent="vision_agent"),
                AxisScore(axis=DecisionAxis.BUDGET_IMPACT, score=70.0, reason="Decent CPW", source_agent="economics_agent"),
                AxisScore(axis=DecisionAxis.STYLE_ALIGNMENT, score=80.0, reason="Style match", source_agent="style_analysis"),
                AxisScore(axis=DecisionAxis.OCCASION_COVERAGE, score=90.0, reason="Fills gap", source_agent="occasion_analysis"),
            ],
            weights_used={"versatility": 0.1667},
            created_at="2026-09-03T12:00:00Z",
        )

        # Mock M26 evaluate_subset
        mock_bundle_eval = {
            "size": 2,
            "item_ids": [201, 202],
            "overall_score": 85.0,
            "verdict": "buy",
            "headline_reason": "BUY: High synergy bundle unlocking 6 complete outfits.",
            "total_price": 135.0,
            "axes": [
                {"axis": "versatility", "score": 80.0, "reason": "Unlocks 6 outfits with synergy", "source_agent": "outfit_composition"},
                {"axis": "redundancy", "score": 85.0, "reason": "Low redundancy", "source_agent": "duplicate_detection"},
                {"axis": "seasonal_relevance", "score": 90.0, "reason": "In season", "source_agent": "vision_agent"},
                {"axis": "budget_impact", "score": 85.0, "reason": "Efficient combined CPW", "source_agent": "economics_agent"},
                {"axis": "style_alignment", "score": 85.0, "reason": "Great style fit", "source_agent": "style_analysis"},
                {"axis": "occasion_coverage", "score": 85.0, "reason": "Good coverage", "source_agent": "occasion_analysis"},
            ],
        }

        with patch("app.routers.opportunity_cost.get_or_create_user", return_value=mock_owner), \
             patch("app.routers.opportunity_cost.synthesize_buy_score", return_value=mock_cand_buy_score), \
             patch("app.routers.opportunity_cost.evaluate_subset", return_value=mock_bundle_eval):

            response = self.client.post(
                "/api/opportunity-cost/compare",
                json={
                    "candidate_item_id": 101,
                    "alternative_item_ids": [201, 202],
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["candidate"]["candidate_id"], 101)
        self.assertEqual(data["candidate"]["overall_score"], 78.0)
        self.assertEqual(data["candidate_versatility"], 40.0)

        self.assertEqual(data["alternative_bundle"]["item_ids"], [201, 202])
        self.assertEqual(data["alternative_bundle"]["overall_score"], 85.0)
        self.assertEqual(data["alternative_bundle_versatility"], 80.0)

        # Versatility delta = 80.0 - 40.0 = +40.0
        self.assertEqual(data["versatility_delta"], 40.0)

    def test_opportunity_cost_requires_exactly_2_alternative_items(self):
        mock_owner = MagicMock(id=42, firebase_uid="test_m27_uid")
        with patch("app.routers.opportunity_cost.get_or_create_user", return_value=mock_owner):
            # Test with only 1 item
            res1 = self.client.post(
                "/api/opportunity-cost/compare",
                json={"candidate_item_id": 101, "alternative_item_ids": [201]},
            )
            self.assertEqual(res1.status_code, 400)
            self.assertIn("exactly 2", res1.json()["detail"])

            # Test with 3 items
            res2 = self.client.post(
                "/api/opportunity-cost/compare",
                json={"candidate_item_id": 101, "alternative_item_ids": [201, 202, 203]},
            )
            self.assertEqual(res2.status_code, 400)
            self.assertIn("exactly 2", res2.json()["detail"])

    def test_opportunity_cost_rejects_foreign_item(self):
        mock_owner = MagicMock(id=42, firebase_uid="test_m27_uid")

        cand = MagicMock(id=101, user_id=42)
        alt1 = MagicMock(id=201, user_id=42)
        alt2 = MagicMock(id=202, user_id=999)  # Foreign user

        def mock_query(model):
            q = MagicMock()
            q.filter.return_value.all.return_value = [cand, alt1, alt2]
            return q

        self.mock_db.query.side_effect = mock_query

        with patch("app.routers.opportunity_cost.get_or_create_user", return_value=mock_owner):
            response = self.client.post(
                "/api/opportunity-cost/compare",
                json={"candidate_item_id": 101, "alternative_item_ids": [201, 202]},
            )

        self.assertEqual(response.status_code, 403)
        self.assertIn("do not have access", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
