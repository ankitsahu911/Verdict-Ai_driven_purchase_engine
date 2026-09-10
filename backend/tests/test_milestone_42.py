"""
Unit and Concurrency Tests for Milestone 42:
Parallelization of the Candidate Item Intake Flow.

Validates:
1. Genuine concurrency: independent agents (Vision, Try-On, Embedding) run concurrently
   and total wall time is significantly less than the sequential sum.
2. Dependency structure: Duplicate Detection is pipelined immediately after Embedding Agent
   completes, starting before longer agents (Vision/Try-On) finish.
3. Fault isolation: Failure in one agent does not abort or crash sibling concurrent agents.
4. Timing instrumentation: Latency metrics are recorded for each agent and validated against
   the 15-second single-item target.
"""

import asyncio
import io
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from PIL import Image

from app.auth import get_current_user
from app.db import get_db
from app.models import GarmentAttributes, User, WardrobeItem
from app.services.tryon_service import TryOnTimeoutError
from app.services.vision_service import VisionServiceError
from app.routers.candidates import evaluate_candidate_item
from verdict_backend.main import app


class TestMilestone42ParallelIntake(unittest.TestCase):
    def setUp(self):
        self.mock_user = {
            "uid": "m42_parallel_user",
            "email": "m42@example.com",
            "name": "M42 Parallel Tester",
        }
        app.dependency_overrides[get_current_user] = lambda: self.mock_user
        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_concurrent_execution_speedup_vs_sequential_sum(self):
        """
        Verify that Vision, Try-On, and Embedding agents execute concurrently in worker threads.
        With synthetic delays:
          Vision = 0.25s, Try-On = 0.35s, Embedding = 0.15s, Duplicate = 0.10s.
          Sequential sum = 0.25 + 0.35 + 0.15 + 0.10 = 0.85s.
          Parallel wall time = max(0.25, 0.35, 0.15 + 0.10) = 0.35s (+ slight overhead).
        Wall time must be well under 0.65s, proving genuine concurrency.
        """
        def delayed_vision(url):
            time.sleep(0.25)
            return {
                "category": "top",
                "color": "navy",
                "pattern": "solid",
                "style": "casual",
                "season": "all-season",
                "material": "cotton",
                "provider_used": "gemini",
            }

        def delayed_tryon(garment_url, user_photo_url=None, garment_category=None):
            time.sleep(0.35)
            return {
                "render_url": "https://youcam.com/render.jpg",
                "fit_tightness": "regular",
                "silhouette": "relaxed",
            }

        def delayed_embedding(url):
            time.sleep(0.15)
            return [0.1] * 512

        def delayed_find_dup(query_embedding, user_id, exclude_item_id=None):
            time.sleep(0.10)
            return None

        mock_owner = User(id=10, firebase_uid="m42_parallel_user", email="m42@example.com")
        mock_cand_item = WardrobeItem(id=501, user_id=10, is_candidate=True, cloudinary_url="https://res.cloudinary.com/test.jpg")

        def db_query(model_cls):
            q = MagicMock()
            if model_cls == User:
                q.filter.return_value.first.return_value = mock_owner
            elif model_cls == WardrobeItem:
                q.filter.return_value.first.return_value = mock_cand_item
            return q

        self.mock_db.query.side_effect = db_query

        mock_file = MagicMock()
        mock_file.filename = "shirt.jpg"
        mock_file.content_type = "image/jpeg"

        with patch("app.routers.candidates._stream_to_temp", return_value=("/tmp/dummy.jpg", 1024)), \
             patch("app.routers.candidates._file_is_allowed", return_value=True), \
             patch("app.routers.candidates.upload_image", return_value={"url": "https://res.cloudinary.com/test.jpg", "public_id": "p1"}), \
             patch("app.routers.candidates.analyze_image", side_effect=delayed_vision), \
             patch("app.routers.candidates.generate_tryon", side_effect=delayed_tryon), \
             patch("app.routers.candidates.generate_embedding", side_effect=delayed_embedding), \
             patch("app.routers.candidates.upsert_wardrobe_embedding"), \
             patch("app.routers.candidates.find_near_duplicate", side_effect=delayed_find_dup):

            t_start = time.perf_counter()
            response = asyncio.run(
                evaluate_candidate_item(
                    file=mock_file,
                    price=None,
                    user=self.mock_user,
                    db=self.mock_db,
                )
            )
            wall_time = time.perf_counter() - t_start

        # Assert output correctness
        self.assertIn("candidate_item_id", response)
        self.assertIn("timings", response)
        timings = response["timings"]

        # Sequential sum would be >= 0.80s; parallel wall time must be < 0.65s
        self.assertLess(
            wall_time,
            0.65,
            f"Expected parallel wall time < 0.65s, but took {wall_time:.3f}s (sequential sum is ~0.85s)",
        )
        self.assertTrue(timings["meets_target"])
        self.assertLessEqual(timings["total_ms"], 15000.0)

    def test_duplicate_detection_pipelined_after_embedding_before_vision_finishes(self):
        """
        Verify the real dependency structure:
        - Duplicate Detection starts strictly after Embedding finishes (t_dup_start >= t_emb_end).
        - Duplicate Detection starts BEFORE the longer Vision agent finishes (t_dup_start < t_vision_end).
        This proves Duplicate Detection is pipelined directly on Embedding, not waiting on Vision.
        """
        events = {}

        def mock_vision(url):
            events["vision_start"] = time.perf_counter()
            time.sleep(0.30)  # Long vision agent
            events["vision_end"] = time.perf_counter()
            return {"category": "outerwear", "color": "black", "pattern": "solid", "style": "casual", "season": "winter", "material": "wool"}

        def mock_tryon(garment_url, user_photo_url=None, garment_category=None):
            events["tryon_start"] = time.perf_counter()
            time.sleep(0.10)
            events["tryon_end"] = time.perf_counter()
            return {"render_url": "https://youcam.com/r.jpg", "fit_tightness": "regular", "silhouette": "relaxed"}

        def mock_embedding(url):
            events["embedding_start"] = time.perf_counter()
            time.sleep(0.08)  # Quick embedding agent
            events["embedding_end"] = time.perf_counter()
            return [0.2] * 512

        def mock_find_dup(query_embedding, user_id, exclude_item_id=None):
            events["duplicate_start"] = time.perf_counter()
            time.sleep(0.04)
            events["duplicate_end"] = time.perf_counter()
            return None

        mock_owner = User(id=11, firebase_uid="m42_parallel_user", email="m42@example.com")
        mock_cand_item = WardrobeItem(id=502, user_id=11, is_candidate=True, cloudinary_url="https://res.cloudinary.com/test.jpg")

        def db_query(model_cls):
            q = MagicMock()
            if model_cls == User:
                q.filter.return_value.first.return_value = mock_owner
            elif model_cls == WardrobeItem:
                q.filter.return_value.first.return_value = mock_cand_item
            return q

        self.mock_db.query.side_effect = db_query

        mock_file = MagicMock(filename="coat.jpg", content_type="image/jpeg")

        with patch("app.routers.candidates._stream_to_temp", return_value=("/tmp/dummy.jpg", 1024)), \
             patch("app.routers.candidates._file_is_allowed", return_value=True), \
             patch("app.routers.candidates.upload_image", return_value={"url": "https://res.cloudinary.com/test.jpg", "public_id": "p2"}), \
             patch("app.routers.candidates.analyze_image", side_effect=mock_vision), \
             patch("app.routers.candidates.generate_tryon", side_effect=mock_tryon), \
             patch("app.routers.candidates.generate_embedding", side_effect=mock_embedding), \
             patch("app.routers.candidates.upsert_wardrobe_embedding"), \
             patch("app.routers.candidates.find_near_duplicate", side_effect=mock_find_dup):

            response = asyncio.run(
                evaluate_candidate_item(
                    file=mock_file,
                    price=None,
                    user=self.mock_user,
                    db=self.mock_db,
                )
            )

        # 1. Duplicate detection started AFTER embedding finished
        self.assertGreaterEqual(
            events["duplicate_start"],
            events["embedding_end"],
            "Duplicate Detection must start after Embedding Agent completes.",
        )

        # 2. Duplicate detection started BEFORE vision finished
        self.assertLess(
            events["duplicate_start"],
            events["vision_end"],
            "Duplicate Detection must start as soon as Embedding is ready, without waiting for Vision.",
        )

        # 3. Vision, Try-On, and Embedding all started approximately at the same time (within 50ms)
        start_spread = max(events["vision_start"], events["tryon_start"], events["embedding_start"]) - \
                       min(events["vision_start"], events["tryon_start"], events["embedding_start"])
        self.assertLess(
            start_spread,
            0.08,
            f"Independent agents should start concurrently; start spread was {start_spread*1000:.1f}ms",
        )

    def test_fault_isolation_vision_error_does_not_block_sibling_agents(self):
        """
        If Vision Agent raises an error, Try-On and Duplicate Detection must still complete
        successfully in parallel.
        """
        mock_owner = User(id=12, firebase_uid="m42_parallel_user", email="m42@example.com")
        mock_cand_item = WardrobeItem(id=503, user_id=12, is_candidate=True, cloudinary_url="https://res.cloudinary.com/test.jpg")

        def db_query(model_cls):
            q = MagicMock()
            if model_cls == User:
                q.filter.return_value.first.return_value = mock_owner
            elif model_cls == WardrobeItem:
                q.filter.return_value.first.return_value = mock_cand_item
            return q

        self.mock_db.query.side_effect = db_query
        mock_file = MagicMock(filename="test.jpg", content_type="image/jpeg")

        with patch("app.routers.candidates._stream_to_temp", return_value=("/tmp/dummy.jpg", 1024)), \
             patch("app.routers.candidates._file_is_allowed", return_value=True), \
             patch("app.routers.candidates.upload_image", return_value={"url": "https://res.cloudinary.com/test.jpg", "public_id": "p3"}), \
             patch("app.routers.candidates.analyze_image", side_effect=VisionServiceError("Cloud quota exhausted")), \
             patch("app.routers.candidates.generate_tryon", return_value={"render_url": "https://youcam.com/r.jpg", "fit_tightness": "regular", "silhouette": "relaxed"}), \
             patch("app.routers.candidates.generate_embedding", return_value=[0.3] * 512), \
             patch("app.routers.candidates.upsert_wardrobe_embedding"), \
             patch("app.routers.candidates.find_near_duplicate", return_value=None):

            response = asyncio.run(
                evaluate_candidate_item(
                    file=mock_file,
                    price=None,
                    user=self.mock_user,
                    db=self.mock_db,
                )
            )

        self.assertIsNone(response["attributes"])
        self.assertIn("attributes", response["errors"])
        self.assertIn("quota exhausted", response["errors"]["attributes"].lower())
        # Try-on succeeded despite Vision failure
        self.assertIsNotNone(response["tryon"])
        self.assertEqual(response["tryon"]["render_url"], "https://youcam.com/r.jpg")
        # Timings still recorded accurately
        self.assertIn("timings", response)
        self.assertTrue(response["timings"]["meets_target"])

    def test_fault_isolation_tryon_timeout_does_not_block_sibling_agents(self):
        """
        If Try-On Agent times out (TryOnTimeoutError), Vision and Duplicate Detection
        still succeed, and M33 graceful degradation applies.
        """
        mock_owner = User(id=13, firebase_uid="m42_parallel_user", email="m42@example.com")
        mock_cand_item = WardrobeItem(id=504, user_id=13, is_candidate=True, cloudinary_url="https://res.cloudinary.com/test.jpg")

        def db_query(model_cls):
            q = MagicMock()
            if model_cls == User:
                q.filter.return_value.first.return_value = mock_owner
            elif model_cls == WardrobeItem:
                q.filter.return_value.first.return_value = mock_cand_item
            return q

        self.mock_db.query.side_effect = db_query
        mock_file = MagicMock(filename="test.jpg", content_type="image/jpeg")

        with patch("app.routers.candidates._stream_to_temp", return_value=("/tmp/dummy.jpg", 1024)), \
             patch("app.routers.candidates._file_is_allowed", return_value=True), \
             patch("app.routers.candidates.upload_image", return_value={"url": "https://res.cloudinary.com/test.jpg", "public_id": "p4"}), \
             patch("app.routers.candidates.analyze_image", return_value={"category": "top", "color": "white", "pattern": "solid", "style": "casual", "season": "summer", "material": "cotton"}), \
             patch("app.routers.candidates.generate_tryon", side_effect=TryOnTimeoutError("YouCam timed out after 15s")), \
             patch("app.routers.candidates.generate_embedding", return_value=[0.4] * 512), \
             patch("app.routers.candidates.upsert_wardrobe_embedding"), \
             patch("app.routers.candidates.find_near_duplicate", return_value=None):

            response = asyncio.run(
                evaluate_candidate_item(
                    file=mock_file,
                    price=None,
                    user=self.mock_user,
                    db=self.mock_db,
                )
            )

        self.assertIsNotNone(response["attributes"])
        self.assertEqual(response["attributes"]["category"], "top")
        self.assertIsNotNone(response["tryon"])
        self.assertTrue(response["tryon"]["tryon_degraded"])
        self.assertIn("tryon", response["errors"])
        self.assertIn("unavailable", response["errors"]["tryon"].lower())


if __name__ == "__main__":
    unittest.main()
