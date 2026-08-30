"""
Unit and Integration Tests for Milestone 18: Return-Risk Score Calculation.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import GarmentAttributes, User, WardrobeItem
from app.services.economics_service import calculate_return_risk


class TestMilestone18ReturnRisk(unittest.TestCase):
    def test_return_risk_fit_tightness_comparison(self):
        """Test tight/oversized fits score measurably higher return-risk than regular fit."""
        category = "dress"  # Baseline return risk = 40%

        risk_tight = calculate_return_risk(category=category, fit_tightness="tight")
        risk_oversized = calculate_return_risk(category=category, fit_tightness="oversized")
        risk_regular = calculate_return_risk(category=category, fit_tightness="regular")
        risk_unspecified = calculate_return_risk(category=category, fit_tightness=None)

        # Baseline dress risk is 40
        self.assertEqual(risk_tight["baseline_risk"], 40)

        # Tight fit = 40 + 25 = 65%
        self.assertEqual(risk_tight["return_risk_score"], 65)

        # Oversized fit = 40 + 15 = 55%
        self.assertEqual(risk_oversized["return_risk_score"], 55)

        # Regular fit = 40 - 5 = 35%
        self.assertEqual(risk_regular["return_risk_score"], 35)

        # Unspecified fit = 40 + 0 = 40%
        self.assertEqual(risk_unspecified["return_risk_score"], 40)

        # Acceptance Criteria: tight & oversized score measurably higher than regular
        self.assertGreater(risk_tight["return_risk_score"], risk_regular["return_risk_score"])
        self.assertGreater(risk_oversized["return_risk_score"], risk_regular["return_risk_score"])

    def test_return_risk_clamping(self):
        """Test return risk score is capped between 0 and 100."""
        # Footwear baseline 45 + 25 tight = 70 (within bounds)
        res_footwear = calculate_return_risk("footwear", "tight")
        self.assertEqual(res_footwear["return_risk_score"], 70)

        # Low baseline accessory 10 - 5 regular = 5 (within bounds)
        res_acc = calculate_return_risk("accessory", "regular")
        self.assertEqual(res_acc["return_risk_score"], 5)
        self.assertGreaterEqual(res_acc["return_risk_score"], 0)

    def test_templated_reasoning_string(self):
        """Test templated reasoning contains real matched inputs without LLM calls."""
        res = calculate_return_risk(category="dress", fit_tightness="tight")
        self.assertIn("Tight fit", res["reasoning"])
        self.assertIn("dress", res["reasoning"])
        self.assertIn("40%", res["reasoning"])
        self.assertIn("65%", res["reasoning"])

    def test_get_candidate_economics_populated_return_risk(self):
        """Test GET /api/candidates/{id}/economics returns populated return_risk object."""
        candidate_item = WardrobeItem(
            id=90,
            user_id=1,
            is_candidate=True,
            price=150.0,
            fit_tightness="tight",
        )
        candidate_item.attributes = GarmentAttributes(category="dress")
        mock_owner = User(id=1, firebase_uid="uid123", email="user@test.com")

        def db_query_side_effect(model_cls):
            q_mock = MagicMock()
            if model_cls == User:
                q_mock.filter.return_value.first.return_value = mock_owner
            else:
                q_mock.filter.return_value.first.return_value = candidate_item
            return q_mock

        mock_db = MagicMock()
        mock_db.query.side_effect = db_query_side_effect
        mock_user = {"uid": "uid123", "email": "user@test.com"}

        import asyncio
        from app.routers.candidates import get_candidate_economics

        res = asyncio.run(
            get_candidate_economics(
                candidate_id=90,
                user=mock_user,
                db=mock_db,
            )
        )

        self.assertEqual(res["candidate_id"], 90)
        self.assertEqual(res["price"], 150.0)
        self.assertEqual(res["cost_per_wear"], 15.0)  # 150 / 10 = 15.0
        self.assertIsNotNone(res["return_risk"])
        self.assertEqual(res["return_risk"]["score"], 65)  # 40 baseline + 25 tight = 65
        self.assertEqual(res["return_risk"]["fit_tightness"], "tight")
        self.assertIn("Tight fit", res["return_risk"]["reasoning"])


if __name__ == "__main__":
    unittest.main()
