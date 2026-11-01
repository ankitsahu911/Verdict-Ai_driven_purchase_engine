import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.decision_engine.orchestrator import synthesize_buy_score
from app.decision_engine.schema import AxisScore, DecisionAxis
from app.models import WardrobeItem
from app.services.duplicate_matching import attribute_duplicate_score, color_family


class TestDuplicateGuardrails(unittest.TestCase):
    def test_same_colour_footwear_sets_a_high_duplicate_floor(self):
        score, reason = attribute_duplicate_score(
            {"category": "shoes", "color": "navy blue", "style": "casual"},
            {"category": "sneakers", "color": "blue", "style": "casual"},
        )
        self.assertGreaterEqual(score, 85.0)
        self.assertIn("same blue footwear", reason)
        self.assertEqual(color_family("navy blue"), "blue")

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
