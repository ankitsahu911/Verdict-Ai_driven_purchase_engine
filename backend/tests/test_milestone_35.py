"""
Milestone 35 Unit Tests:
Backend RAG Pipeline for Stylist Chat.
Tests CLIP text embedding, ChromaDB semantic retrieval scoped to user,
system prompt guardrails, LLM provider abstraction integration with Ollama fallback,
and POST /api/stylist/chat endpoint.
"""

import math
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.auth import get_current_user
from app.db import get_db
from app.models import GarmentAttributes, User, WardrobeItem
from app.services.embedding_service import (
    EmbeddingServiceError,
    generate_text_embedding,
)
from app.services.stylist_service import (
    STYLIST_SYSTEM_PROMPT,
    format_wardrobe_context,
    retrieve_wardrobe_context,
    stylist_chat,
)
from verdict_backend.main import app


class TestMilestone35StylistRAG(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("app.services.embedding_service._get_model_and_processor")
    def test_generate_text_embedding(self, mock_get_model):
        """generate_text_embedding produces normalized 512-dim vector in the shared CLIP space."""
        import torch

        mock_model = MagicMock()
        mock_processor = MagicMock()

        # Simulate torch tensor of shape (1, 512) with magnitude 2.0
        fake_tensor = torch.ones((1, 512)) * 2.0
        mock_model.get_text_features.return_value = fake_tensor
        mock_get_model.return_value = (mock_model, mock_processor)

        vec = generate_text_embedding("classic navy blazer")

        self.assertEqual(len(vec), 512)
        # Verify L2 normalization: norm should equal 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        self.assertAlmostEqual(norm, 1.0, places=4)

        # Empty text raises error
        with self.assertRaises(EmbeddingServiceError):
            generate_text_embedding("")

        with self.assertRaises(EmbeddingServiceError):
            generate_text_embedding("   ")

    def test_stylist_system_prompt_guardrails(self):
        """Verify the stylist system prompt includes strict wardrobe-only and anti-hallucination rules."""
        self.assertIn("Verdict Stylist", STYLIST_SYSTEM_PROMPT)
        self.assertIn("strictly grounded in their personal wardrobe", STYLIST_SYSTEM_PROMPT.lower())
        self.assertIn("decline", STYLIST_SYSTEM_PROMPT.lower())
        self.assertIn("only discuss", STYLIST_SYSTEM_PROMPT.lower())

    @patch("app.services.stylist_service.query_similar_items")
    @patch("app.services.stylist_service.generate_text_embedding")
    def test_retrieve_wardrobe_context(self, mock_gen_emb, mock_query_similar):
        """retrieve_wardrobe_context queries Chroma and pairs with Postgres wardrobe items and attributes."""
        mock_gen_emb.return_value = [0.1] * 512
        mock_query_similar.return_value = [
            {"id": 101, "distance": 0.2, "metadata": {"category": "outerwear"}},
            {"id": 105, "distance": 0.4, "metadata": {"category": "bottom"}},
        ]

        # Mock DB items
        item_101 = MagicMock()
        item_101.id = 101
        item_101.user_id = 42
        item_101.cloudinary_url = "https://cloudinary.com/blazer.jpg"
        attrs_101 = MagicMock()
        attrs_101.category = "outerwear"
        attrs_101.color = "navy"
        attrs_101.style = "classic"
        attrs_101.pattern = "solid"
        attrs_101.season = "all-season"
        attrs_101.material = "wool"
        item_101.attributes = attrs_101

        item_105 = MagicMock()
        item_105.id = 105
        item_105.user_id = 42
        item_105.cloudinary_url = "https://cloudinary.com/chinos.jpg"
        attrs_105 = MagicMock()
        attrs_105.category = "bottom"
        attrs_105.color = "grey"
        attrs_105.style = "smart-casual"
        attrs_105.pattern = "solid"
        attrs_105.season = "all-season"
        attrs_105.material = "cotton"
        item_105.attributes = attrs_105

        mock_db = MagicMock()
        mock_db.query().filter().all.return_value = [item_101, item_105]

        items = retrieve_wardrobe_context(user_id=42, query_text="navy jacket pairings", db=mock_db)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["id"], 101)
        self.assertEqual(items[0]["color"], "navy")
        self.assertEqual(items[0]["category"], "outerwear")
        self.assertEqual(items[0]["similarity_score"], 80.0)  # 1.0 - 0.2 = 0.8 -> 80%

        self.assertEqual(items[1]["id"], 105)
        self.assertEqual(items[1]["color"], "grey")
        self.assertEqual(items[1]["category"], "bottom")

        # Test context formatting string
        context_text = format_wardrobe_context(items)
        self.assertIn("Item #101: navy outerwear", context_text)
        self.assertIn("Item #105: grey bottom", context_text)

    @patch("app.services.stylist_service.get_chat_completion")
    @patch("app.services.stylist_service.retrieve_wardrobe_context")
    def test_stylist_chat_success(self, mock_retrieve, mock_get_completion):
        """stylist_chat formats prompt, invokes LLM abstraction, and returns reply with retrieved items."""
        mock_retrieve.return_value = [
            {
                "id": 201,
                "category": "bottom",
                "color": "beige",
                "style": "tailored",
                "pattern": "solid",
                "season": "spring",
                "material": "linen",
                "thumbnail_url": "https://cloudinary.com/pants.jpg",
                "similarity_score": 85.0,
                "distance": 0.15,
            }
        ]

        mock_completion = MagicMock()
        mock_completion.content = (
            "Based on your wardrobe, your beige tailored linen pants (Item #201) "
            "pair effortlessly with your navy blazer for a smart-casual aesthetic."
        )
        mock_completion.provider_used = "gemini"
        mock_completion.model_used = "gemini-3.5-flash"
        mock_get_completion.return_value = mock_completion

        mock_db = MagicMock()
        res = stylist_chat(
            user_id=1,
            message="what goes with my navy blazer",
            db=mock_db,
        )

        self.assertEqual(res["provider_used"], "gemini")
        self.assertEqual(res["model_used"], "gemini-3.5-flash")
        self.assertIn("beige tailored linen pants", res["reply"])
        self.assertEqual(len(res["retrieved_items"]), 1)
        self.assertEqual(res["retrieved_items"][0]["id"], 201)

        # Verify prompt passed to get_chat_completion contained the context
        prompt_called = mock_get_completion.call_args[1]["prompt"]
        self.assertIn("Item #201: beige bottom", prompt_called)
        self.assertIn("what goes with my navy blazer", prompt_called)

    @patch("app.services.llm_provider.call_ollama_chat")
    @patch("app.services.llm_provider.call_gemini_chat")
    @patch("app.services.stylist_service.retrieve_wardrobe_context")
    def test_stylist_chat_automatic_fallback(
        self,
        mock_retrieve,
        mock_call_gemini,
        mock_call_ollama,
    ):
        """When Gemini chat fails with 429 quota exhaustion, stylist chat falls back to local Ollama."""
        mock_retrieve.return_value = [
            {
                "id": 301,
                "category": "footwear",
                "color": "brown",
                "style": "classic",
                "pattern": "solid",
                "season": "all-season",
                "material": "leather",
                "thumbnail_url": "https://cloudinary.com/shoes.jpg",
                "similarity_score": 90.0,
                "distance": 0.1,
            }
        ]

        # Primary provider fails with 429
        mock_call_gemini.side_effect = RuntimeError("429 RESOURCE_EXHAUSTED: Rate limit exceeded")

        # Local Ollama succeeds
        mock_call_ollama.return_value = {
            "content": "From your wardrobe, brown leather footwear (Item #301) grounds this look nicely.",
            "model_used": "llava",
            "provider_used": "ollama_fallback",
        }

        mock_db = MagicMock()
        res = stylist_chat(
            user_id=2,
            message="Which shoes should I wear?",
            db=mock_db,
        )

        self.assertEqual(res["provider_used"], "ollama_fallback")
        self.assertEqual(res["model_used"], "llava")
        self.assertIn("Item #301", res["reply"])
        mock_call_ollama.assert_called_once()

    def test_post_stylist_chat_endpoint(self):
        """Verify protected POST /api/stylist/chat endpoint returns complete response model."""
        user_dict = {"uid": "user_stylist_m35", "email": "stylist@example.com"}

        mock_user = MagicMock()
        mock_user.id = 50
        mock_user.firebase_uid = "user_stylist_m35"
        mock_user.email = "stylist@example.com"

        mock_db = MagicMock()
        mock_db.query(User).filter().first.return_value = mock_user

        fake_chat_res = {
            "reply": "Your blue denim jacket (Item #12) pairs well with your black chinos (Item #15).",
            "retrieved_items": [
                {
                    "id": 12,
                    "category": "outerwear",
                    "color": "blue",
                    "style": "casual",
                    "pattern": "solid",
                    "season": "all-season",
                    "material": "denim",
                    "thumbnail_url": "https://cloudinary.com/jacket.jpg",
                    "similarity_score": 92.0,
                    "distance": 0.08,
                },
                {
                    "id": 15,
                    "category": "bottom",
                    "color": "black",
                    "style": "casual",
                    "pattern": "solid",
                    "season": "all-season",
                    "material": "cotton",
                    "thumbnail_url": "https://cloudinary.com/chinos.jpg",
                    "similarity_score": 88.0,
                    "distance": 0.12,
                },
            ],
            "provider_used": "gemini",
            "model_used": "gemini-3.5-flash",
        }

        app.dependency_overrides[get_current_user] = lambda: user_dict
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            with patch("app.routers.stylist.stylist_chat", return_value=fake_chat_res) as mock_sc:
                resp = self.client.post(
                    "/api/stylist/chat",
                    json={"message": "what goes with my blue jacket", "top_k": 5},
                )
                self.assertEqual(resp.status_code, 200)
                data = resp.json()

                self.assertIn("reply", data)
                self.assertIn("Item #12", data["reply"])
                self.assertEqual(len(data["retrieved_items"]), 2)
                self.assertEqual(data["retrieved_items"][0]["id"], 12)
                self.assertEqual(data["retrieved_items"][0]["color"], "blue")
                self.assertEqual(data["provider_used"], "gemini")
                self.assertEqual(data["model_used"], "gemini-3.5-flash")

                mock_sc.assert_called_once_with(
                    user_id=50,
                    message="what goes with my blue jacket",
                    db=mock_db,
                    top_k=5,
                )
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
