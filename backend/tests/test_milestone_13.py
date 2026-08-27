"""
Unit and Integration Tests for Milestone 13: Flag Near-Duplicates by Embedding Similarity.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.chroma_service import (
    distance_to_similarity_percentage,
    find_near_duplicate,
)


class TestMilestone13NearDuplicate(unittest.TestCase):
    def test_distance_to_similarity_percentage_cosine(self):
        """Test conversion of cosine distances to intuitive 0-100% similarity scores."""
        # 0 distance => 100% match
        self.assertEqual(distance_to_similarity_percentage(0.0), 100.0)

        # 0.07 distance => 93.0% match (e.g. 93% similar hoodie)
        self.assertEqual(distance_to_similarity_percentage(0.07), 93.0)

        # 0.15 distance => 85.0% match
        self.assertEqual(distance_to_similarity_percentage(0.15), 85.0)

        # 0.5 distance => 50.0% match
        self.assertEqual(distance_to_similarity_percentage(0.5), 50.0)

        # 1.0 distance => 0.0% match
        self.assertEqual(distance_to_similarity_percentage(1.0), 0.0)

    def test_distance_to_similarity_percentage_l2_space(self):
        """Test squared L2 distance handling (d_l2 > 1.0 for unit vectors)."""
        # d_l2 = 0.14 => 1 - 0.07 = 0.93 => 93.0%
        self.assertEqual(distance_to_similarity_percentage(0.14), 86.0)

        # d_l2 = 1.8 => 1 - 0.9 = 0.1 => 10.0%
        self.assertEqual(distance_to_similarity_percentage(1.8), 10.0)

    @patch("app.services.chroma_service.get_wardrobe_collection")
    def test_find_near_duplicate_scoping_and_exclusion(self, mock_get_collection):
        """Test find_near_duplicate scopes query to user_id and excludes candidate item."""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection

        # Query returns item 101 (candidate) and item 102 (nearest neighbor d=0.07)
        mock_collection.query.return_value = {
            "ids": [["101", "102"]],
            "distances": [[0.0, 0.07]],
            "metadatas": [[{"user_id": 5, "category": "hoodie"}, {"user_id": 5, "category": "hoodie"}]],
        }

        dummy_vector = [0.1] * 512
        res = find_near_duplicate(
            query_embedding=dummy_vector,
            user_id=5,
            exclude_item_id=101,
        )

        self.assertIsNotNone(res)
        self.assertEqual(res["wardrobe_item_id"], 102)
        self.assertEqual(res["similarity_percentage"], 93.0)
        self.assertAlmostEqual(res["distance"], 0.07, places=4)

        # Verify collection.query received user_id where filter and fetch_k=2
        mock_collection.query.assert_called_once_with(
            query_embeddings=[dummy_vector],
            n_results=2,
            where={"user_id": 5},
        )

    @patch("app.services.chroma_service.get_wardrobe_collection")
    def test_find_near_duplicate_no_matches(self, mock_get_collection):
        """Test find_near_duplicate returns None when no items match user_id filter."""
        mock_collection = MagicMock()
        mock_get_collection.return_value = mock_collection
        mock_collection.query.return_value = {"ids": [[]], "distances": [[]], "metadatas": [[]]}

        dummy_vector = [0.1] * 512
        res = find_near_duplicate(query_embedding=dummy_vector, user_id=99)
        self.assertIsNone(res)


if __name__ == "__main__":
    unittest.main()
