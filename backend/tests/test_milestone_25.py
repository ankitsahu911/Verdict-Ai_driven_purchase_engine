import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.auth import get_current_user
from app.db import get_db
from app.models import User, WardrobeItem
from app.routers.what_if import enumerate_subsets
from verdict_backend.main import app


class TestMilestone25WhatIfEnumeration(unittest.TestCase):
    def setUp(self):
        self.mock_user = {
            "uid": "test_m25_uid",
            "email": "m25@example.com",
            "name": "Test M25 User",
        }
        app.dependency_overrides[get_current_user] = lambda: self.mock_user
        self.mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: self.mock_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_mathematical_subsets_enumeration(self):
        subsets_3 = enumerate_subsets([1, 2, 3])
        self.assertEqual(len(subsets_3), 8)
        self.assertEqual(subsets_3[0], [])
        self.assertIn([1], subsets_3)
        self.assertIn([1, 2], subsets_3)
        self.assertIn([1, 2, 3], subsets_3)

        subsets_4 = enumerate_subsets([10, 20, 30, 40])
        self.assertEqual(len(subsets_4), 16)
        self.assertEqual(subsets_4[0], [])
        self.assertEqual(subsets_4[-1], [10, 20, 30, 40])

        subsets_5 = enumerate_subsets([10, 20, 30, 40, 50])
        self.assertEqual(len(subsets_5), 32)
        self.assertEqual(subsets_5[0], [])
        self.assertEqual(subsets_5[-1], [10, 20, 30, 40, 50])

    def test_api_enumerate_4_items_generates_16_subsets(self):
        mock_owner = MagicMock()
        mock_owner.id = 42
        mock_owner.firebase_uid = "test_m25_uid"

        items = []
        for i in [101, 102, 103, 104]:
            item = MagicMock()
            item.id = i
            item.user_id = 42
            item.is_candidate = True
            items.append(item)

        with patch("app.routers.what_if.get_or_create_user", return_value=mock_owner):
            self.mock_db.query.return_value.filter.return_value.all.return_value = items

            response = self.client.post(
                "/api/what-if/enumerate",
                json={"item_ids": [101, 102, 103, 104]},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_items"], 4)
        self.assertEqual(data["total_subsets"], 16)
        self.assertEqual(len(data["subsets"]), 16)

        # First subset must be empty set
        self.assertEqual(data["subsets"][0]["size"], 0)
        self.assertEqual(data["subsets"][0]["item_ids"], [])
        self.assertEqual(data["subsets"][0]["subset_id"], "subset_1")

        # Last subset must contain all 4 items
        self.assertEqual(data["subsets"][-1]["size"], 4)
        self.assertEqual(data["subsets"][-1]["item_ids"], [101, 102, 103, 104])
        self.assertEqual(data["subsets"][-1]["subset_id"], "subset_16")

    def test_api_enumerate_enforces_min_3_items(self):
        mock_owner = MagicMock()
        mock_owner.id = 42
        with patch("app.routers.what_if.get_or_create_user", return_value=mock_owner):
            response = self.client.post(
                "/api/what-if/enumerate",
                json={"item_ids": [101, 102]},
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("between 3 and 5", response.json()["detail"])

    def test_api_enumerate_enforces_max_5_items(self):
        mock_owner = MagicMock()
        mock_owner.id = 42
        with patch("app.routers.what_if.get_or_create_user", return_value=mock_owner):
            response = self.client.post(
                "/api/what-if/enumerate",
                json={"item_ids": [101, 102, 103, 104, 105, 106]},
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("between 3 and 5", response.json()["detail"])

    def test_api_enumerate_ownership_check_foreign_item(self):
        mock_owner = MagicMock()
        mock_owner.id = 42

        item1 = MagicMock(id=101, user_id=42)
        item2 = MagicMock(id=102, user_id=42)
        item3 = MagicMock(id=103, user_id=999)  # Foreign item

        with patch("app.routers.what_if.get_or_create_user", return_value=mock_owner):
            self.mock_db.query.return_value.filter.return_value.all.return_value = [
                item1,
                item2,
                item3,
            ]

            response = self.client.post(
                "/api/what-if/enumerate",
                json={"item_ids": [101, 102, 103]},
            )

        self.assertEqual(response.status_code, 403)
        self.assertIn("do not have access", response.json()["detail"])

    def test_api_enumerate_missing_item_not_found(self):
        mock_owner = MagicMock()
        mock_owner.id = 42

        item1 = MagicMock(id=101, user_id=42)
        item2 = MagicMock(id=102, user_id=42)

        with patch("app.routers.what_if.get_or_create_user", return_value=mock_owner):
            self.mock_db.query.return_value.filter.return_value.all.return_value = [
                item1,
                item2,
            ]

            response = self.client.post(
                "/api/what-if/enumerate",
                json={"item_ids": [101, 102, 999]},
            )

        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
