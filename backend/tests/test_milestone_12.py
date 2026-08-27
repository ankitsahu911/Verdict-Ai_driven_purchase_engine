"""
Unit and Integration Tests for Milestone 12: CLIP Vector Embeddings & ChromaDB.
"""

import math
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.chroma_service import (
    has_wardrobe_embedding,
    query_similar_items,
    upsert_wardrobe_embedding,
)
from app.services.embedding_service import EmbeddingServiceError, generate_embedding


class TestMilestone12Embeddings(unittest.TestCase):
    @patch("app.services.embedding_service.requests.get")
    @patch("app.services.embedding_service._get_model_and_processor")
    @patch("app.services.embedding_service.Image.open")
    def test_generate_embedding_normalization(self, mock_image_open, mock_get_model, mock_requests_get):
        """Test generate_embedding produces 512-dim normalized float list."""
        import torch

        mock_resp = MagicMock()
        mock_resp.content = b"fake_bytes"
        mock_requests_get.return_value = mock_resp

        mock_image = MagicMock()
        mock_image.convert.return_value = mock_image
        mock_image_open.return_value = mock_image

        mock_model = MagicMock()
        mock_processor = MagicMock()
        mock_get_model.return_value = (mock_model, mock_processor)

        # Mock processor output
        mock_processor.return_value = {"pixel_values": torch.zeros((1, 3, 224, 224))}

        # Raw non-normalized 512-dim tensor
        raw_features = torch.ones((1, 512)) * 2.0
        mock_model.get_image_features.return_value = raw_features

        vec = generate_embedding("https://dummy.com/image.jpg")

        self.assertEqual(len(vec), 512)
        # Verify L2 norm is ~1.0
        l2_norm = math.sqrt(sum(x * x for x in vec))
        self.assertAlmostEqual(l2_norm, 1.0, places=4)

    def test_generate_embedding_empty_path(self):
        """Test generate_embedding raises EmbeddingServiceError when path is empty."""
        with self.assertRaises(EmbeddingServiceError):
            generate_embedding("")

    @patch("app.services.chroma_service.get_wardrobe_collection")
    def test_upsert_and_has_embedding(self, mock_get_collection):
        """Test ChromaDB upserting and checking record existence."""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection
        mock_collection.get.return_value = {"ids": ["101"]}

        dummy_vector = [0.1] * 512
        upsert_wardrobe_embedding(item_id=101, user_id=1, category="outerwear", embedding=dummy_vector)

        mock_collection.upsert.assert_called_once_with(
            ids=["101"],
            embeddings=[dummy_vector],
            metadatas=[{"user_id": 1, "category": "outerwear"}],
        )

        exists = has_wardrobe_embedding(101)
        self.assertTrue(exists)

    @patch("app.services.chroma_service.get_wardrobe_collection")
    def test_query_similar_items(self, mock_get_collection):
        """Test querying nearest-neighbor vectors with metadata filtering."""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection
        mock_collection.query.return_value = {
            "ids": [["102", "103"]],
            "distances": [[0.15, 0.42]],
            "metadatas": [[{"user_id": 1, "category": "top"}, {"user_id": 1, "category": "top"}]],
        }

        dummy_vector = [0.1] * 512
        matches = query_similar_items(query_embedding=dummy_vector, top_k=2, user_id=1)

        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0]["id"], 102)
        self.assertAlmostEqual(matches[0]["distance"], 0.15, places=4)
        self.assertEqual(matches[0]["metadata"]["category"], "top")


if __name__ == "__main__":
    unittest.main()
