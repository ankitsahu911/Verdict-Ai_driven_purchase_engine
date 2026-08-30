"""
Unit Tests for Milestone 19: Decision Axes Shared Contract & Schema.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pydantic import ValidationError

from app.decision_engine import (
    AxisScore,
    AxisScorer,
    CandidateDecisionPayload,
    DecisionAxis,
)


class DummyScorer:
    """Mock scorer class implementing AxisScorer protocol."""

    def score(self, candidate_item_id: int, db: any) -> AxisScore:
        return AxisScore(
            axis=DecisionAxis.VERSATILITY,
            score=85.0,
            reason="Pairs with 4 items in your wardrobe.",
            source_agent="OutfitCompositionAgent",
            raw_evidence={"compatible_count": 4},
        )


class TestMilestone19DecisionEngineSchema(unittest.TestCase):
    def test_decision_axis_enum(self):
        """Test all 6 decision axes are enumerated."""
        axes = [a.value for a in DecisionAxis]
        expected = [
            "versatility",
            "redundancy",
            "seasonal_relevance",
            "budget_impact",
            "style_alignment",
            "occasion_coverage",
        ]
        self.assertEqual(sorted(axes), sorted(expected))

    def test_axis_score_instantiation_and_bounds(self):
        """Test AxisScore model validation and 0-100 score bounds."""
        score_obj = AxisScore(
            axis=DecisionAxis.REDUNDANCY,
            score=93.2,
            reason="Only 6.8% similar to existing wardrobe pieces (very unique).",
            source_agent="DuplicateDetectionAgent",
            raw_evidence={"nearest_similarity_pct": 6.8},
        )

        self.assertEqual(score_obj.axis, DecisionAxis.REDUNDANCY)
        self.assertEqual(score_obj.score, 93.2)
        self.assertEqual(score_obj.source_agent, "DuplicateDetectionAgent")
        self.assertIsNotNone(score_obj.raw_evidence)

        # Test score > 100 raises ValidationError
        with self.assertRaises(ValidationError):
            AxisScore(
                axis=DecisionAxis.BUDGET_IMPACT,
                score=150.0,
                reason="Invalid score",
                source_agent="TestAgent",
            )

        # Test score < 0 raises ValidationError
        with self.assertRaises(ValidationError):
            AxisScore(
                axis=DecisionAxis.BUDGET_IMPACT,
                score=-5.0,
                reason="Invalid score",
                source_agent="TestAgent",
            )

    def test_axis_scorer_protocol_conformance(self):
        """Test mock class satisfies AxisScorer Protocol interface."""
        scorer = DummyScorer()
        self.assertTrue(isinstance(scorer, AxisScorer))

        res = scorer.score(10, None)
        self.assertIsInstance(res, AxisScore)
        self.assertEqual(res.axis, DecisionAxis.VERSATILITY)
        self.assertEqual(res.score, 85.0)

    def test_candidate_decision_payload_serialization(self):
        """Test CandidateDecisionPayload aggregation and JSON round-trip."""
        payload = CandidateDecisionPayload(
            candidate_id=42,
            scores={
                DecisionAxis.VERSATILITY: AxisScore(
                    axis=DecisionAxis.VERSATILITY,
                    score=80.0,
                    reason="Highly versatile pairing.",
                    source_agent="OutfitAgent",
                ),
                DecisionAxis.REDUNDANCY: AxisScore(
                    axis=DecisionAxis.REDUNDANCY,
                    score=95.0,
                    reason="Unique piece.",
                    source_agent="DuplicateAgent",
                ),
            },
            overall_score=87.5,
        )

        json_str = payload.model_dump_json()
        deserialized = CandidateDecisionPayload.model_validate_json(json_str)

        self.assertEqual(deserialized.candidate_id, 42)
        self.assertEqual(deserialized.overall_score, 87.5)
        self.assertIn(DecisionAxis.VERSATILITY, deserialized.scores)
        self.assertEqual(deserialized.scores[DecisionAxis.VERSATILITY].score, 80.0)


if __name__ == "__main__":
    unittest.main()
