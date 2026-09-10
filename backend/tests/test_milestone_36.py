"""
Milestone 36 Unit Tests:
Chat Interface & Tested Structural Guardrails for Stylist Chat.
Verifies that:
1. On-topic queries ("what goes with my blue jacket") retrieve wardrobe items, invoke LLM, and return grounded answers (guardrail_triggered=False).
2. Off-topic queries ("what's trending in Paris fashion week", general trivia) hit the structural similarity threshold check, short-circuit, DO NOT call the LLM (0 LLM tokens), and return the canned templated redirect (guardrail_triggered=True).
3. Empty wardrobe queries hit the structural redirect with 0 LLM calls.
4. Filtered grounding items only include items that meet the threshold.
5. POST /api/stylist/chat endpoint returns proper schema with guardrail_triggered flag.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.auth import get_current_user
from app.db import get_db
from app.models import User
from app.services.stylist_service import (
    DEFAULT_SIMILARITY_THRESHOLD_PCT,
    STYLIST_GUARDRAIL_REDIRECT_MESSAGE,
    stylist_chat,
)
from verdict_backend.main import app


class TestMilestone36StructuralGuardrails(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("app.services.stylist_service.get_chat_completion")
    @patch("app.services.stylist_service.retrieve_wardrobe_context")
    def test_on_topic_query_invokes_llm_with_grounding(
        self,
        mock_retrieve,
        mock_get_completion,
    ):
        """On-topic query ("what goes with my blue jacket") passes threshold, calls LLM, and returns grounded response."""
        mock_retrieve.return_value = [
            {
                "id": 101,
                "category": "outerwear",
                "color": "navy",
                "style": "classic",
                "pattern": "solid",
                "season": "all-season",
                "material": "wool",
                "thumbnail_url": "https://cloudinary.com/blazer.jpg",
                "similarity_score": 85.0,  # Well above 20%
                "distance": 0.15,
            },
            {
                "id": 105,
                "category": "bottom",
                "color": "grey",
                "style": "smart-casual",
                "pattern": "solid",
                "season": "all-season",
                "material": "cotton",
                "thumbnail_url": "https://cloudinary.com/pants.jpg",
                "similarity_score": 72.0,  # Well above 20%
                "distance": 0.28,
            },
        ]

        mock_completion = MagicMock()
        mock_completion.content = "Your navy blazer (Item #101) pairs cleanly with your grey chinos (Item #105)."
        mock_completion.provider_used = "gemini"
        mock_completion.model_used = "gemini-3.5-flash"
        mock_get_completion.return_value = mock_completion

        mock_db = MagicMock()
        result = stylist_chat(
            user_id=10,
            message="what goes with my blue jacket",
            db=mock_db,
        )

        # 1. Verify LLM was called
        mock_get_completion.assert_called_once()
        # 2. Verify guardrail was NOT triggered
        self.assertFalse(result["guardrail_triggered"])
        # 3. Verify reply from LLM
        self.assertEqual(result["reply"], mock_completion.content)
        # 4. Verify grounding items
        self.assertEqual(len(result["retrieved_items"]), 2)
        self.assertEqual(result["retrieved_items"][0]["id"], 101)
        self.assertEqual(result["provider_used"], "gemini")

    @patch("app.services.stylist_service.get_chat_completion")
    @patch("app.services.stylist_service.retrieve_wardrobe_context")
    def test_off_topic_query_structural_redirect_skips_llm(
        self,
        mock_retrieve,
        mock_get_completion,
    ):
        """Off-topic query ("what's trending in Paris fashion week") hits similarity threshold, skips LLM entirely (0 calls), and returns canned template."""
        # Simulated low similarity below 20% threshold
        mock_retrieve.return_value = [
            {
                "id": 201,
                "category": "top",
                "color": "black",
                "style": "casual",
                "pattern": "solid",
                "season": "summer",
                "material": "cotton",
                "thumbnail_url": "https://cloudinary.com/tshirt.jpg",
                "similarity_score": 11.5,  # Below 20%
                "distance": 0.885,
            }
        ]

        mock_db = MagicMock()
        result = stylist_chat(
            user_id=10,
            message="what's trending in Paris fashion week",
            db=mock_db,
        )

        # 1. CRITICAL: Verify LLM was NOT called at all!
        mock_get_completion.assert_not_called()
        # 2. Verify guardrail triggered
        self.assertTrue(result["guardrail_triggered"])
        # 3. Verify exact canned templated redirect message
        self.assertEqual(result["reply"], STYLIST_GUARDRAIL_REDIRECT_MESSAGE)
        self.assertIn("own wardrobe and purchase decisions", result["reply"])
        self.assertIn("don't have general fashion trend info", result["reply"])
        # 4. Verify no grounding items attached
        self.assertEqual(len(result["retrieved_items"]), 0)
        self.assertEqual(result["provider_used"], "guardrail_template")
        self.assertEqual(result["model_used"], "none")

    @patch("app.services.stylist_service.get_chat_completion")
    @patch("app.services.stylist_service.retrieve_wardrobe_context")
    def test_empty_wardrobe_hits_structural_guardrail(
        self,
        mock_retrieve,
        mock_get_completion,
    ):
        """When user has 0 items in wardrobe, query hits structural guardrail with 0 LLM calls."""
        mock_retrieve.return_value = []

        mock_db = MagicMock()
        result = stylist_chat(
            user_id=20,
            message="what shoes should I wear?",
            db=mock_db,
        )

        mock_get_completion.assert_not_called()
        self.assertTrue(result["guardrail_triggered"])
        self.assertEqual(result["reply"], STYLIST_GUARDRAIL_REDIRECT_MESSAGE)
        self.assertEqual(len(result["retrieved_items"]), 0)

    @patch("app.services.stylist_service.get_chat_completion")
    @patch("app.services.stylist_service.retrieve_wardrobe_context")
    def test_filter_below_threshold_items(
        self,
        mock_retrieve,
        mock_get_completion,
    ):
        """Only items above the threshold are kept in context; items below are pruned."""
        mock_retrieve.return_value = [
            {
                "id": 301,
                "category": "top",
                "color": "white",
                "style": "formal",
                "pattern": "solid",
                "season": "all-season",
                "material": "cotton",
                "thumbnail_url": "https://cloudinary.com/shirt.jpg",
                "similarity_score": 78.0,  # Keep
                "distance": 0.22,
            },
            {
                "id": 302,
                "category": "footwear",
                "color": "neon pink",
                "style": "athletic",
                "pattern": "striped",
                "season": "summer",
                "material": "synthetic",
                "thumbnail_url": "https://cloudinary.com/sneakers.jpg",
                "similarity_score": 14.0,  # Prune (< 20%)
                "distance": 0.86,
            },
        ]

        mock_completion = MagicMock()
        mock_completion.content = "Your white formal shirt (Item #301) is a versatile classic."
        mock_completion.provider_used = "gemini"
        mock_completion.model_used = "gemini-3.5-flash"
        mock_get_completion.return_value = mock_completion

        mock_db = MagicMock()
        result = stylist_chat(
            user_id=30,
            message="Show me my work shirts",
            db=mock_db,
        )

        self.assertFalse(result["guardrail_triggered"])
        # Only item 301 should remain
        self.assertEqual(len(result["retrieved_items"]), 1)
        self.assertEqual(result["retrieved_items"][0]["id"], 301)

        # Verify prompt only contained item 301
        prompt_called = mock_get_completion.call_args[1]["prompt"]
        self.assertIn("Item #301", prompt_called)
        self.assertNotIn("Item #302", prompt_called)

    def test_api_endpoint_with_guardrail(self):
        """POST /api/stylist/chat returns guardrail_triggered flag appropriately."""
        user_dict = {"uid": "user_m36_test", "email": "m36@example.com"}

        mock_user = MagicMock()
        mock_user.id = 60
        mock_user.firebase_uid = "user_m36_test"
        mock_user.email = "m36@example.com"

        mock_db = MagicMock()
        mock_db.query(User).filter().first.return_value = mock_user

        app.dependency_overrides[get_current_user] = lambda: user_dict
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            # 1. On-topic request
            with patch("app.routers.stylist.stylist_chat") as mock_sc:
                mock_sc.return_value = {
                    "reply": "Here is advice.",
                    "retrieved_items": [{"id": 1, "category": "top", "color": "blue", "style": "casual", "pattern": "solid", "season": "all-season", "material": "cotton", "thumbnail_url": None, "similarity_score": 80.0, "distance": 0.2}],
                    "provider_used": "gemini",
                    "model_used": "gemini-3.5-flash",
                    "guardrail_triggered": False,
                }
                resp1 = self.client.post("/api/stylist/chat", json={"message": "what goes with my blue shirt"})
                self.assertEqual(resp1.status_code, 200)
                data1 = resp1.json()
                self.assertFalse(data1["guardrail_triggered"])
                self.assertEqual(len(data1["retrieved_items"]), 1)

            # 2. Off-topic request
            with patch("app.routers.stylist.stylist_chat") as mock_sc:
                mock_sc.return_value = {
                    "reply": STYLIST_GUARDRAIL_REDIRECT_MESSAGE,
                    "retrieved_items": [],
                    "provider_used": "guardrail_template",
                    "model_used": "none",
                    "guardrail_triggered": True,
                }
                resp2 = self.client.post("/api/stylist/chat", json={"message": "what's trending in Paris fashion week"})
                self.assertEqual(resp2.status_code, 200)
                data2 = resp2.json()
                self.assertTrue(data2["guardrail_triggered"])
                self.assertEqual(data2["reply"], STYLIST_GUARDRAIL_REDIRECT_MESSAGE)
                self.assertEqual(len(data2["retrieved_items"]), 0)

        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
