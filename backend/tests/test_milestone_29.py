import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.decision_engine.confidence import (
    AMBIGUOUS_STYLES,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    calculate_confidence,
    evaluate_axis_variance,
    evaluate_category_ambiguity,
    evaluate_threshold_proximity,
)
from app.decision_engine.orchestrator import synthesize_buy_score
from app.decision_engine.schema import AxisScore, DecisionAxis
from app.models import WardrobeItem


class TestMilestone29Confidence(unittest.TestCase):
    def test_high_confidence_decisive_item(self):
        # Plain white t-shirt: decisive score (88.0), tight consensus (84-90), unambiguous style ("casual")
        overall_score = 88.0
        axis_scores = [
            AxisScore(axis=DecisionAxis.VERSATILITY, score=85.0, reason="ok", source_agent="test"),
            AxisScore(axis=DecisionAxis.REDUNDANCY, score=90.0, reason="ok", source_agent="test"),
            AxisScore(axis=DecisionAxis.SEASONAL_RELEVANCE, score=88.0, reason="ok", source_agent="test"),
            AxisScore(axis=DecisionAxis.BUDGET_IMPACT, score=86.0, reason="ok", source_agent="test"),
            AxisScore(axis=DecisionAxis.STYLE_ALIGNMENT, score=84.0, reason="ok", source_agent="test"),
            AxisScore(axis=DecisionAxis.OCCASION_COVERAGE, score=87.0, reason="ok", source_agent="test"),
        ]
        style = "casual"

        conf = calculate_confidence(overall_score, axis_scores, style)

        self.assertEqual(conf.level, CONFIDENCE_HIGH)
        self.assertEqual(conf.signals["total_penalty"], 0)
        self.assertIn("High confidence", conf.reasoning)
        self.assertIn("decisive", conf.reasoning)

    def test_low_confidence_boundary_blazer(self):
        # Borderline smart-casual blazer:
        # 1. overall_score sits at 69.0 (1.0 pt from Buy threshold 70.0) -> proximity penalty = 2
        # 2. axis spread from 25.0 to 85.0 (spread = 60.0 >= 45.0) -> variance penalty = 2
        # 3. style = "smart-casual" (in ambiguous list) -> category penalty = 1
        # Total penalty = 5 >= 3 -> low confidence
        overall_score = 69.0
        axis_scores = [
            AxisScore(axis=DecisionAxis.VERSATILITY, score=85.0, reason="ok", source_agent="test"),
            AxisScore(axis=DecisionAxis.REDUNDANCY, score=25.0, reason="ok", source_agent="test"),
            AxisScore(axis=DecisionAxis.SEASONAL_RELEVANCE, score=80.0, reason="ok", source_agent="test"),
            AxisScore(axis=DecisionAxis.BUDGET_IMPACT, score=35.0, reason="ok", source_agent="test"),
            AxisScore(axis=DecisionAxis.STYLE_ALIGNMENT, score=80.0, reason="ok", source_agent="test"),
            AxisScore(axis=DecisionAxis.OCCASION_COVERAGE, score=60.0, reason="ok", source_agent="test"),
        ]
        style = "smart-casual"

        conf = calculate_confidence(overall_score, axis_scores, style)

        self.assertEqual(conf.level, CONFIDENCE_LOW)
        self.assertGreaterEqual(conf.signals["total_penalty"], 3)
        self.assertIn("Low confidence", conf.reasoning)
        self.assertIn("threshold", conf.reasoning)
        self.assertIn("disagreement", conf.reasoning)
        self.assertIn("smart-casual", conf.reasoning)

    def test_medium_confidence_single_signal_trigger(self):
        # Score is close to Buy threshold (71.5), but axes agree (spread 10) and category is clear ("athletic")
        overall_score = 71.5
        axis_scores = [70.0, 72.0, 73.0, 71.0, 70.0, 73.0]
        style = "formal"

        conf = calculate_confidence(overall_score, axis_scores, style)

        self.assertEqual(conf.level, CONFIDENCE_MEDIUM)
        self.assertEqual(conf.signals["proximity"]["nearest_threshold"], "Buy")
        self.assertIn("Medium confidence", conf.reasoning)

    def test_acceptance_criteria_rule_comparison(self):
        # White t-shirt vs. smart-casual blazer comparison
        tshirt_conf = calculate_confidence(
            overall_score=85.0,
            axis_scores=[80.0, 85.0, 82.0, 88.0, 86.0, 84.0],
            style="casual",
        )
        blazer_conf = calculate_confidence(
            overall_score=68.5,
            axis_scores=[30.0, 85.0, 80.0, 35.0, 80.0, 55.0],
            style="smart-casual",
        )

        self.assertEqual(tshirt_conf.level, CONFIDENCE_HIGH)
        self.assertEqual(blazer_conf.level, CONFIDENCE_LOW)
        self.assertLess(tshirt_conf.signals["total_penalty"], blazer_conf.signals["total_penalty"])

    def test_synthesize_buy_score_wires_confidence(self):
        mock_db = MagicMock()
        mock_cand = MagicMock(spec=WardrobeItem)
        mock_cand.id = 101
        mock_cand.user_id = 42
        mock_cand.attributes = MagicMock(style="smart-casual")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_cand

        with patch("app.decision_engine.orchestrator.score_versatility", return_value=AxisScore(axis=DecisionAxis.VERSATILITY, score=80.0, reason="ok", source_agent="test")), \
             patch("app.decision_engine.orchestrator.score_redundancy", return_value=AxisScore(axis=DecisionAxis.REDUNDANCY, score=75.0, reason="ok", source_agent="test")), \
             patch("app.decision_engine.orchestrator.score_seasonal_relevance", return_value=AxisScore(axis=DecisionAxis.SEASONAL_RELEVANCE, score=70.0, reason="ok", source_agent="test")), \
             patch("app.decision_engine.orchestrator.score_budget_impact", return_value=AxisScore(axis=DecisionAxis.BUDGET_IMPACT, score=65.0, reason="ok", source_agent="test")), \
             patch("app.decision_engine.orchestrator.score_style_alignment", return_value=AxisScore(axis=DecisionAxis.STYLE_ALIGNMENT, score=70.0, reason="ok", source_agent="test")), \
             patch("app.decision_engine.orchestrator.score_occasion_coverage", return_value=AxisScore(axis=DecisionAxis.OCCASION_COVERAGE, score=70.0, reason="ok", source_agent="test")):

            result = synthesize_buy_score(101, mock_db, persist=False)

        self.assertIsNotNone(result.confidence)
        self.assertIn(result.confidence.level, [CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW])
        self.assertIsInstance(result.confidence.reasoning, str)
        self.assertGreater(len(result.confidence.reasoning), 10)


if __name__ == "__main__":
    unittest.main()
