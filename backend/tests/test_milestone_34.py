"""
Milestone 34 Unit Tests:
LLM Provider Abstraction Layer with Automatic Fallback to Local Ollama.
Tests primary cloud completion (Gemini), quota/429 fallback, timeout fallback,
network error fallback, invalid/missing API key fallback, JSON extractor resilience,
fit analysis fallback, and candidate intake end-to-end survival during cloud outages.
"""

import asyncio
import base64
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import User
from app.services.llm_provider import (
    call_gemini_vision,
    call_ollama_vision,
    extract_json_from_text,
    fetch_image_base64,
    get_vision_completion,
)
from app.services.vision_service import (
    VisionServiceError,
    analyze_fit,
    analyze_image,
)


class TestMilestone34LLMProviderFallback(unittest.TestCase):

    def test_extract_json_from_text_variants(self):
        """Verify robust JSON extraction from direct JSON, markdown code blocks, and prose."""
        # 1. Direct JSON
        raw1 = '{"category": "top", "color": "blue"}'
        self.assertEqual(extract_json_from_text(raw1), {"category": "top", "color": "blue"})

        # 2. Markdown fenced block with json
        raw2 = "Here is the response:\n```json\n{\"category\": \"bottom\", \"color\": \"black\"}\n```\nHope that helps!"
        self.assertEqual(extract_json_from_text(raw2), {"category": "bottom", "color": "black"})

        # 3. Markdown fenced block without language tag
        raw3 = "```\n{\"category\": \"dress\", \"color\": \"red\"}\n```"
        self.assertEqual(extract_json_from_text(raw3), {"category": "dress", "color": "red"})

        # 4. Embedded between prose
        raw4 = "The item looks like: {\"category\": \"outerwear\", \"color\": \"grey\"} as shown."
        self.assertEqual(extract_json_from_text(raw4), {"category": "outerwear", "color": "grey"})

        # 5. Invalid text raises ValueError
        with self.assertRaises(ValueError):
            extract_json_from_text("This is plain text with no json structure at all.")

    def test_fetch_image_base64_data_uri(self):
        """Data URIs are cleanly stripped and returned as base64 string."""
        sample_b64 = base64.b64encode(b"fake_image_bytes").decode("utf-8")
        data_uri = f"data:image/png;base64,{sample_b64}"
        self.assertEqual(fetch_image_base64(data_uri), sample_b64)

    @patch("requests.get")
    def test_fetch_image_base64_http_url(self, mock_get):
        """HTTP URLs are fetched and encoded as base64."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"cloud_image_bytes"
        mock_get.return_value = mock_resp

        result = fetch_image_base64("https://cloudinary.com/jacket.jpg")
        expected = base64.b64encode(b"cloud_image_bytes").decode("utf-8")
        self.assertEqual(result, expected)

    @patch("app.services.llm_provider.call_gemini_vision")
    def test_primary_provider_success(self, mock_call_gemini):
        """When Gemini succeeds, provider_used is 'gemini' and no fallback is triggered."""
        mock_call_gemini.return_value = {
            "data": {
                "category": "top",
                "color": "navy",
                "pattern": "striped",
                "style": "casual",
                "season": "summer",
                "material": "linen",
            },
            "raw_text": '{"category": "top"}',
            "model_used": "gemini-3.5-flash",
            "provider_used": "gemini",
        }

        result = get_vision_completion(
            prompt="Analyze garment",
            image_url="https://example.com/shirt.jpg",
        )

        self.assertEqual(result.provider_used, "gemini")
        self.assertEqual(result.model_used, "gemini-3.5-flash")
        self.assertIsNone(result.error_reason)
        self.assertEqual(result.data["category"], "top")
        self.assertEqual(result.data["color"], "navy")

    @patch("app.services.llm_provider.call_ollama_vision")
    @patch("app.services.llm_provider.call_gemini_vision")
    def test_fallback_on_quota_exhausted_429(self, mock_call_gemini, mock_call_ollama):
        """When Gemini raises 429 / RESOURCE_EXHAUSTED, automatically falls back to Ollama."""
        mock_call_gemini.side_effect = RuntimeError("429 RESOURCE_EXHAUSTED: Free tier quota exceeded")
        mock_call_ollama.return_value = {
            "data": {
                "category": "outerwear",
                "color": "olive",
                "pattern": "solid",
                "style": "streetwear",
                "season": "winter",
                "material": "wool",
            },
            "raw_text": '{"category": "outerwear"}',
            "model_used": "llava",
            "provider_used": "ollama_fallback",
        }

        result = get_vision_completion(
            prompt="Analyze garment",
            image_url="https://example.com/parka.jpg",
        )

        self.assertEqual(result.provider_used, "ollama_fallback")
        self.assertEqual(result.model_used, "llava")
        self.assertIn("RESOURCE_EXHAUSTED", result.error_reason)
        self.assertEqual(result.data["category"], "outerwear")
        mock_call_ollama.assert_called_once()

    @patch("app.services.llm_provider.call_ollama_vision")
    @patch("app.services.llm_provider.call_gemini_vision")
    def test_fallback_on_primary_timeout(self, mock_call_gemini, mock_call_ollama):
        """When Gemini times out, seamlessly falls back to Ollama."""
        mock_call_gemini.side_effect = TimeoutError("Gemini API request timed out after 60s")
        mock_call_ollama.return_value = {
            "data": {
                "category": "dress",
                "color": "floral red",
                "pattern": "floral",
                "style": "bohemian",
                "season": "summer",
                "material": "silk",
            },
            "raw_text": '{"category": "dress"}',
            "model_used": "llava",
            "provider_used": "ollama_fallback",
        }

        result = get_vision_completion(
            prompt="Analyze garment",
            image_url="https://example.com/dress.jpg",
        )

        self.assertEqual(result.provider_used, "ollama_fallback")
        self.assertIn("timed out", result.error_reason.lower())
        self.assertEqual(result.data["category"], "dress")

    @patch("app.services.llm_provider.call_ollama_vision")
    @patch("app.services.llm_provider.call_gemini_vision")
    def test_fallback_on_connection_failure(self, mock_call_gemini, mock_call_ollama):
        """When Gemini connection fails, seamlessly falls back to Ollama."""
        mock_call_gemini.side_effect = ConnectionError("Failed to connect to generativelanguage.googleapis.com")
        mock_call_ollama.return_value = {
            "data": {
                "category": "bottom",
                "color": "blue",
                "pattern": "solid",
                "style": "casual",
                "season": "all-season",
                "material": "denim",
            },
            "raw_text": '{"category": "bottom"}',
            "model_used": "llava",
            "provider_used": "ollama_fallback",
        }

        result = get_vision_completion(
            prompt="Analyze garment",
            image_url="https://example.com/jeans.jpg",
        )

        self.assertEqual(result.provider_used, "ollama_fallback")
        self.assertEqual(result.data["category"], "bottom")

    @patch("app.services.llm_provider.call_ollama_vision")
    def test_fallback_on_missing_api_key(self, mock_call_ollama):
        """Missing or empty GEMINI_API_KEY falls back to Ollama without throwing unhandled error."""
        mock_call_ollama.return_value = {
            "data": {
                "category": "top",
                "color": "white",
                "pattern": "solid",
                "style": "minimalist",
                "season": "all-season",
                "material": "cotton",
            },
            "raw_text": '{"category": "top"}',
            "model_used": "llava",
            "provider_used": "ollama_fallback",
        }

        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            result = get_vision_completion(
                prompt="Analyze garment",
                image_url="https://example.com/tshirt.jpg",
            )

        self.assertEqual(result.provider_used, "ollama_fallback")
        self.assertEqual(result.data["category"], "top")
        self.assertIn("GEMINI_API_KEY", result.error_reason)

    @patch("app.services.llm_provider.call_ollama_vision")
    @patch("app.services.llm_provider.call_gemini_vision")
    def test_analyze_image_refactored_with_fallback(self, mock_call_gemini, mock_call_ollama):
        """analyze_image returns full structured garment attributes including provider_used."""
        # Cloud fails
        mock_call_gemini.side_effect = RuntimeError("429 Quota Exceeded")
        # Ollama succeeds with slightly rough local output
        mock_call_ollama.return_value = {
            "data": {
                "category": "TOP",
                "color": "beige",
                "pattern": "solid",
                "style": "smart-casual",
                # season and material omitted by local model to test sensible defaults
            },
            "raw_text": "...",
            "model_used": "llava",
            "provider_used": "ollama_fallback",
        }

        extracted = analyze_image("https://example.com/sweater.jpg")

        self.assertEqual(extracted["category"], "top")
        self.assertEqual(extracted["color"], "beige")
        self.assertEqual(extracted["pattern"], "solid")
        self.assertEqual(extracted["style"], "smart-casual")
        self.assertEqual(extracted["season"], "all-season")  # Sensible default
        self.assertEqual(extracted["material"], "cotton")      # Sensible default
        self.assertEqual(extracted["provider_used"], "ollama_fallback")

    @patch("app.services.llm_provider.call_ollama_vision")
    @patch("app.services.llm_provider.call_gemini_vision")
    def test_analyze_fit_refactored_with_fallback(self, mock_call_gemini, mock_call_ollama):
        """analyze_fit derives fit signals with provider_used flag during fallback."""
        mock_call_gemini.side_effect = ConnectionError("Cloud unreachable")
        mock_call_ollama.return_value = {
            "data": {
                "fit_tightness": "LOOSE",
                "silhouette": "BOXY",
                "notes": "Loose fit over shoulders and chest.",
            },
            "raw_text": "...",
            "model_used": "llava",
            "provider_used": "ollama_fallback",
        }

        fit_result = analyze_fit("https://example.com/render.jpg")

        self.assertEqual(fit_result["fit_tightness"], "loose")
        self.assertEqual(fit_result["silhouette"], "boxy")
        self.assertEqual(fit_result["notes"], "Loose fit over shoulders and chest.")
        self.assertEqual(fit_result["provider_used"], "ollama_fallback")

    @patch("app.services.llm_provider.call_ollama_vision")
    @patch("app.services.llm_provider.call_gemini_vision")
    def test_candidate_intake_survives_gemini_outage(self, mock_call_gemini, mock_call_ollama):
        """Full Candidate Intake completes successfully when Gemini is down, using Ollama fallback."""
        mock_call_gemini.side_effect = RuntimeError("429 RESOURCE_EXHAUSTED")
        mock_call_ollama.return_value = {
            "data": {
                "category": "top",
                "color": "navy",
                "pattern": "solid",
                "style": "classic",
                "season": "all-season",
                "material": "cotton",
            },
            "raw_text": "...",
            "model_used": "llava",
            "provider_used": "ollama_fallback",
        }

        mock_file = MagicMock()
        mock_file.filename = "candidate_shirt.jpg"
        mock_file.content_type = "image/jpeg"
        mock_user = {"uid": "user_m34_intake", "email": "m34@example.com"}

        mock_owner = User(id=340, firebase_uid="user_m34_intake", email="m34@example.com")
        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = mock_owner

        with patch("app.routers.candidates._file_is_allowed", return_value=True), \
             patch("app.routers.candidates._stream_to_temp", return_value=("/tmp/dummy.jpg", 1024)), \
             patch("app.routers.candidates.upload_image", return_value={"url": "https://cloudinary.com/shirt.jpg", "public_id": "test_id"}), \
             patch("app.routers.candidates.generate_tryon", return_value={"render_url": "https://youcam.com/render.jpg", "fit_tightness": "regular", "silhouette": "relaxed"}), \
             patch("app.routers.candidates.generate_embedding", return_value=[0.1] * 512), \
             patch("app.routers.candidates.upsert_wardrobe_embedding"), \
             patch("app.routers.candidates.find_near_duplicate", return_value=None):

            from app.routers.candidates import evaluate_candidate_item

            response = asyncio.run(
                evaluate_candidate_item(
                    file=mock_file,
                    price="49.99",
                    user=mock_user,
                    db=mock_db,
                )
            )

        self.assertIn("candidate_item_id", response)
        self.assertIsNotNone(response["attributes"])
        self.assertEqual(response["attributes"]["category"], "top")
        self.assertEqual(response["attributes"]["provider_used"], "ollama_fallback")

    @patch("app.services.llm_provider.call_ollama_vision")
    @patch("app.services.llm_provider.call_gemini_vision")
    def test_both_providers_fail_raises_runtime_error(self, mock_call_gemini, mock_call_ollama):
        """When both primary Gemini and local Ollama fail, raises RuntimeError explaining both."""
        mock_call_gemini.side_effect = RuntimeError("429 Quota Exceeded")
        mock_call_ollama.side_effect = ConnectionError("Ollama daemon not running on port 11434")

        with self.assertRaises(RuntimeError) as ctx:
            get_vision_completion("prompt", "https://example.com/item.jpg")

        err_msg = str(ctx.exception)
        self.assertIn("429 Quota Exceeded", err_msg)
        self.assertIn("Ollama daemon not running", err_msg)


if __name__ == "__main__":
    unittest.main()
