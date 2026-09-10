import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.auth import get_current_user
from app.db import get_db
from app.decision_engine.orchestrator import synthesize_buy_score
from app.decision_engine.schema import AxisScore, DecisionAxis
from app.decision_engine.subset_evaluator import evaluate_subset
from app.models import WardrobeItem
from app.services.dashboard_service import (
    assemble_candidate_summary_panel,
    assemble_subset_summary_panel,
    classify_sustainability_tier,
)
from verdict_backend.main import app


class TestMilestone31SummaryPanel(unittest.TestCase):
    def setUp(self):
        self.mock_user = {
            "uid": "test_m31_uid",
            "email": "m31@example.com",
            "name": "Test M31 User",
        }
        app.dependency_overrides[get_current_user] = lambda: self.mock_user
        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_sustainability_tier_heuristic_and_disclaimer(self):
        # 1. Natural fibers -> Lower impact
        tier, reason = classify_sustainability_tier("100% Cotton")
        self.assertEqual(tier, "Lower impact")
        self.assertIn("Rough", reason)
        self.assertIn("Not a certified rating", reason)

        tier_wool, reason_wool = classify_sustainability_tier("Merino Wool")
        self.assertEqual(tier_wool, "Lower impact")

        tier_linen, _ = classify_sustainability_tier("pure linen")
        self.assertEqual(tier_linen, "Lower impact")

        # 2. Synthetics -> Higher impact
        tier_poly, reason_poly = classify_sustainability_tier("Polyester blend")
        self.assertEqual(tier_poly, "Higher impact")
        self.assertIn("Rough", reason_poly)

        tier_nylon, _ = classify_sustainability_tier("100% nylon")
        self.assertEqual(tier_nylon, "Higher impact")

        # 3. Unknown -> Unrated
        tier_unk, _ = classify_sustainability_tier("Space-age alloy")
        self.assertEqual(tier_unk, "Unrated")

        tier_none, _ = classify_sustainability_tier(None)
        self.assertEqual(tier_none, "Unrated")

    def test_duplicate_risk_polarity_non_inverted(self):
        # Test candidate with duplicate_similarity_pct = 78.5%
        cand = MagicMock(spec=WardrobeItem)
        cand.id = 101
        cand.user_id = 42
        cand.price = 50.0
        cand.duplicate_similarity_pct = 78.5
        cand.attributes = MagicMock(category="top", material="cotton", season="summer")

        self.mock_db.query.return_value.filter.return_value.first.return_value = cand

        vers_axis = AxisScore(
            axis=DecisionAxis.VERSATILITY,
            score=80.0,
            reason="ok",
            source_agent="outfit_composition",
            raw_evidence={"combinations_count": 4},
        )
        season_axis = AxisScore(
            axis=DecisionAxis.SEASONAL_RELEVANCE,
            score=90.0,
            reason="ok",
            source_agent="vision_agent",
        )

        panel = assemble_candidate_summary_panel(
            candidate_item_id=101,
            db=self.mock_db,
            versatility_axis=vers_axis,
            seasonality_axis=season_axis,
        )

        # MUST BE 78.5 (original similarity percentage), NOT inverted 21.5!
        self.assertEqual(panel.duplicate_risk, 78.5)
        self.assertIn("78.5%", panel.duplicate_risk_label)
        self.assertIn("High duplicate risk", panel.duplicate_risk_label)

        # Check versatility and outfits count
        self.assertEqual(panel.versatility, 80.0)
        self.assertEqual(panel.versatility_outfits_count, 4)

        # Check seasonality
        self.assertEqual(panel.seasonality, 90.0)

        # Check sustainability
        self.assertEqual(panel.sustainability_tier, "Lower impact")
        self.assertTrue(panel.is_estimate)

    def test_subset_summary_panel_aggregation(self):
        item1 = MagicMock(id=1, user_id=42, price=60.0, duplicate_similarity_pct=20.0)
        item1.attributes = MagicMock(category="top", material="cotton", season="fall")

        item2 = MagicMock(id=2, user_id=42, price=80.0, duplicate_similarity_pct=65.0)
        item2.attributes = MagicMock(category="bottom", material="polyester", season="fall")

        self.mock_db.query.return_value.filter.return_value.all.return_value = [item1, item2]

        axes = [
            {"axis": "versatility", "score": 85.0, "raw_evidence": {"total_outfits_count": 6}},
            {"axis": "seasonal_relevance", "score": 75.0},
        ]

        subset_panel = assemble_subset_summary_panel([1, 2], self.mock_db, axes)

        self.assertEqual(subset_panel.versatility, 85.0)
        self.assertEqual(subset_panel.versatility_outfits_count, 6)
        # Duplicate risk must be peak similarity = 65.0
        self.assertEqual(subset_panel.duplicate_risk, 65.0)
        self.assertEqual(subset_panel.seasonality, 75.0)
        # Sustainability tier: includes polyester -> Higher impact
        self.assertEqual(subset_panel.sustainability_tier, "Higher impact")
        self.assertTrue(subset_panel.is_estimate)

    def test_synthesize_buy_score_includes_summary_panel(self):
        mock_cand = MagicMock(spec=WardrobeItem)
        mock_cand.id = 101
        mock_cand.user_id = 42
        mock_cand.price = 95.0
        mock_cand.duplicate_similarity_pct = 15.0
        mock_cand.attributes = MagicMock(category="outerwear", material="linen", style="casual")
        self.mock_db.query.return_value.filter.return_value.first.return_value = mock_cand

        with patch("app.decision_engine.orchestrator.score_versatility", return_value=AxisScore(axis=DecisionAxis.VERSATILITY, score=70.0, reason="ok", source_agent="test", raw_evidence={"combinations_count": 3})), \
             patch("app.decision_engine.orchestrator.score_redundancy", return_value=AxisScore(axis=DecisionAxis.REDUNDANCY, score=85.0, reason="ok", source_agent="test")), \
             patch("app.decision_engine.orchestrator.score_seasonal_relevance", return_value=AxisScore(axis=DecisionAxis.SEASONAL_RELEVANCE, score=90.0, reason="ok", source_agent="test")), \
             patch("app.decision_engine.orchestrator.score_budget_impact", return_value=AxisScore(axis=DecisionAxis.BUDGET_IMPACT, score=60.0, reason="ok", source_agent="test")), \
             patch("app.decision_engine.orchestrator.score_style_alignment", return_value=AxisScore(axis=DecisionAxis.STYLE_ALIGNMENT, score=70.0, reason="ok", source_agent="test")), \
             patch("app.decision_engine.orchestrator.score_occasion_coverage", return_value=AxisScore(axis=DecisionAxis.OCCASION_COVERAGE, score=70.0, reason="ok", source_agent="test")):

            result = synthesize_buy_score(101, self.mock_db, persist=False)

        self.assertIsNotNone(result.summary_panel)
        panel = result.summary_panel
        self.assertEqual(panel["duplicate_risk"], 15.0)
        self.assertEqual(panel["sustainability_tier"], "Lower impact")
        self.assertEqual(panel["versatility"], 70.0)
        self.assertEqual(panel["seasonality"], 90.0)
        self.assertIn("$", panel["cost_per_wear_formatted"])


if __name__ == "__main__":
    unittest.main()
