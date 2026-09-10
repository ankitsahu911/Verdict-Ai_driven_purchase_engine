import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.auth import get_current_user
from app.db import get_db
from app.decision_engine.subset_evaluator import (
    EMPTY_SUBSET_SCORE,
    evaluate_and_rank_subsets,
    evaluate_subset,
    score_subset_redundancy,
    score_subset_versatility,
)
from app.models import ExtractionSource, GarmentAttributes, User, WardrobeItem
from verdict_backend.main import app


class TestMilestone26WhatIfScoring(unittest.TestCase):
    def setUp(self):
        self.mock_user = {
            "uid": "test_m26_uid",
            "email": "m26@example.com",
            "name": "Test M26 User",
        }
        app.dependency_overrides[get_current_user] = lambda: self.mock_user
        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_empty_subset_has_fixed_50_score(self):
        result = evaluate_subset([], self.mock_db)
        self.assertEqual(result["size"], 0)
        self.assertEqual(result["item_ids"], [])
        self.assertEqual(result["overall_score"], 50.0)
        self.assertEqual(result["verdict"], "consider")
        self.assertEqual(len(result["axes"]), 6)
        for ax in result["axes"]:
            self.assertEqual(ax["score"], 50.0)

    def test_within_subset_redundancy_penalty(self):
        cand1 = MagicMock()
        cand1.id = 101
        cand1.user_id = 42
        cand1.is_candidate = True
        cand1.duplicate_similarity_pct = 0.0
        cand1.duplicate_match_item_id = None
        cand1.attributes = MagicMock(
            category="top", color="white", pattern="solid", style="casual", season="summer", material="cotton"
        )

        cand2 = MagicMock()
        cand2.id = 102
        cand2.user_id = 42
        cand2.is_candidate = True
        cand2.duplicate_similarity_pct = 0.0
        cand2.duplicate_match_item_id = None
        cand2.attributes = MagicMock(
            category="top", color="white", pattern="solid", style="casual", season="summer", material="cotton"
        )

        def mock_query(model):
            q = MagicMock()
            q.filter.return_value.all.return_value = [cand1, cand2]
            def mock_first():
                return cand1
            q.filter.return_value.first.side_effect = lambda: cand1
            return q

        self.mock_db.query.side_effect = mock_query

        with patch("app.decision_engine.subset_evaluator.score_redundancy") as mock_indiv:
            mock_indiv.return_value = MagicMock(score=100.0)
            score_res = score_subset_redundancy([101, 102], self.mock_db)

        # Because both items are identical white casual tops, max internal similarity will be high and score penalized
        self.assertLess(score_res.score, 100.0)
        self.assertIn("Within-cart redundancy", score_res.reason)

    def test_set_versatility_synergy(self):
        cand_top = MagicMock()
        cand_top.id = 101
        cand_top.user_id = 42
        cand_top.is_candidate = True
        cand_top.cloudinary_url = "http://example.com/top.jpg"
        cand_top.attributes = MagicMock(
            category="top", color="white", pattern="solid", style="casual", season="all-season", material="cotton"
        )

        cand_bottom = MagicMock()
        cand_bottom.id = 102
        cand_bottom.user_id = 42
        cand_bottom.is_candidate = True
        cand_bottom.cloudinary_url = "http://example.com/bottom.jpg"
        cand_bottom.attributes = MagicMock(
            category="bottom", color="blue", pattern="solid", style="casual", season="all-season", material="denim"
        )

        w_shoes = MagicMock()
        w_shoes.id = 1
        w_shoes.user_id = 42
        w_shoes.is_candidate = False
        w_shoes.cloudinary_url = "http://example.com/shoes.jpg"
        w_shoes.attributes = MagicMock(
            category="footwear", color="black", pattern="solid", style="casual", season="all-season", material="leather"
        )

        def mock_query(model):
            q = MagicMock()
            def mock_filter(*args, **kwargs):
                f = MagicMock()
                # Check if querying candidate items or wardrobe items
                if args and hasattr(args[0], "left") and getattr(args[0].left, "key", None) == "id":
                    f.all.return_value = [cand_top, cand_bottom]
                else:
                    f.all.return_value = [w_shoes]
                return f
            q.filter.side_effect = mock_filter
            return q

        self.mock_db.query.side_effect = mock_query

        score_res = score_subset_versatility([101, 102], self.mock_db)
        self.assertGreater(score_res.score, 0.0)
        self.assertIn("synergy", score_res.reason.lower())

    def test_evaluate_and_rank_subsets_order(self):
        cand1 = MagicMock(id=101, user_id=42, price=50.0, is_candidate=True)
        cand1.attributes = MagicMock(category="top", color="white", pattern="solid", style="casual", season="summer", material="cotton")
        cand1.duplicate_similarity_pct = 10.0
        cand1.fit_tightness = "regular"

        cand2 = MagicMock(id=102, user_id=42, price=70.0, is_candidate=True)
        cand2.attributes = MagicMock(category="bottom", color="black", pattern="solid", style="casual", season="summer", material="denim")
        cand2.duplicate_similarity_pct = 10.0
        cand2.fit_tightness = "regular"

        cand3 = MagicMock(id=103, user_id=42, price=90.0, is_candidate=True)
        cand3.attributes = MagicMock(category="outerwear", color="khaki", pattern="solid", style="casual", season="fall", material="twill")
        cand3.duplicate_similarity_pct = 10.0
        cand3.fit_tightness = "regular"

        items_map = {101: cand1, 102: cand2, 103: cand3}

        def mock_query(model):
            q = MagicMock()
            def mock_filter(*args, **kwargs):
                f = MagicMock()
                f.all.return_value = [cand1, cand2, cand3]
                f.first.side_effect = lambda: cand1
                return f
            q.filter.side_effect = mock_filter
            return q

        self.mock_db.query.side_effect = mock_query

        with patch("app.decision_engine.subset_evaluator.score_redundancy", return_value=MagicMock(score=90.0)), \
             patch("app.decision_engine.subset_evaluator.score_seasonal_relevance", return_value=MagicMock(score=80.0)), \
             patch("app.decision_engine.subset_evaluator.score_budget_impact", return_value=MagicMock(score=75.0)), \
             patch("app.decision_engine.subset_evaluator.score_style_alignment", return_value=MagicMock(score=70.0)), \
             patch("app.decision_engine.subset_evaluator.score_occasion_coverage", return_value=MagicMock(score=65.0)):
            ranked = evaluate_and_rank_subsets([101, 102, 103], self.mock_db)

        self.assertEqual(len(ranked), 8)  # 2^3

        # Ranks must be 1 to 8
        self.assertEqual([r["rank"] for r in ranked], list(range(1, 9)))

        # Scores must be in descending order
        scores = [r["overall_score"] for r in ranked]
        for i in range(len(scores) - 1):
            self.assertGreaterEqual(scores[i], scores[i + 1])

        # Verify "skip all" (size 0) is present and has exactly score 50.0
        skip_all = next(r for r in ranked if r["size"] == 0)
        self.assertEqual(skip_all["overall_score"], 50.0)

    def test_api_what_if_score_endpoint(self):
        mock_owner = MagicMock(id=42, firebase_uid="test_m26_uid")

        items = []
        for i in [101, 102, 103, 104]:
            itm = MagicMock(id=i, user_id=42, price=60.0, is_candidate=True)
            itm.attributes = MagicMock(category="top", color="black", pattern="solid", style="casual", season="all-season", material="cotton")
            itm.duplicate_similarity_pct = 15.0
            itm.fit_tightness = "regular"
            items.append(itm)

        def mock_query(model):
            q = MagicMock()
            def mock_filter(*args, **kwargs):
                f = MagicMock()
                f.all.return_value = items
                f.first.return_value = items[0]
                return f
            q.filter.side_effect = mock_filter
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
                json={"item_ids": [101, 102, 103, 104]},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_items"], 4)
        self.assertEqual(data["total_subsets"], 16)
        self.assertIn("top_recommendation", data)
        self.assertEqual(data["top_recommendation"]["rank"], 1)
        self.assertEqual(len(data["subsets"]), 16)

        # Check that empty set is in subsets with score 50.0
        empty_subset = next(s for s in data["subsets"] if s["size"] == 0)
        self.assertEqual(empty_subset["overall_score"], 50.0)


if __name__ == "__main__":
    unittest.main()
