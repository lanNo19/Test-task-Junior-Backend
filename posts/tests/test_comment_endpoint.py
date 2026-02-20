"""
Integration tests for POST /api/posts/{pk}/comment/

Covers every row in the test table from design doc.
Uses Django's APIClient so the full stack (URL → View → Service → DB) runs.
All Instagram API calls are mocked: no real HTTP connections are made

Mock target: the InstagramClient as imported inside CommentService.
"""

from __future__ import annotations

from typing import Final
from unittest.mock import MagicMock, patch

from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase

from posts.exceptions import InstagramAPIError
from posts.models import Comment, Post
from posts.tests.factories import PostFactory

# Patch target: _make_client in views — controls which client all views receive.
_MOCK_MAKE_CLIENT: Final[str] = "posts.views._make_client"


class TestCommentEndpoint(APITestCase):
    """Integration tests for the comment creation endpoint.

    Each test corresponds to a row in design doc test table.
    """

    def setUp(self) -> None:
        """Create a real Post in the test DB for tests that need one."""
        self.post: Post = PostFactory()
        self.url: str = reverse("posts:comment-create", kwargs={"pk": self.post.pk})
        self.valid_payload: dict[str, str] = {"text": "Great shot!"}

    # ------------------------------------------------------------------
    # T1: Successful comment creation
    # ------------------------------------------------------------------

    def test_comment_success_returns_201(self) -> None:
        """T1a: Successful request returns HTTP 201."""
        with patch(_MOCK_MAKE_CLIENT) as mock_make:
            mock_client: MagicMock = MagicMock()
            mock_client.publish_comment.return_value = "ig_comment_99"
            mock_make.return_value = mock_client

            resp: Response = self.client.post(
                self.url, self.valid_payload, format="json"
            )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_comment_success_creates_db_record(self) -> None:
        """T1b: Successful request creates exactly one Comment in the DB."""
        with patch(_MOCK_MAKE_CLIENT) as mock_make:
            mock_client: MagicMock = MagicMock()
            mock_client.publish_comment.return_value = "ig_comment_99"
            mock_make.return_value = mock_client

            self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(Comment.objects.count(), 1)
        comment: Comment = Comment.objects.get()
        self.assertEqual(comment.post_id, self.post.pk)
        self.assertEqual(comment.text, "Great shot!")
        self.assertEqual(comment.instagram_comment_id, "ig_comment_99")

    def test_comment_success_response_body(self) -> None:
        """T1c: Response body contains the expected fields."""
        with patch(_MOCK_MAKE_CLIENT) as mock_make:
            mock_client: MagicMock = MagicMock()
            mock_client.publish_comment.return_value = "ig_comment_99"
            mock_make.return_value = mock_client

            resp: Response = self.client.post(
                self.url, self.valid_payload, format="json"
            )

        data: dict = resp.json()
        self.assertEqual(data["instagram_comment_id"], "ig_comment_99")
        self.assertEqual(data["text"], "Great shot!")
        self.assertEqual(data["post"], self.post.pk)
        self.assertIn("id", data)
        self.assertIn("created_at", data)

    def test_comment_calls_instagram_with_correct_args(self) -> None:
        """T1d: The client is called with the post's instagram_id and the text."""
        with patch(_MOCK_MAKE_CLIENT) as mock_make:
            mock_client: MagicMock = MagicMock()
            mock_client.publish_comment.return_value = "ig_comment_99"
            mock_make.return_value = mock_client

            self.client.post(self.url, self.valid_payload, format="json")

        mock_client.publish_comment.assert_called_once_with(
            self.post.instagram_id, "Great shot!"
        )

    # ------------------------------------------------------------------
    # T2: Post not found in local DB
    # ------------------------------------------------------------------

    def test_post_not_found_returns_404(self) -> None:
        """T2a: Non-existent post pk returns 404."""
        non_existent_url: str = reverse(
            "posts:comment-create", kwargs={"pk": 99999}
        )
        resp: Response = self.client.post(
            non_existent_url, self.valid_payload, format="json"
        )

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_not_found_creates_no_comment(self) -> None:
        """T2b: 404 response leaves DB unchanged."""
        non_existent_url: str = reverse(
            "posts:comment-create", kwargs={"pk": 99999}
        )
        self.client.post(non_existent_url, self.valid_payload, format="json")

        self.assertEqual(Comment.objects.count(), 0)

    # ------------------------------------------------------------------
    # T3: Post exists locally but Instagram rejects the comment
    # ------------------------------------------------------------------

    def test_instagram_api_error_returns_502(self) -> None:
        """T3a: Instagram API failure returns 502 Bad Gateway."""
        with patch(_MOCK_MAKE_CLIENT) as mock_make:
            mock_client: MagicMock = MagicMock()
            mock_client.publish_comment.side_effect = InstagramAPIError(
                status_code=404,
                detail="Media not found.",
            )
            mock_make.return_value = mock_client

            resp: Response = self.client.post(
                self.url, self.valid_payload, format="json"
            )

        self.assertEqual(resp.status_code, status.HTTP_502_BAD_GATEWAY)

    def test_instagram_api_error_creates_no_comment(self) -> None:
        """T3b: Instagram API failure leaves DB unchanged — no partial writes."""
        with patch(_MOCK_MAKE_CLIENT) as mock_make:
            mock_client: MagicMock = MagicMock()
            mock_client.publish_comment.side_effect = InstagramAPIError(
                status_code=404,
                detail="Media not found.",
            )
            mock_make.return_value = mock_client

            self.client.post(self.url, self.valid_payload, format="json")

        self.assertEqual(Comment.objects.count(), 0)

    def test_instagram_timeout_returns_502(self) -> None:
        """T3c: Network timeout is also surfaced as 502."""
        with patch(_MOCK_MAKE_CLIENT) as mock_make:
            mock_client: MagicMock = MagicMock()
            mock_client.publish_comment.side_effect = InstagramAPIError(
                status_code="timeout",
                detail="Request to Instagram timed out.",
            )
            mock_make.return_value = mock_client

            resp: Response = self.client.post(
                self.url, self.valid_payload, format="json"
            )

        self.assertEqual(resp.status_code, status.HTTP_502_BAD_GATEWAY)

    # ------------------------------------------------------------------
    # T4 & T5: Input validation
    # ------------------------------------------------------------------

    def test_empty_text_returns_400(self) -> None:
        """T4: Empty string text is rejected with 400."""
        resp: Response = self.client.post(self.url, {"text": ""}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("text", resp.json())

    def test_missing_text_returns_400(self) -> None:
        """T5: Missing text field is rejected with 400."""
        resp: Response = self.client.post(self.url, {}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("text", resp.json())

    def test_text_exceeding_2200_chars_returns_400(self) -> None:
        """T5b: Text exceeding Instagram's 2200-char limit is rejected."""
        resp: Response = self.client.post(
            self.url, {"text": "x" * 2201}, format="json"
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("text", resp.json())