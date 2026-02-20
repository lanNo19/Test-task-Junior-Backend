"""
Integration tests for GET /api/posts/

Covers design doc test table.
"""

from __future__ import annotations

from typing import Any

from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

from posts.tests.factories import PostFactory


class TestPostListEndpoint(APITestCase):
    """Integration tests for the paginated post list endpoint."""

    def setUp(self) -> None:
        self.url: str = reverse("posts:post-list")

    def test_empty_db_returns_empty_results(self) -> None:
        """P1: No posts in DB returns empty results list."""
        resp: Response = self.client.get(self.url)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data: dict[str, Any] = resp.json()
        self.assertEqual(data["results"], [])
        self.assertIsNone(data["next"])

    def test_list_returns_correct_fields(self) -> None:
        """P1b: Each result contains the expected fields."""
        PostFactory()
        resp: Response = self.client.get(self.url)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        result: dict[str, Any] = resp.json()["results"][0]
        expected_fields: set[str] = {
            "id", "instagram_id", "caption", "media_type",
            "media_url", "permalink", "timestamp", "synced_at",
        }
        self.assertEqual(set(result.keys()), expected_fields)

    def test_25_posts_first_page_has_20(self) -> None:
        """P2: 25 posts → first page returns 20 results with a next cursor."""
        PostFactory.create_batch(25)
        resp: Response = self.client.get(self.url)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data: dict[str, Any] = resp.json()
        self.assertEqual(len(data["results"]), 20)
        self.assertIsNotNone(data["next"])

    def test_cursor_second_page_has_remaining(self) -> None:
        """P3: Following the cursor from page 1 returns the remaining 5 posts."""
        PostFactory.create_batch(25)

        page1: Response = self.client.get(self.url)
        next_url: str = page1.json()["next"]
        page2: Response = self.client.get(next_url)

        self.assertEqual(page2.status_code, status.HTTP_200_OK)
        data: dict[str, Any] = page2.json()
        self.assertEqual(len(data["results"]), 5)
        self.assertIsNone(data["next"])