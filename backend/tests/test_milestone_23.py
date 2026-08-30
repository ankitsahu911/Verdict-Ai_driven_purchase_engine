"""
Unit and Integration Tests for Milestone 23: Deterministic Buy Score Orchestrator.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.decision_engine.orchestrator import (
    BUY_THRESHOLD,
    CONSIDER_THRESHOLD,
    build_headline_reason,
    map_score_to_verdict,
    synthesize_buy_score,
)
from app.decision_engine.schema import AxisScore, BuyScoreResult, DecisionAxis
from app.models import Decision, DecisionLog, GarmentAttributes, User, WardrobeItem


class TestMilestone23BuyScoreOrchestrator(unittest.TestCase):
    def test_verdict_threshold_mapping(self):
        """Test fixed documented threshold mapping for buy, consider, and skip."""
        self.assertEqual(map_score_to_verdict(85.0), "buy")
        self.assertEqual(map_score_to_verdict(BUY_THRESHOLD), "buy")
        self.assertEqual(map_score_to_verdict(69.9), "consider")
        self.assertEqual(map_score_to_verdict(CONSIDER_THRESHOLD), "consider")
        self.assertEqual(map_score_to_verdict(44.9), "skip")
        self.assertEqual(map_score_to_verdict(15.0), "skip")

    def test_headline_reason_templating(self):
        """Test deterministic headline reasoning combining best and worst axis explanations."""
        axes = [
            AxisScore(
                axis=DecisionAxis.VERSATILITY,
                score=80.0,
                reason="Pairs into 4 complete outfits with items you already own.",
                source_agent="outfit_composition",
            ),
            AxisScore(
                axis=DecisionAxis.REDUNDANCY,
                score=95.0,
                reason="No close match in your current wardrobe.",
                source_agent="duplicate_detection",
            ),
            AxisScore(
                axis=DecisionAxis.BUDGET_IMPACT,
                score=30.0,
                reason="High cost-per-wear ($8.00/wear vs $3.50 ceiling).",
                source_agent="economics_agent",
            ),
        ]

        headline = build_headline_reason("buy", axes)
        # Should lead with best axis (redundancy: 95.0) and include worst axis caveat (budget_impact: 30.0 < 40)
        self.assertTrue(headline.startswith("BUY: No close match in your current wardrobe."))
        self.assertIn("Though note: High cost-per-wear", headline)

    @patch("app.decision_engine.orchestrator.score_occasion_coverage")
    @patch("app.decision_engine.orchestrator.score_style_alignment")
    @patch("app.decision_engine.orchestrator.score_budget_impact")
    @patch("app.decision_engine.orchestrator.score_seasonal_relevance")
    @patch("app.decision_engine.orchestrator.score_redundancy")
    @patch("app.decision_engine.orchestrator.score_versatility")
    def test_determinism_proof_synthesize_buy_score(
        self,
        mock_v,
        mock_r,
        mock_s,
        mock_b,
        mock_sa,
        mock_oc,
    ):
        """Prove that calling synthesize_buy_score multiple times on identical inputs returns byte-identical output."""
        mock_v.return_value = AxisScore(
            axis=DecisionAxis.VERSATILITY,
            score=80.0,
            reason="Pairs into 4 outfits.",
            source_agent="outfit_composition",
        )
        mock_r.return_value = AxisScore(
            axis=DecisionAxis.REDUNDANCY,
            score=90.0,
            reason="Unique item.",
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
            score=85.0,
            reason="Affordable CPW.",
            source_agent="economics_agent",
        )
        mock_sa.return_value = AxisScore(
            axis=DecisionAxis.STYLE_ALIGNMENT,
            score=60.0,
            reason="Fits personal style.",
            source_agent="style_analysis",
        )
        mock_oc.return_value = AxisScore(
            axis=DecisionAxis.OCCASION_COVERAGE,
            score=45.0,
            reason="Moderate coverage.",
            source_agent="occasion_analysis",
        )

        mock_db = MagicMock()
        candidate = WardrobeItem(id=77, user_id=1, is_candidate=True)
        mock_db.query.return_value.filter.return_value.first.return_value = candidate

        # Run 1:
        res_1 = synthesize_buy_score(77, mock_db, persist=False)

        # Run 2:
        res_2 = synthesize_buy_score(77, mock_db, persist=False)

        # Expected overall: (80 + 90 + 100 + 85 + 60 + 45) / 6 = 460 / 6 = 76.7
        self.assertEqual(res_1.overall_score, 76.7)
        self.assertEqual(res_1.verdict, "buy")

        # Determinism Assertion: Exact match between run 1 and run 2
        self.assertEqual(res_1.overall_score, res_2.overall_score)
        self.assertEqual(res_1.verdict, res_2.verdict)
        self.assertEqual(res_1.headline_reason, res_2.headline_reason)
        self.assertEqual(len(res_1.axes), len(res_2.axes))
        for a1, a2 in zip(res_1.axes, res_2.axes):
            self.assertEqual(a1.axis, a2.axis)
            self.assertEqual(a1.score, a2.score)
            self.assertEqual(a1.reason, a2.reason)

    @patch("app.decision_engine.orchestrator.score_occasion_coverage")
    @patch("app.decision_engine.orchestrator.score_style_alignment")
    @patch("app.decision_engine.orchestrator.score_budget_impact")
    @patch("app.decision_engine.orchestrator.score_seasonal_relevance")
    @patch("app.decision_engine.orchestrator.score_redundancy")
    @patch("app.decision_engine.orchestrator.score_versatility")
    def test_decision_log_persistence(
        self,
        mock_v,
        mock_r,
        mock_s,
        mock_b,
        mock_sa,
        mock_oc,
    ):
        """Test that synthesize_buy_score writes a row to decision_logs table."""
        mock_v.return_value = AxisScore(axis=DecisionAxis.VERSATILITY, score=30.0, reason="Low", source_agent="v")
        mock_r.return_value = AxisScore(axis=DecisionAxis.REDUNDANCY, score=30.0, reason="Low", source_agent="r")
        mock_s.return_value = AxisScore(axis=DecisionAxis.SEASONAL_RELEVANCE, score=30.0, reason="Low", source_agent="s")
        mock_b.return_value = AxisScore(axis=DecisionAxis.BUDGET_IMPACT, score=30.0, reason="Low", source_agent="b")
        mock_sa.return_value = AxisScore(axis=DecisionAxis.STYLE_ALIGNMENT, score=30.0, reason="Low", source_agent="sa")
        mock_oc.return_value = AxisScore(axis=DecisionAxis.OCCASION_COVERAGE, score=30.0, reason="Low", source_agent="oc")

        mock_db = MagicMock()
        candidate = WardrobeItem(id=88, user_id=9, is_candidate=True)
        mock_db.query.return_value.filter.return_value.first.return_value = candidate

        res = synthesize_buy_score(88, mock_db, persist=True)

        self.assertEqual(res.overall_score, 30.0)
        self.assertEqual(res.verdict, "skip")

        # Verify db.add called with DecisionLog
        added_objs = [call[0][0] for call in mock_db.add.call_args_list]
        log_entry = next((o for o in added_objs if isinstance(o, DecisionLog)), None)
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.user_id, 9)
        self.assertEqual(log_entry.wardrobe_item_id, 88)
        self.assertEqual(log_entry.decision, Decision.SKIP)
        self.assertEqual(log_entry.buy_score, 30.0)
        self.assertIn("axes", log_entry.raw_payload)

    @patch("app.routers.candidates.synthesize_buy_score")
    def test_get_candidate_buy_score_endpoint(self, mock_synthesize):
        """Test GET /api/candidates/{id}/buy-score endpoint."""
        mock_synthesize.return_value = BuyScoreResult(
            candidate_id=99,
            verdict="buy",
            overall_score=82.5,
            headline_reason="BUY: High versatility and unique item.",
            axes=[
                AxisScore(axis=DecisionAxis.VERSATILITY, score=80.0, reason="r", source_agent="a"),
                AxisScore(axis=DecisionAxis.REDUNDANCY, score=85.0, reason="r", source_agent="a"),
            ],
            weights_used={"versatility": 0.1667, "redundancy": 0.1667},
            decision_log_id=123,
            created_at="2026-08-29T11:15:00Z",
        )

        mock_owner = User(id=1, firebase_uid="uid123", email="user@test.com")
        candidate = WardrobeItem(id=99, user_id=1, is_candidate=True)

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
        from app.routers.candidates import get_candidate_buy_score

        res = asyncio.run(
            get_candidate_buy_score(
                candidate_id=99,
                user=mock_user,
                db=mock_db,
            )
        )

        self.assertEqual(res["candidate_id"], 99)
        self.assertEqual(res["verdict"], "buy")
        self.assertEqual(res["overall_score"], 82.5)
        self.assertEqual(res["decision_log_id"], 123)
        self.assertIn("BUY:", res["headline_reason"])


if __name__ == "__main__":
    unittest.main()
