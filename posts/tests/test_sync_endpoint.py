"""
Integration tests for POST /api/sync/

Covers design doc test table.
"""

from __future__ import annotations

from typing import Any, Final
from unittest.mock import MagicMock, patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

from posts.exceptions import InstagramAPIError
from posts.models import Post
from posts.tests.factories import PostFactory

_MOCK_MAKE_CLIENT: Final[str] = "posts.views._make_client"


def _make_media(n: int = 1) -> list[dict[str, Any]]:
    """Build n fake Instagram media API response dicts."""
    return [
        {
            "id": f"ig_{i:06d}",
            "caption": f"Caption {i}",
            "media_type": "IMAGE",
            "media_url": f"https://cdn.example.com/{i}.jpg",
            "permalink": f"https://www.instagram.com/p/{i}/",
            "timestamp": timezone.now().isoformat(),
        }
        for i in range(n)
    ]


class TestSyncEndpoint(APITestCase):
    """Integration tests for POST /api/sync/."""

    def setUp(self) -> None:
        self.url: str = reverse("posts:sync")

    def test_sync_creates_posts(self) -> None:
        """S1: Sync with 3 new media items creates 3 Post rows."""
        with patch(_MOCK_MAKE_CLIENT) as mock_make:
            mock_client: MagicMock = MagicMock()
            mock_client.fetch_all_media.return_value = _make_media(3)
            mock_make.return_value = mock_client

            resp: Response = self.client.post(self.url)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(Post.objects.count(), 3)
        self.assertEqual(resp.json(), {"created": 3, "updated": 0})

    def test_sync_updates_existing_post(self) -> None:
        """S2: Sync with an existing instagram_id updates, not duplicates."""
        existing: Post = PostFactory(instagram_id="ig_000000", caption="Old caption")
        media: list[dict[str, Any]] = _make_media(1)
        media[0]["id"] = "ig_000000"
        media[0]["caption"] = "New caption"

        with patch(_MOCK_MAKE_CLIENT) as mock_make:
            mock_client: MagicMock = MagicMock()
            mock_client.fetch_all_media.return_value = media
            mock_make.return_value = mock_client

            resp: Response = self.client.post(self.url)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(resp.json(), {"created": 0, "updated": 1})
        existing.refresh_from_db()
        self.assertEqual(existing.caption, "New caption")

    def test_sync_api_failure_returns_502(self) -> None:
        """S3: Instagram API error during sync returns 502."""
        with patch(_MOCK_MAKE_CLIENT) as mock_make:
            mock_client: MagicMock = MagicMock()
            mock_client.fetch_all_media.side_effect = InstagramAPIError(
                500, "Server error"
            )
            mock_make.return_value = mock_client

            resp: Response = self.client.post(self.url)

        self.assertEqual(resp.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(Post.objects.count(), 0)

    def test_sync_empty_account(self) -> None:
        """S4: Account with no media returns 200 with zeros."""
        with patch(_MOCK_MAKE_CLIENT) as mock_make:
            mock_client: MagicMock = MagicMock()
            mock_client.fetch_all_media.return_value = []
            mock_make.return_value = mock_client

            resp: Response = self.client.post(self.url)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json(), {"created": 0, "updated": 0})