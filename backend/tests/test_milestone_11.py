"""
Unit and Integration Tests for Milestone 11: Structured Fit Analysis & Try-On Agent.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.tryon_service import TryOnServiceError, generate_tryon
from app.services.vision_service import VisionServiceError, analyze_fit


class TestMilestone11FitAnalysis(unittest.TestCase):
    @patch("app.services.vision_service._get_client")
    def test_analyze_fit_success(self, mock_get_client):
        """Test analyze_fit parses structured fit response correctly."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.parsed = {
            "fit_tightness": "regular",
            "silhouette": "tailored",
            "notes": "Fits nicely around chest and waist.",
        }
        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client

        res = analyze_fit("https://example.com/render.jpg")

        self.assertEqual(res["fit_tightness"], "regular")
        self.assertEqual(res["silhouette"], "tailored")
        self.assertEqual(res["notes"], "Fits nicely around chest and waist.")

    @patch("app.services.vision_service._get_client")
    def test_analyze_fit_normalizes_enums(self, mock_get_client):
        """Test analyze_fit normalizes case and falls back gracefully for invalid enum values."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.parsed = {
            "fit_tightness": "LOOSE",
            "silhouette": "INVALID_SILHOUETTE",
            "notes": "Casual oversized look.",
        }
        mock_client.models.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client

        res = analyze_fit("https://example.com/render.jpg")

        self.assertEqual(res["fit_tightness"], "loose")
        self.assertEqual(res["silhouette"], "tailored")  # fallback default
        self.assertEqual(res["notes"], "Casual oversized look.")

    def test_analyze_fit_missing_url(self):
        """Test analyze_fit raises VisionServiceError when image URL is missing."""
        with self.assertRaises(VisionServiceError):
            analyze_fit("")

    @patch("app.services.tryon_service.requests.post")
    @patch("app.services.tryon_service.requests.get")
    @patch("app.services.tryon_service.analyze_fit")
    def test_generate_tryon_combined_success(self, mock_analyze_fit, mock_requests_get, mock_requests_post):
        """Test generate_tryon returns combined render_url and fit signals on success."""
        # Mock YouCam task creation
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {
            "status": 200,
            "data": {"task_id": "test_task_123"},
        }
        mock_requests_post.return_value = mock_post_resp

        # Mock YouCam task polling success
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.raise_for_status.return_value = None
        mock_get_resp.json.return_value = {
            "status": 200,
            "data": {
                "task_status": "success",
                "results": {"url": "https://youcam.com/render_123.jpg"},
            },
        }
        mock_requests_get.return_value = mock_get_resp

        # Mock fit analysis
        mock_analyze_fit.return_value = {
            "fit_tightness": "regular",
            "silhouette": "tailored",
            "notes": "Clean drape through body.",
        }

        with patch.dict(os.environ, {"YOUCAM_API_KEY": "test_key", "YOUCAM_SRC_URL": "http://model.jpg"}):
            result = generate_tryon("http://garment.jpg")

        self.assertEqual(result["render_url"], "https://youcam.com/render_123.jpg")
        self.assertEqual(result["fit_tightness"], "regular")
        self.assertEqual(result["silhouette"], "tailored")
        self.assertEqual(result["notes"], "Clean drape through body.")

    @patch("app.services.tryon_service.requests.post")
    @patch("app.services.tryon_service.requests.get")
    @patch("app.services.tryon_service.analyze_fit")
    def test_generate_tryon_fit_failure_resilience(self, mock_analyze_fit, mock_requests_get, mock_requests_post):
        """Test generate_tryon returns render_url with null fit fields if fit analysis fails (Requirement 4)."""
        # Mock YouCam task creation
        mock_post_resp = MagicMock()
        mock_post_resp.status_code = 200
        mock_post_resp.json.return_value = {
            "status": 200,
            "data": {"task_id": "test_task_123"},
        }
        mock_requests_post.return_value = mock_post_resp

        # Mock YouCam task polling success
        mock_get_resp = MagicMock()
        mock_get_resp.status_code = 200
        mock_get_resp.raise_for_status.return_value = None
        mock_get_resp.json.return_value = {
            "status": 200,
            "data": {
                "task_status": "success",
                "results": {"url": "https://youcam.com/render_123.jpg"},
            },
        }
        mock_requests_get.return_value = mock_get_resp

        # Mock fit analysis throwing exception
        mock_analyze_fit.side_effect = VisionServiceError("Quota exceeded")

        with patch.dict(os.environ, {"YOUCAM_API_KEY": "test_key", "YOUCAM_SRC_URL": "http://model.jpg"}):
            result = generate_tryon("http://garment.jpg")

        self.assertEqual(result["render_url"], "https://youcam.com/render_123.jpg")
        self.assertIsNone(result["fit_tightness"])
        self.assertIsNone(result["silhouette"])
        self.assertIsNone(result["notes"])


if __name__ == "__main__":
    unittest.main()
