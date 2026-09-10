"""
Milestone 33 Unit Tests:
Virtual Try-On Graceful Degradation during YouCam Outages and Timeouts.
Tests fallback hierarchy (stale cache -> neutral placeholder), tryon_degraded flags,
candidate intake resilience, and full Buy Score synthesis without unhandled errors.
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.auth import get_current_user
from app.db import get_db
from app.models import GarmentAttributes, User, WardrobeItem
from app.decision_engine.orchestrator import synthesize_buy_score
from app.decision_engine.scorers.budget_impact import score_budget_impact
from app.decision_engine.schema import AxisScore, DecisionAxis
from app.services.tryon_service import (
    DEFAULT_FALLBACK_FIT_TIGHTNESS,
    DEFAULT_FALLBACK_SILHOUETTE,
    DEFAULT_TRYON_PLACEHOLDER_URL,
    TryOnConnectionError,
    TryOnServiceError,
    TryOnTimeoutError,
    build_tryon_fallback,
    generate_tryon,
)
from verdict_backend.main import app


class TestMilestone33GracefulDegradation(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_exception_hierarchy(self):
        """Verify custom timeout and connection errors inherit from TryOnServiceError."""
        self.assertTrue(issubclass(TryOnTimeoutError, TryOnServiceError))
        self.assertTrue(issubclass(TryOnConnectionError, TryOnServiceError))

    @patch.dict(os.environ, {"YOUCAM_API_KEY": "test_key", "YOUCAM_SRC_URL": "https://example.com/src.jpg"})
    @patch("requests.post")
    def test_generate_tryon_timeout_exception(self, mock_post):
        """generate_tryon raises TryOnTimeoutError when requests times out."""
        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out after 15s")
        with self.assertRaises(TryOnTimeoutError) as ctx:
            generate_tryon(garment_url="https://example.com/garment.jpg")
        self.assertIn("timed out", str(ctx.exception).lower())

    @patch.dict(os.environ, {"YOUCAM_API_KEY": "test_key", "YOUCAM_SRC_URL": "https://example.com/src.jpg"})
    @patch("requests.post")
    def test_generate_tryon_connection_error(self, mock_post):
        """generate_tryon raises TryOnConnectionError when network connection fails."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Name or service not known")
        with self.assertRaises(TryOnConnectionError) as ctx:
            generate_tryon(garment_url="https://example.com/garment.jpg")
        self.assertIn("failed to connect", str(ctx.exception).lower())

    def test_build_tryon_fallback_with_stale_cache(self):
        """Fallback 2a: Item with previously cached render uses it even if stale, setting tryon_degraded=True."""
        class StaleItem:
            id = 501
            tryon_render_url = "https://youcam.com/old_stale_render.jpg"
            fit_tightness = "fitted"
            silhouette = "tailored"
            cloudinary_url = "https://cloudinary.com/item.jpg"

        stale_item = StaleItem()
        fallback = build_tryon_fallback(stale_item, error_reason="YouCam 503 Outage")

        self.assertEqual(fallback["render_url"], "https://youcam.com/old_stale_render.jpg")
        self.assertEqual(fallback["fit_tightness"], "fitted")
        self.assertEqual(fallback["silhouette"], "tailored")
        self.assertTrue(fallback["tryon_degraded"])
        self.assertTrue(fallback["cached"])
        self.assertIn("stale cached render", fallback["notes"])

    def test_build_tryon_fallback_without_cache(self):
        """Fallback 2b: Item with no cached render gets neutral fit signals and placeholder image."""
        class FreshItem:
            id = 502
            tryon_render_url = None
            fit_tightness = None
            silhouette = None
            cloudinary_url = "https://cloudinary.com/new_shirt.jpg"

        fresh_item = FreshItem()
        fallback = build_tryon_fallback(fresh_item, error_reason="Timeout after 15s")

        self.assertEqual(fallback["render_url"], "https://cloudinary.com/new_shirt.jpg")
        self.assertEqual(fallback["fit_tightness"], DEFAULT_FALLBACK_FIT_TIGHTNESS)  # "regular"
        self.assertEqual(fallback["silhouette"], DEFAULT_FALLBACK_SILHOUETTE)       # "relaxed"
        self.assertTrue(fallback["tryon_degraded"])
        self.assertFalse(fallback["cached"])
        self.assertIn("neutral fit", fallback["notes"])

    @patch("app.routers.tryon.generate_tryon")
    def test_endpoint_fallback_to_stale_cache_on_outage(self, mock_generate_tryon):
        """POST /api/tryon/{id} falls back to stale cache on YouCam error, returning 200 with tryon_degraded=True."""
        mock_generate_tryon.side_effect = TryOnConnectionError("YouCam host unreachable")

        user_dict = {"uid": "user_m33_stale", "email": "stale@example.com"}

        mock_user = MagicMock()
        mock_user.id = 60
        mock_user.firebase_uid = "user_m33_stale"
        mock_user.email = "stale@example.com"
        mock_user.model_photo_url = "https://example.com/new_photo.jpg"

        class FakeItem:
            id = 601
            user_id = 60
            cloudinary_url = "https://cloudinary.com/jacket.jpg"
            tryon_render_url = "https://youcam.com/previous_render.jpg"
            tryon_cached_model_photo_url = "https://example.com/old_photo.jpg"  # Stale model photo
            fit_tightness = "loose"
            silhouette = "oversized"
            tryon_degraded = False

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
            resp = self.client.post("/api/tryon/601")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()

            # Verify response is degraded but successful
            self.assertTrue(data["tryon_degraded"])
            self.assertTrue(data["cached"])
            self.assertEqual(data["render_url"], "https://youcam.com/previous_render.jpg")
            self.assertEqual(data["fit_tightness"], "loose")
            self.assertEqual(data["silhouette"], "oversized")

            # Verify DB item was marked degraded
            self.assertTrue(fake_item.tryon_degraded)
            mock_db.commit.assert_called()
        finally:
            app.dependency_overrides.clear()

    @patch("app.routers.tryon.generate_tryon")
    def test_endpoint_fallback_to_placeholder_when_no_cache(self, mock_generate_tryon):
        """POST /api/tryon/{id} falls back to neutral placeholder on YouCam timeout when no cache exists."""
        mock_generate_tryon.side_effect = TryOnTimeoutError("YouCam task polling timed out")

        user_dict = {"uid": "user_m33_fresh", "email": "fresh@example.com"}

        mock_user = MagicMock()
        mock_user.id = 70
        mock_user.firebase_uid = "user_m33_fresh"
        mock_user.email = "fresh@example.com"
        mock_user.model_photo_url = "https://example.com/model.jpg"

        class FakeItem:
            id = 701
            user_id = 70
            cloudinary_url = "https://cloudinary.com/blazer.jpg"
            tryon_render_url = None
            tryon_cached_model_photo_url = None
            fit_tightness = None
            silhouette = None
            tryon_degraded = False

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
            resp = self.client.post("/api/tryon/701")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()

            # Verify neutral defaults and placeholder
            self.assertTrue(data["tryon_degraded"])
            self.assertFalse(data["cached"])
            self.assertEqual(data["render_url"], "https://cloudinary.com/blazer.jpg")
            self.assertEqual(data["fit_tightness"], "regular")
            self.assertEqual(data["silhouette"], "relaxed")

            # Verify DB item updated with neutral signals and degraded flag
            self.assertEqual(fake_item.fit_tightness, "regular")
            self.assertEqual(fake_item.silhouette, "relaxed")
            self.assertTrue(fake_item.tryon_degraded)
            mock_db.commit.assert_called()
        finally:
            app.dependency_overrides.clear()

    @patch("app.routers.candidates.find_near_duplicate")
    @patch("app.routers.candidates.upsert_wardrobe_embedding")
    @patch("app.routers.candidates.generate_embedding")
    @patch("app.routers.candidates.generate_tryon")
    @patch("app.routers.candidates.analyze_image")
    @patch("app.routers.candidates.upload_image")
    @patch("app.routers.candidates._stream_to_temp")
    @patch("app.routers.candidates._file_is_allowed")
    def test_candidate_intake_succeeds_during_youcam_outage(
        self,
        mock_file_allowed,
        mock_stream_temp,
        mock_upload_image,
        mock_analyze_image,
        mock_generate_tryon,
        mock_generate_embedding,
        mock_upsert_embedding,
        mock_find_duplicate,
    ):
        """Candidate intake completes cleanly with tryon_degraded=True when YouCam fails."""
        mock_file_allowed.return_value = True
        mock_stream_temp.return_value = ("/tmp/dummy.jpg", 1024)
        mock_upload_image.return_value = {
            "url": "https://res.cloudinary.com/test/candidate.jpg",
            "public_id": "verdict/candidates/user_m33_intake/abc",
        }
        mock_analyze_image.return_value = {
            "category": "top",
            "color": "navy",
            "pattern": "solid",
            "style": "classic",
            "season": "all-season",
            "material": "cotton",
        }
        mock_generate_tryon.side_effect = TryOnConnectionError("Failed to connect to YouCam server")
        mock_generate_embedding.return_value = [0.1] * 512
        mock_find_duplicate.return_value = None

        mock_owner = User(id=80, firebase_uid="user_m33_intake", email="intake@example.com")

        mock_db = MagicMock()
        mock_db.query().filter().first.return_value = mock_owner

        mock_file = MagicMock()
        mock_file.filename = "candidate_shirt.jpg"
        mock_file.content_type = "image/jpeg"
        mock_user = {"uid": "user_m33_intake", "email": "intake@example.com"}

        from app.routers.candidates import evaluate_candidate_item

        response = asyncio.run(
            evaluate_candidate_item(
                file=mock_file,
                price="45.00",
                user=mock_user,
                db=mock_db,
            )
        )

        self.assertIn("candidate_item_id", response)
        self.assertIsNotNone(response["tryon"])
        self.assertTrue(response["tryon"]["tryon_degraded"])
        self.assertEqual(response["tryon"]["fit_tightness"], "regular")
        self.assertEqual(response["tryon"]["silhouette"], "relaxed")
        self.assertIn("tryon", response.get("errors", {}))

    def test_full_buy_score_synthesis_with_degraded_tryon(self):
        """Full Decision Engine completes and produces Buy Score when tryon is degraded."""
        mock_candidate = MagicMock()
        mock_candidate.id = 901
        mock_candidate.user_id = 90
        mock_candidate.price = 50.0
        mock_candidate.fit_tightness = "regular"  # neutral fallback fit
        mock_candidate.silhouette = "relaxed"     # neutral fallback silhouette
        mock_candidate.tryon_degraded = True
        mock_candidate.duplicate_match_item_id = None
        mock_candidate.duplicate_similarity_pct = None

        mock_attrs = MagicMock()
        mock_attrs.category = "top"
        mock_attrs.color = "blue"
        mock_attrs.style = "classic"
        mock_attrs.season = "all-season"
        mock_attrs.material = "cotton"
        mock_candidate.attributes = mock_attrs

        mock_db = MagicMock()

        def mock_query(model):
            q = MagicMock()
            if model == WardrobeItem:
                q.filter.return_value.first.return_value = mock_candidate
                q.filter.return_value.all.return_value = [mock_candidate]
            else:
                q.filter.return_value.first.return_value = None
                q.filter.return_value.all.return_value = []
            return q

        mock_db.query.side_effect = mock_query

        # 1. Verify budget impact scorer specifically handles degraded candidate cleanly
        budget_score = score_budget_impact(901, mock_db)
        self.assertEqual(budget_score.axis, DecisionAxis.BUDGET_IMPACT)
        self.assertTrue(budget_score.raw_evidence.get("tryon_degraded"))
        self.assertGreater(budget_score.score, 0.0)

        # 2. Mock individual scorers or verify synthesize_buy_score directly
        with patch("app.decision_engine.orchestrator.score_versatility") as mock_v, \
             patch("app.decision_engine.orchestrator.score_redundancy") as mock_r, \
             patch("app.decision_engine.orchestrator.score_seasonal_relevance") as mock_s, \
             patch("app.decision_engine.orchestrator.score_style_alignment") as mock_sa, \
             patch("app.decision_engine.orchestrator.score_occasion_coverage") as mock_oc:

            mock_v.return_value = AxisScore(
                axis=DecisionAxis.VERSATILITY,
                score=75.0,
                reason="Pairs with 3 bottoms.",
                source_agent="outfit_composition",
            )
            mock_r.return_value = AxisScore(
                axis=DecisionAxis.REDUNDANCY,
                score=90.0,
                reason="Unique in wardrobe.",
                source_agent="duplicate_detection",
            )
            mock_s.return_value = AxisScore(
                axis=DecisionAxis.SEASONAL_RELEVANCE,
                score=80.0,
                reason="Suitable for current season.",
                source_agent="vision_agent",
            )
            mock_sa.return_value = AxisScore(
                axis=DecisionAxis.STYLE_ALIGNMENT,
                score=70.0,
                reason="Matches classic style.",
                source_agent="style_analysis",
            )
            mock_oc.return_value = AxisScore(
                axis=DecisionAxis.OCCASION_COVERAGE,
                score=65.0,
                reason="Covers casual occasions.",
                source_agent="occasion_analysis",
            )

            buy_score_result = synthesize_buy_score(901, mock_db, persist=True)

        self.assertIsNotNone(buy_score_result)
        self.assertEqual(buy_score_result.candidate_id, 901)
        self.assertIn(buy_score_result.verdict.lower(), ["buy", "consider", "skip"])
        self.assertTrue(buy_score_result.tryon_degraded)
        self.assertEqual(len(buy_score_result.axes), 6)
        self.assertIsNotNone(buy_score_result.confidence)
        self.assertIsNotNone(buy_score_result.summary_panel)

        # Verify DecisionLog was persisted with tryon_degraded = True
        mock_db.add.assert_called()
        persisted_log = mock_db.add.call_args[0][0]
        self.assertTrue(persisted_log.raw_payload["tryon_degraded"])


if __name__ == "__main__":
    unittest.main()
