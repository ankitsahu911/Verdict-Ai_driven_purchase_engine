"""
Milestone 44 Copy and Wording Audit Script.

Re-reads and validates every piece of explanatory copy in Verdict:
1. Axis reason strings (Versatility, Redundancy/Uniqueness, Timing, Budget, Style Fit, Wardrobe Gap)
2. Headline template edge cases (identical axes, uniform tight cluster, SKIP leading with drawback)
3. Confidence score reasoning (no statistical jargon like std dev, plain-English point gaps)
4. Redundancy (inverted) vs Duplicate Risk % (non-inverted) framing
5. Sustainability estimate disclaimers
"""

import os
import sys
import unittest
from unittest.mock import MagicMock

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.decision_engine.schema import AxisScore, DecisionAxis
from app.decision_engine.orchestrator import build_headline_reason
from app.decision_engine.confidence import (
    calculate_confidence,
    evaluate_threshold_proximity,
    evaluate_axis_variance,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
)
from app.decision_engine.scorers.redundancy import score_redundancy
from app.decision_engine.scorers.budget_impact import score_budget_impact
from app.decision_engine.scorers.seasonal_relevance import score_seasonal_relevance
from app.decision_engine.scorers.versatility import score_versatility
from app.decision_engine.scorers.style_alignment import score_style_alignment
from app.decision_engine.scorers.occasion_coverage import score_occasion_coverage
from app.services.dashboard_service import (
    classify_sustainability_tier,
    assemble_candidate_summary_panel,
)
from app.models import WardrobeItem, GarmentAttributes


class TestMilestone44CopyAudit(unittest.TestCase):
    """Systematic copy audit test suite for Milestone 44."""

    def test_01_redundancy_reason_copy_and_inversion_clarity(self):
        """Redundancy reason strings must explain both duplicate similarity and inverted uniqueness."""
        mock_db = MagicMock()

        # Case A: completely unique item (0% duplicate)
        item_unique = WardrobeItem(id=1, duplicate_similarity_pct=0.0)
        mock_db.query.return_value.filter.return_value.first.return_value = item_unique
        res_unique = score_redundancy(1, mock_db)
        self.assertEqual(res_unique.score, 100.0)
        self.assertIn("No close match", res_unique.reason)
        self.assertIn("100/100 uniqueness", res_unique.reason)
        print(f"  [Audit Passed] Unique Redundancy Reason: {res_unique.reason}")

        # Case B: heavy duplicate item (92% duplicate)
        item_dup = WardrobeItem(id=2, duplicate_similarity_pct=92.0)
        mock_db.query.return_value.filter.return_value.first.return_value = item_dup
        res_dup = score_redundancy(2, mock_db)
        self.assertEqual(res_dup.score, 8.0)
        self.assertIn("92.0% similar to an item you already own", res_dup.reason)
        self.assertIn("8/100 uniqueness", res_dup.reason)
        self.assertIn("100 minus duplicate overlap", res_dup.reason)
        print(f"  [Audit Passed] Duplicate Redundancy Reason: {res_dup.reason}")

        # Case C: low overlap item (15% duplicate)
        item_low = WardrobeItem(id=3, duplicate_similarity_pct=15.0)
        mock_db.query.return_value.filter.return_value.first.return_value = item_low
        res_low = score_redundancy(3, mock_db)
        self.assertEqual(res_low.score, 85.0)
        self.assertIn("85/100", res_low.reason)
        self.assertIn("15.0%", res_low.reason)
        print(f"  [Audit Passed] Low Overlap Redundancy Reason: {res_low.reason}")

    def test_02_budget_impact_grammar_and_plain_english(self):
        """Budget impact must use proper articles ('an outerwear piece') and clear benchmark framing."""
        mock_db = MagicMock()

        # Vowel category: outerwear
        item_outer = WardrobeItem(id=10, price=120.0)
        item_outer.attributes = GarmentAttributes(category="outerwear")
        mock_db.query.return_value.filter.return_value.first.return_value = item_outer
        res_outer = score_budget_impact(10, mock_db)
        self.assertNotIn("for a outerwear", res_outer.reason)
        self.assertIn("for an outerwear piece", res_outer.reason)
        self.assertIn("predicted return risk", res_outer.reason)
        print(f"  [Audit Passed] Budget Reason (Outerwear): {res_outer.reason}")

        # Consonant category: top
        item_top = WardrobeItem(id=11, price=30.0)
        item_top.attributes = GarmentAttributes(category="top")
        mock_db.query.return_value.filter.return_value.first.return_value = item_top
        res_top = score_budget_impact(11, mock_db)
        self.assertIn("for a top piece", res_top.reason)
        print(f"  [Audit Passed] Budget Reason (Top): {res_top.reason}")

    def test_03_confidence_reasoning_no_statistical_jargon(self):
        """Confidence reasoning must NOT contain statistical jargon like 'std dev' and must use clear terms."""
        # High variance case (scores 25 to 85, spread = 60)
        axis_scores = [
            AxisScore(axis=DecisionAxis.VERSATILITY, score=85.0, reason="ok", source_agent="test"),
            AxisScore(axis=DecisionAxis.REDUNDANCY, score=25.0, reason="ok", source_agent="test"),
            AxisScore(axis=DecisionAxis.SEASONAL_RELEVANCE, score=80.0, reason="ok", source_agent="test"),
            AxisScore(axis=DecisionAxis.BUDGET_IMPACT, score=35.0, reason="ok", source_agent="test"),
            AxisScore(axis=DecisionAxis.STYLE_ALIGNMENT, score=80.0, reason="ok", source_agent="test"),
            AxisScore(axis=DecisionAxis.OCCASION_COVERAGE, score=60.0, reason="ok", source_agent="test"),
        ]
        conf = calculate_confidence(overall_score=69.0, axis_scores=axis_scores, style="smart-casual")
        self.assertEqual(conf.level, CONFIDENCE_LOW)

        # Confirm NO 'std dev' in reasoning string
        self.assertNotIn("std dev", conf.reasoning)
        self.assertNotIn("pts", conf.reasoning)  # uses points or -point
        self.assertIn("threshold", conf.reasoning)
        self.assertIn("disagreement", conf.reasoning)
        self.assertIn("smart-casual", conf.reasoning)
        print(f"  [Audit Passed] Low Confidence Plain-English Reasoning: {conf.reasoning}")

        # High confidence case
        decisive_axes = [
            AxisScore(axis=DecisionAxis.VERSATILITY, score=85.0, reason="ok", source_agent="test"),
            AxisScore(axis=DecisionAxis.REDUNDANCY, score=85.0, reason="ok", source_agent="test"),
            AxisScore(axis=DecisionAxis.SEASONAL_RELEVANCE, score=90.0, reason="ok", source_agent="test"),
            AxisScore(axis=DecisionAxis.BUDGET_IMPACT, score=80.0, reason="ok", source_agent="test"),
            AxisScore(axis=DecisionAxis.STYLE_ALIGNMENT, score=85.0, reason="ok", source_agent="test"),
            AxisScore(axis=DecisionAxis.OCCASION_COVERAGE, score=80.0, reason="ok", source_agent="test"),
        ]
        conf_high = calculate_confidence(overall_score=85.0, axis_scores=decisive_axes, style="casual")
        self.assertEqual(conf_high.level, CONFIDENCE_HIGH)
        self.assertIn("High confidence", conf_high.reasoning)
        self.assertIn("decisive", conf_high.reasoning)
        print(f"  [Audit Passed] High Confidence Plain-English Reasoning: {conf_high.reasoning}")

    def test_04_headline_edge_case_identical_best_and_worst_axis(self):
        """When best and worst axis are identical (or single axis), no awkward '(Though note:)' should appear."""
        axes = [
            AxisScore(
                axis=DecisionAxis.VERSATILITY,
                score=70.0,
                reason="Pairs into 3 complete outfits with items you already own.",
                source_agent="outfit_composition",
            ),
        ]
        headline = build_headline_reason("buy", axes)
        self.assertEqual(headline, "BUY: Pairs into 3 complete outfits with items you already own.")
        self.assertNotIn("Though note:", headline)
        self.assertNotIn("Caution:", headline)
        print(f"  [Audit Passed] Single / Identical Axis Headline: {headline}")

    def test_05_headline_edge_case_tight_uniform_cluster(self):
        """When all 6 axes score similarly with no clear standout, return a holistic balanced summary."""
        # Case A: Uniform BUY (all score 78-82)
        axes_buy = [
            AxisScore(axis=DecisionAxis.VERSATILITY, score=80.0, reason="v", source_agent="t"),
            AxisScore(axis=DecisionAxis.REDUNDANCY, score=82.0, reason="r", source_agent="t"),
            AxisScore(axis=DecisionAxis.SEASONAL_RELEVANCE, score=79.0, reason="s", source_agent="t"),
            AxisScore(axis=DecisionAxis.BUDGET_IMPACT, score=81.0, reason="b", source_agent="t"),
            AxisScore(axis=DecisionAxis.STYLE_ALIGNMENT, score=80.0, reason="sa", source_agent="t"),
            AxisScore(axis=DecisionAxis.OCCASION_COVERAGE, score=78.0, reason="oc", source_agent="t"),
        ]
        headline_buy = build_headline_reason("buy", axes_buy)
        self.assertIn("BUY: Well-rounded addition with consistent positive scores", headline_buy)
        print(f"  [Audit Passed] Uniform BUY Headline: {headline_buy}")

        # Case B: Uniform CONSIDER (all score 50-54)
        axes_consider = [
            AxisScore(axis=DecisionAxis.VERSATILITY, score=52.0, reason="v", source_agent="t"),
            AxisScore(axis=DecisionAxis.REDUNDANCY, score=50.0, reason="r", source_agent="t"),
            AxisScore(axis=DecisionAxis.SEASONAL_RELEVANCE, score=54.0, reason="s", source_agent="t"),
            AxisScore(axis=DecisionAxis.BUDGET_IMPACT, score=51.0, reason="b", source_agent="t"),
            AxisScore(axis=DecisionAxis.STYLE_ALIGNMENT, score=53.0, reason="sa", source_agent="t"),
            AxisScore(axis=DecisionAxis.OCCASION_COVERAGE, score=50.0, reason="oc", source_agent="t"),
        ]
        headline_consider = build_headline_reason("consider", axes_consider)
        self.assertIn("CONSIDER: Balanced profile across all criteria", headline_consider)
        print(f"  [Audit Passed] Uniform CONSIDER Headline: {headline_consider}")

        # Case C: Uniform SKIP (all score 20-25)
        axes_skip = [
            AxisScore(axis=DecisionAxis.VERSATILITY, score=22.0, reason="v", source_agent="t"),
            AxisScore(axis=DecisionAxis.REDUNDANCY, score=20.0, reason="r", source_agent="t"),
            AxisScore(axis=DecisionAxis.SEASONAL_RELEVANCE, score=24.0, reason="s", source_agent="t"),
            AxisScore(axis=DecisionAxis.BUDGET_IMPACT, score=21.0, reason="b", source_agent="t"),
            AxisScore(axis=DecisionAxis.STYLE_ALIGNMENT, score=25.0, reason="sa", source_agent="t"),
            AxisScore(axis=DecisionAxis.OCCASION_COVERAGE, score=20.0, reason="oc", source_agent="t"),
        ]
        headline_skip = build_headline_reason("skip", axes_skip)
        self.assertIn("SKIP: Consistently low utility across all evaluation criteria", headline_skip)
        print(f"  [Audit Passed] Uniform SKIP Headline: {headline_skip}")

    def test_06_headline_edge_case_skip_leads_with_primary_drawback(self):
        """When verdict is SKIP, headline must lead with the primary drawback, NOT a positive compliment."""
        axes_skip_drawback = [
            AxisScore(
                axis=DecisionAxis.VERSATILITY,
                score=70.0,
                reason="Pairs into 3 complete outfits with items you already own.",
                source_agent="outfit_composition",
            ),
            AxisScore(
                axis=DecisionAxis.REDUNDANCY,
                score=8.0,
                reason="92.0% similar to an item you already own — largely redundant (8/100 uniqueness).",
                source_agent="duplicate_detection",
            ),
            AxisScore(
                axis=DecisionAxis.BUDGET_IMPACT,
                score=35.0,
                reason="High cost-per-wear.",
                source_agent="economics_agent",
            ),
        ]
        headline = build_headline_reason("skip", axes_skip_drawback)
        # Must lead with redundancy drawback, NOT versatility compliment!
        self.assertTrue(headline.startswith("SKIP: 92.0% similar to an item you already own"))
        self.assertIn("Despite pairs into 3 complete outfits", headline)
        print(f"  [Audit Passed] SKIP Priority Drawback Headline: {headline}")

    def test_07_sustainability_tier_estimate_framing(self):
        """Sustainability tier must read clearly as a heuristic estimate, never certified."""
        tier_lower, reason_lower = classify_sustainability_tier("cotton")
        self.assertEqual(tier_lower, "Lower impact")
        self.assertIn("Rough material estimate", reason_lower)
        self.assertIn("Not a certified rating", reason_lower)

        tier_higher, reason_higher = classify_sustainability_tier("polyester")
        self.assertEqual(tier_higher, "Higher impact")
        self.assertIn("Rough material estimate", reason_higher)
        self.assertIn("Not a certified rating", reason_higher)

        tier_unrated, reason_unrated = classify_sustainability_tier(None)
        self.assertEqual(tier_unrated, "Unrated")
        self.assertIn("estimate not available", reason_unrated.lower())
        print(f"  [Audit Passed] Sustainability Disclaimers: '{reason_lower}' and '{reason_higher}'")

    def test_08_dashboard_duplicate_risk_label_plain_english(self):
        """Dashboard candidate summary duplicate risk label must explicitly reference uniqueness."""
        mock_db = MagicMock()
        item = WardrobeItem(id=50, duplicate_similarity_pct=85.0)
        item.attributes = GarmentAttributes(category="top", material="cotton", season="fall", style="casual")
        item.price = 45.0
        mock_db.query.return_value.filter.return_value.first.return_value = item

        panel = assemble_candidate_summary_panel(50, mock_db)
        self.assertEqual(panel.duplicate_risk, 85.0)
        self.assertIn("85.0%", panel.duplicate_risk_label)
        self.assertIn("High duplicate risk", panel.duplicate_risk_label)
        self.assertIn("low uniqueness on radar", panel.duplicate_risk_label)
        print(f"  [Audit Passed] Dashboard Duplicate Risk Label: {panel.duplicate_risk_label}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("RUNNING MILESTONE 44 COPY AND EXPLANATORY WORDING AUDIT")
    print("=" * 80 + "\n")
    unittest.main()
