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


class TestMilestone28OpportunityCostCard(unittest.TestCase):
    def setUp(self):
        self.mock_user = {
            "uid": "test_m28_uid",
            "email": "m28@example.com",
            "name": "Test M28 User",
        }
        app.dependency_overrides[get_current_user] = lambda: self.mock_user
        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_raw_outfit_count_threading_integrity(self):
        mock_owner = MagicMock(id=42, firebase_uid="test_m28_uid")

        cand = MagicMock(id=101, user_id=42, price=200.0, is_candidate=True)
        cand.attributes = MagicMock(category="jacket", color="black")

        alt1 = MagicMock(id=201, user_id=42, price=75.0, is_candidate=True)
        alt1.attributes = MagicMock(category="top", color="white")

        alt2 = MagicMock(id=202, user_id=42, price=90.0, is_candidate=True)
        alt2.attributes = MagicMock(category="bottom", color="blue")

        def mock_query(model):
            q = MagicMock()
            q.filter.return_value.all.return_value = [cand, alt1, alt2]
            return q

        self.mock_db.query.side_effect = mock_query

        # Mock M23 single candidate Buy Score with raw_evidence combinations_count = 2
        mock_cand_buy_score = BuyScoreResult(
            candidate_id=101,
            verdict="consider",
            overall_score=64.0,
            headline_reason="CONSIDER: Moderate versatility.",
            axes=[
                AxisScore(
                    axis=DecisionAxis.VERSATILITY,
                    score=40.0,
                    reason="Pairs into 2 outfits",
                    source_agent="outfit_composition",
                    raw_evidence={"combinations_count": 2},
                ),
                AxisScore(axis=DecisionAxis.REDUNDANCY, score=80.0, reason="Unique", source_agent="duplicate_detection"),
                AxisScore(axis=DecisionAxis.SEASONAL_RELEVANCE, score=90.0, reason="In season", source_agent="vision_agent"),
                AxisScore(axis=DecisionAxis.BUDGET_IMPACT, score=50.0, reason="Moderate CPW", source_agent="economics_agent"),
                AxisScore(axis=DecisionAxis.STYLE_ALIGNMENT, score=70.0, reason="Style match", source_agent="style_analysis"),
                AxisScore(axis=DecisionAxis.OCCASION_COVERAGE, score=54.0, reason="Occasion match", source_agent="occasion_analysis"),
            ],
            weights_used={"versatility": 0.1667},
            created_at="2026-09-04T00:00:00Z",
        )

        # Mock M26 alternative bundle with raw_evidence total_outfits_count = 7
        mock_bundle_eval = {
            "size": 2,
            "item_ids": [201, 202],
            "overall_score": 83.5,
            "verdict": "buy",
            "headline_reason": "BUY: High synergy pair creating 7 new outfits.",
            "total_price": 165.0,
            "axes": [
                {
                    "axis": "versatility",
                    "score": 87.5,
                    "reason": "Unlocks 7 outfits with synergy",
                    "source_agent": "outfit_composition",
                    "raw_evidence": {"total_outfits_count": 7, "synergy_outfits_count": 3},
                },
                {"axis": "redundancy", "score": 90.0, "reason": "No redundancy", "source_agent": "duplicate_detection"},
                {"axis": "seasonal_relevance", "score": 95.0, "reason": "In season", "source_agent": "vision_agent"},
                {"axis": "budget_impact", "score": 80.0, "reason": "Great combined value", "source_agent": "economics_agent"},
                {"axis": "style_alignment", "score": 75.0, "reason": "Good style fit", "source_agent": "style_analysis"},
                {"axis": "occasion_coverage", "score": 75.0, "reason": "Expands occasion", "source_agent": "occasion_analysis"},
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

        # Check raw integer outfit counts
        self.assertEqual(data["candidate_outfit_count"], 2)
        self.assertEqual(data["alternative_bundle_outfit_count"], 7)
        self.assertEqual(data["outfit_count_delta"], 5)  # 7 - 2 = +5

        # Check names formatted for template copy
        self.assertEqual(data["candidate_name"], "Black Jacket")
        self.assertEqual(data["alternative_names"], ["White Top", "Blue Bottom"])

        # Check scores
        self.assertEqual(data["candidate"]["overall_score"], 64.0)
        self.assertEqual(data["alternative_bundle"]["overall_score"], 83.5)
        self.assertEqual(data["versatility_delta"], 47.5)


if __name__ == "__main__":
    unittest.main()
