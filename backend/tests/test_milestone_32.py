"""
Milestone 32 Unit Tests:
Try-On Agent Caching, Cache Validation Against Model Photo URL,
Invalidation, and Logging.
"""

import logging
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.auth import get_current_user
from app.db import get_db
from app.models import User, WardrobeItem
from verdict_backend.main import app


class TestMilestone32TryOnCaching(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_schema_columns_exist(self):
        """Verify tryon_cached_model_photo_url exists on WardrobeItem and model_photo_url on User."""
        self.assertTrue(hasattr(WardrobeItem, "tryon_cached_model_photo_url"))
        self.assertTrue(hasattr(WardrobeItem, "tryon_render_url"))
        self.assertTrue(hasattr(WardrobeItem, "fit_tightness"))
        self.assertTrue(hasattr(WardrobeItem, "silhouette"))
        self.assertTrue(hasattr(User, "model_photo_url"))

    @patch("app.routers.tryon.generate_tryon")
    def test_tryon_cache_miss_then_hit(self, mock_generate_tryon):
        """Viewing the same candidate item twice only calls YouCam once (cache miss then hit)."""
        mock_generate_tryon.return_value = {
            "render_url": "https://youcam.com/render_fresh.jpg",
            "fit_tightness": "regular",
            "silhouette": "tailored",
            "notes": "Good shoulder fit",
        }

        user_dict = {"uid": "user_m32", "email": "m32@example.com"}

        mock_user = MagicMock()
        mock_user.id = 10
        mock_user.firebase_uid = "user_m32"
        mock_user.email = "m32@example.com"
        mock_user.model_photo_url = "https://example.com/user_photo_v1.jpg"

        class FakeItem:
            id = 101
            user_id = 10
            cloudinary_url = "https://cloudinary.com/jacket.jpg"
            tryon_render_url = None
            tryon_cached_model_photo_url = None
            fit_tightness = None
            silhouette = None

        fake_item = FakeItem()

        mock_db = MagicMock()

        def mock_query(model):
            q = MagicMock()
            if model == User:
                q.filter.return_value.first.return_value = mock_user
            else:
                q.filter.return_value.first.return_value = fake_item
            return q

        mock_db.query.side_effect = mock_query

        app.dependency_overrides[get_current_user] = lambda: user_dict
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            # 1. FIRST CALL: Cache MISS -> calls YouCam
            resp1 = self.client.post("/api/tryon/101")
            self.assertEqual(resp1.status_code, 200)
            data1 = resp1.json()
            self.assertFalse(data1["cached"])
            self.assertEqual(data1["render_url"], "https://youcam.com/render_fresh.jpg")
            self.assertEqual(mock_generate_tryon.call_count, 1)

            # Verify fake_item was updated in-memory
            self.assertEqual(fake_item.tryon_render_url, "https://youcam.com/render_fresh.jpg")
            self.assertEqual(
                fake_item.tryon_cached_model_photo_url,
                "https://example.com/user_photo_v1.jpg",
            )

            # 2. SECOND CALL: Cache HIT -> returns cached values without calling YouCam
            resp2 = self.client.post("/api/tryon/101")
            self.assertEqual(resp2.status_code, 200)
            data2 = resp2.json()
            self.assertTrue(data2["cached"])
            self.assertEqual(data2["render_url"], "https://youcam.com/render_fresh.jpg")
            self.assertEqual(data2["fit_tightness"], "regular")
            self.assertEqual(data2["silhouette"], "tailored")
            # Call count MUST STILL BE 1!
            self.assertEqual(mock_generate_tryon.call_count, 1)

            # 3. GET /api/tryon/101 returns cached result
            resp_get = self.client.get("/api/tryon/101")
            self.assertEqual(resp_get.status_code, 200)
            data_get = resp_get.json()
            self.assertTrue(data_get["cached"])
            self.assertEqual(data_get["render_url"], "https://youcam.com/render_fresh.jpg")

        finally:
            app.dependency_overrides.clear()

    @patch("app.routers.tryon.generate_tryon")
    def test_cache_invalidation_when_model_photo_changes(self, mock_generate_tryon):
        """Updating user model photo invalidates the cache and triggers a fresh YouCam render."""
        mock_generate_tryon.side_effect = [
            {
                "render_url": "https://youcam.com/render_photo1.jpg",
                "fit_tightness": "regular",
                "silhouette": "tailored",
                "notes": "Render with photo 1",
            },
            {
                "render_url": "https://youcam.com/render_photo2.jpg",
                "fit_tightness": "loose",
                "silhouette": "relaxed",
                "notes": "Render with photo 2",
            },
        ]

        user_dict = {"uid": "user_m32_inval", "email": "inval@example.com"}

        mock_user = MagicMock()
        mock_user.id = 20
        mock_user.firebase_uid = "user_m32_inval"
        mock_user.email = "inval@example.com"
        mock_user.model_photo_url = "https://example.com/photo_A.jpg"

        class FakeItem:
            id = 202
            user_id = 20
            cloudinary_url = "https://cloudinary.com/dress.jpg"
            tryon_render_url = None
            tryon_cached_model_photo_url = None
            fit_tightness = None
            silhouette = None

        fake_item = FakeItem()
        mock_db = MagicMock()

        def mock_query(model):
            q = MagicMock()
            if model == User:
                q.filter.return_value.first.return_value = mock_user
            else:
                q.filter.return_value.first.return_value = fake_item
            return q

        mock_db.query.side_effect = mock_query

        app.dependency_overrides[get_current_user] = lambda: user_dict
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            # First call with photo_A
            resp1 = self.client.post("/api/tryon/202")
            self.assertEqual(resp1.status_code, 200)
            self.assertEqual(resp1.json()["render_url"], "https://youcam.com/render_photo1.jpg")
            self.assertEqual(mock_generate_tryon.call_count, 1)
            self.assertEqual(fake_item.tryon_cached_model_photo_url, "https://example.com/photo_A.jpg")

            # User updates their model photo to photo_B
            mock_user.model_photo_url = "https://example.com/photo_B.jpg"

            # Second call: Model photo changed -> Cache MISS -> Calls YouCam again
            resp2 = self.client.post("/api/tryon/202")
            self.assertEqual(resp2.status_code, 200)
            data2 = resp2.json()
            self.assertFalse(data2["cached"])
            self.assertEqual(data2["render_url"], "https://youcam.com/render_photo2.jpg")
            self.assertEqual(mock_generate_tryon.call_count, 2)
            self.assertEqual(fake_item.tryon_cached_model_photo_url, "https://example.com/photo_B.jpg")

            # Third call with photo_B -> Cache HIT
            resp3 = self.client.post("/api/tryon/202")
            self.assertEqual(resp3.status_code, 200)
            self.assertTrue(resp3.json()["cached"])
            self.assertEqual(mock_generate_tryon.call_count, 2)

        finally:
            app.dependency_overrides.clear()

    @patch("app.routers.tryon.generate_tryon")
    def test_force_refresh_bypasses_cache(self, mock_generate_tryon):
        """Query param ?force=true forces a fresh YouCam render even if cached."""
        mock_generate_tryon.return_value = {
            "render_url": "https://youcam.com/render_forced.jpg",
            "fit_tightness": "fitted",
            "silhouette": "straight",
            "notes": "Forced fresh render",
        }

        user_dict = {"uid": "user_m32_force", "email": "force@example.com"}

        mock_user = MagicMock()
        mock_user.id = 30
        mock_user.firebase_uid = "user_m32_force"
        mock_user.email = "force@example.com"
        mock_user.model_photo_url = "https://example.com/user.jpg"

        class FakeItem:
            id = 303
            user_id = 30
            cloudinary_url = "https://cloudinary.com/pants.jpg"
            tryon_render_url = "https://youcam.com/old_render.jpg"
            tryon_cached_model_photo_url = "https://example.com/user.jpg"
            fit_tightness = "regular"
            silhouette = "tailored"

        fake_item = FakeItem()
        mock_db = MagicMock()

        def mock_query(model):
            q = MagicMock()
            if model == User:
                q.filter.return_value.first.return_value = mock_user
            else:
                q.filter.return_value.first.return_value = fake_item
            return q

        mock_db.query.side_effect = mock_query

        app.dependency_overrides[get_current_user] = lambda: user_dict
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            # Call with ?force=true
            resp = self.client.post("/api/tryon/303?force=true")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertFalse(data["cached"])
            self.assertEqual(data["render_url"], "https://youcam.com/render_forced.jpg")
            self.assertEqual(mock_generate_tryon.call_count, 1)
        finally:
            app.dependency_overrides.clear()

    @patch("app.routers.tryon.generate_tryon")
    def test_cache_hit_and_miss_logging(self, mock_generate_tryon):
        """Verify clear [TryOn Cache] HIT and MISS logging."""
        mock_generate_tryon.return_value = {
            "render_url": "https://youcam.com/render_log.jpg",
            "fit_tightness": "regular",
            "silhouette": "tailored",
        }

        user_dict = {"uid": "user_m32_log", "email": "log@example.com"}

        mock_user = MagicMock()
        mock_user.id = 40
        mock_user.firebase_uid = "user_m32_log"
        mock_user.email = "log@example.com"
        mock_user.model_photo_url = "https://example.com/model.jpg"

        class FakeItem:
            id = 404
            user_id = 40
            cloudinary_url = "https://cloudinary.com/coat.jpg"
            tryon_render_url = None
            tryon_cached_model_photo_url = None
            fit_tightness = None
            silhouette = None

        fake_item = FakeItem()
        mock_db = MagicMock()

        def mock_query(model):
            q = MagicMock()
            if model == User:
                q.filter.return_value.first.return_value = mock_user
            else:
                q.filter.return_value.first.return_value = fake_item
            return q

        mock_db.query.side_effect = mock_query

        app.dependency_overrides[get_current_user] = lambda: user_dict
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            with self.assertLogs("app.routers.tryon", level=logging.INFO) as log_context:
                # 1. First call -> MISS
                self.client.post("/api/tryon/404")
                self.assertTrue(any("[TryOn Cache] MISS" in msg for msg in log_context.output))

                # 2. Second call -> HIT
                self.client.post("/api/tryon/404")
                self.assertTrue(any("[TryOn Cache] HIT" in msg for msg in log_context.output))
        finally:
            app.dependency_overrides.clear()

    def test_patch_model_photo_endpoint(self):
        """Verify PATCH /api/me/model-photo updates and returns the user's model photo URL."""
        user_dict = {"uid": "user_patch_test", "email": "patch@example.com"}

        mock_user = MagicMock()
        mock_user.id = 50
        mock_user.firebase_uid = "user_patch_test"
        mock_user.email = "patch@example.com"
        mock_user.model_photo_url = "https://example.com/old_photo.jpg"

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = mock_user

        app.dependency_overrides[get_current_user] = lambda: user_dict
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            resp = self.client.patch(
                "/api/me/model-photo",
                json={"model_photo_url": "https://example.com/new_model_photo.jpg"},
            )
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["user_id"], 50)
            self.assertEqual(data["model_photo_url"], "https://example.com/new_model_photo.jpg")
            self.assertEqual(mock_user.model_photo_url, "https://example.com/new_model_photo.jpg")
            mock_db.commit.assert_called()
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
