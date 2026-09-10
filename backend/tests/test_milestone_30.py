import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.auth import get_current_user
from app.db import get_db
from app.decision_engine.schema import AxisScore, BuyScoreResult, ConfidenceResult, DecisionAxis
from app.decision_engine.subset_evaluator import evaluate_subset
from app.models import WardrobeItem
from verdict_backend.main import app


class TestMilestone30SurfaceConfidence(unittest.TestCase):
    def setUp(self):
        self.mock_user = {
            "uid": "test_m30_uid",
            "email": "m30@example.com",
            "name": "Test M30 User",
        }
        app.dependency_overrides[get_current_user] = lambda: self.mock_user
        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_evaluate_subset_empty_contains_confidence(self):
        result = evaluate_subset([], self.mock_db)
        self.assertIn("confidence", result)
        self.assertIn(result["confidence"]["level"], ["high", "medium", "low"])
        self.assertIsInstance(result["confidence"]["reasoning"], str)

    def test_evaluate_subset_non_empty_contains_confidence(self):
        item1 = MagicMock(id=1, user_id=42, price=50.0)
        item1.attributes = MagicMock(style="smart-casual", category="top", color="white")
        item2 = MagicMock(id=2, user_id=42, price=70.0)
        item2.attributes = MagicMock(style="smart-casual", category="bottom", color="blue")

        self.mock_db.query.return_value.filter.return_value.all.return_value = [item1, item2]

        with patch("app.decision_engine.subset_evaluator.score_subset_versatility", return_value=AxisScore(axis=DecisionAxis.VERSATILITY, score=80.0, reason="ok", source_agent="test")), \
             patch("app.decision_engine.subset_evaluator.score_subset_redundancy", return_value=AxisScore(axis=DecisionAxis.REDUNDANCY, score=75.0, reason="ok", source_agent="test")), \
             patch("app.decision_engine.subset_evaluator.score_subset_seasonal_relevance", return_value=AxisScore(axis=DecisionAxis.SEASONAL_RELEVANCE, score=70.0, reason="ok", source_agent="test")), \
             patch("app.decision_engine.subset_evaluator.score_subset_budget_impact", return_value=AxisScore(axis=DecisionAxis.BUDGET_IMPACT, score=65.0, reason="ok", source_agent="test")), \
             patch("app.decision_engine.subset_evaluator.score_subset_style_alignment", return_value=AxisScore(axis=DecisionAxis.STYLE_ALIGNMENT, score=70.0, reason="ok", source_agent="test")), \
             patch("app.decision_engine.subset_evaluator.score_subset_occasion_coverage", return_value=AxisScore(axis=DecisionAxis.OCCASION_COVERAGE, score=70.0, reason="ok", source_agent="test")):

            result = evaluate_subset([1, 2], self.mock_db)

        self.assertIn("confidence", result)
        self.assertIn(result["confidence"]["level"], ["high", "medium", "low"])
        self.assertIsInstance(result["confidence"]["reasoning"], str)
        # Because style is 'smart-casual', reasoning should mention category
        self.assertIn("smart-casual", result["confidence"]["reasoning"])

    def test_what_if_score_endpoint_returns_confidence(self):
        mock_owner = MagicMock(id=42, firebase_uid="test_m30_uid")
        items = []
        for i in [101, 102, 103]:
            itm = MagicMock(id=i, user_id=42, price=50.0)
            itm.attributes = MagicMock(category="top", color="black", style="casual")
            items.append(itm)

        def mock_query(model):
            q = MagicMock()
            q.filter.return_value.all.return_value = items
            q.filter.return_value.first.return_value = items[0]
            return q

        self.mock_db.query.side_effect = mock_query

        with patch("app.routers.what_if.get_or_create_user", return_value=mock_owner), \
             patch("app.decision_engine.subset_evaluator.score_redundancy", return_value=MagicMock(score=85.0)), \
             patch("app.decision_engine.subset_evaluator.score_seasonal_relevance", return_value=MagicMock(score=80.0)), \
             patch("app.decision_engine.subset_evaluator.score_budget_impact", return_value=MagicMock(score=75.0)), \
             patch("app.decision_engine.subset_evaluator.score_style_alignment", return_value=MagicMock(score=70.0)), \
             patch("app.decision_engine.subset_evaluator.score_occasion_coverage", return_value=MagicMock(score=65.0)):

            response = self.client.post(
                "/api/what-if/score",
                json={"item_ids": [101, 102, 103]},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("top_recommendation", data)
        self.assertIn("confidence", data["top_recommendation"])
        self.assertIsNotNone(data["top_recommendation"]["confidence"])
        for subset in data["subsets"]:
            self.assertIn("confidence", subset)
            self.assertIsNotNone(subset["confidence"])
            self.assertIn(subset["confidence"]["level"], ["high", "medium", "low"])

    def test_opportunity_cost_returns_confidence_both_sides(self):
        mock_owner = MagicMock(id=42, firebase_uid="test_m30_uid")

        cand = MagicMock(id=101, user_id=42, price=200.0)
        cand.attributes = MagicMock(category="jacket", color="black", style="formal")

        alt1 = MagicMock(id=201, user_id=42, price=75.0)
        alt1.attributes = MagicMock(category="top", color="white", style="casual")

        alt2 = MagicMock(id=202, user_id=42, price=90.0)
        alt2.attributes = MagicMock(category="bottom", color="blue", style="casual")

        def mock_query(model):
            q = MagicMock()
            q.filter.return_value.all.return_value = [cand, alt1, alt2]
            q.filter.return_value.first.return_value = cand
            return q

        self.mock_db.query.side_effect = mock_query

        # Mock single candidate Buy Score
        mock_cand_buy_score = BuyScoreResult(
            candidate_id=101,
            verdict="buy",
            overall_score=85.0,
            headline_reason="BUY: Solid piece",
            axes=[
                AxisScore(axis=DecisionAxis.VERSATILITY, score=85.0, reason="ok", source_agent="test", raw_evidence={"combinations_count": 3}),
                AxisScore(axis=DecisionAxis.REDUNDANCY, score=90.0, reason="ok", source_agent="test"),
                AxisScore(axis=DecisionAxis.SEASONAL_RELEVANCE, score=85.0, reason="ok", source_agent="test"),
                AxisScore(axis=DecisionAxis.BUDGET_IMPACT, score=80.0, reason="ok", source_agent="test"),
                AxisScore(axis=DecisionAxis.STYLE_ALIGNMENT, score=85.0, reason="ok", source_agent="test"),
                AxisScore(axis=DecisionAxis.OCCASION_COVERAGE, score=85.0, reason="ok", source_agent="test"),
            ],
            weights_used={"versatility": 0.1667},
            confidence=ConfidenceResult(level="high", reasoning="High confidence: decisive score."),
            created_at="2026-09-04T00:00:00Z",
        )

        mock_bundle_eval = {
            "size": 2,
            "item_ids": [201, 202],
            "overall_score": 69.5,
            "verdict": "consider",
            "headline_reason": "CONSIDER: Borderline",
            "total_price": 165.0,
            "axes": [
                {"axis": "versatility", "score": 70.0, "reason": "ok", "source_agent": "test", "raw_evidence": {"total_outfits_count": 5}},
                {"axis": "redundancy", "score": 70.0, "reason": "ok", "source_agent": "test"},
                {"axis": "seasonal_relevance", "score": 70.0, "reason": "ok", "source_agent": "test"},
                {"axis": "budget_impact", "score": 70.0, "reason": "ok", "source_agent": "test"},
                {"axis": "style_alignment", "score": 70.0, "reason": "ok", "source_agent": "test"},
                {"axis": "occasion_coverage", "score": 70.0, "reason": "ok", "source_agent": "test"},
            ],
            "confidence": {"level": "medium", "reasoning": "Medium confidence: close to threshold."},
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
        self.assertIsNotNone(data["candidate"]["confidence"])
        self.assertEqual(data["candidate"]["confidence"]["level"], "high")
        self.assertIsNotNone(data["alternative_bundle"]["confidence"])
        self.assertEqual(data["alternative_bundle"]["confidence"]["level"], "medium")


if __name__ == "__main__":
    unittest.main()
