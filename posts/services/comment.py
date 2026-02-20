"""
Comment service: publishes a comment via Instagram API and saves it locally.

The sequence is:
  1. Verify the Post exists in local DB (raises PostNotFound if not).
  2. Call Instagram API (raises InstagramAPIError on failure).
  3. Persist the Comment locally.

This ordering ensures we never write to the DB unless Instagram confirms
the comment was accepted, and we never call Instagram for a non-existent post.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import icontract

from posts.clients.instagram import InstagramClient
from posts.exceptions import InstagramAPIError, PostNotFound  # noqa: F401 — re-exported

if TYPE_CHECKING:
    from posts.models import Comment

logger = logging.getLogger(__name__)


class CommentService:
    """Posts a comment to Instagram and records it in the local database.

    Args:
        client: A valid InstagramClient instance.
    """

    @icontract.require(
        lambda client: client is not None,
        description="client must not be None.",
    )
    def __init__(self, client: InstagramClient) -> None:
        self._client: InstagramClient = client

    @icontract.require(
        lambda post_pk: post_pk > 0,
        description="post_pk must be a positive integer.",
    )
    @icontract.require(
        lambda text: 1 <= len(text) <= 2200,
        description="text must be between 1 and 2200 characters.",
    )
    @icontract.ensure(
        lambda result: result.pk is not None,
        description="returned Comment must be persisted (pk must not be None).",
    )
    @icontract.ensure(
        lambda result, text: result.text == text,
        description="persisted Comment text must match the input text.",
    )
    def post_comment(self, post_pk: int, text: str) -> Comment:
        """Publish a comment and persist it locally.

        Args:
            post_pk: Internal primary key of the Post to comment on.
            text: Comment text.

        Returns:
            The newly created and persisted Comment instance.

        Raises:
            PostNotFound: If no Post with pk=post_pk exists in the DB.
            InstagramAPIError: If the Graph API rejects the comment request.
        """
        # Import inside method to avoid circular imports at runtime
        from posts.models import Comment, Post

        try:
            post: Post = Post.objects.get(pk=post_pk)
        except Post.DoesNotExist:
            logger.warning("post_comment called with non-existent pk=%d", post_pk)
            raise PostNotFound(pk=post_pk)

        logger.info(
            "Publishing comment to instagram_id=%s (local pk=%d)",
            post.instagram_id,
            post_pk,
        )
        instagram_comment_id: str = self._client.publish_comment(
            media_id=post.instagram_id,
            text=text,
        )

        comment: Comment = Comment.objects.create(
            post=post,
            instagram_comment_id=instagram_comment_id,
            text=text,
        )
        logger.info(
            "Comment saved locally: pk=%d instagram_comment_id=%s",
            comment.pk,
            instagram_comment_id,
        )
        return comment