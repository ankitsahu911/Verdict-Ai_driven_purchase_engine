"""
Router Integration Test for POST /api/tryon/{wardrobe_item_id}.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.auth import get_current_user
from app.db import get_db
from verdict_backend.main import app


class TestTryOnRouter(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("app.routers.tryon.generate_tryon")
    def test_create_tryon_render_endpoint_success(self, mock_generate_tryon):
        """Test POST /api/tryon/{wardrobe_item_id} returns combined JSON response."""
        user_dict = {
            "uid": "test_user_uid",
            "email": "test@example.com",
        }

        # Mock DB user & wardrobe item
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.firebase_uid = "test_user_uid"

        mock_item = MagicMock()
        mock_item.id = 42
        mock_item.user_id = 1
        mock_item.cloudinary_url = "https://cloudinary.com/garment.jpg"

        mock_db.query().filter().first.side_effect = [mock_user, mock_item]

        # Mock generate_tryon combined result
        mock_generate_tryon.return_value = {
            "render_url": "https://youcam.com/render_output.jpg",
            "fit_tightness": "regular",
            "silhouette": "tailored",
            "notes": "Natural drape around shoulders and torso.",
        }

        # Set dependency overrides
        app.dependency_overrides[get_current_user] = lambda: user_dict
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            response = self.client.post(
                "/api/tryon/42",
                json={"user_photo_url": "https://example.com/user.jpg"},
            )

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["render_url"], "https://youcam.com/render_output.jpg")
            self.assertEqual(data["fit_tightness"], "regular")
            self.assertEqual(data["silhouette"], "tailored")
            self.assertEqual(data["notes"], "Natural drape around shoulders and torso.")
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
