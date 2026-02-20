"""
Views for the posts app.

These views handle HTTP mechanics only (routing, request parsing, serialization, and error mapping).
No business logic lives in this layer.

Error mapping contract:
    PostNotFound       -> 404
    InstagramAPIError  -> 502
    ValidationError    -> 400 (raised by DRF serializer automatically)
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from django.conf import settings
from django.db.models import QuerySet
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from posts.clients.instagram import InstagramClient
from posts.exceptions import InstagramAPIError, PostNotFound
from posts.models import Post
from posts.pagination import PostCursorPagination
from posts.serializers import CommentInputSerializer, CommentSerializer, PostSerializer
from posts.services.comment import CommentService
from posts.services.sync import SyncService, SyncResult

logger = logging.getLogger(__name__)


def _make_client() -> InstagramClient:
    """
    Build an InstagramClient from Django settings.

    Returns:
        A fully configured InstagramClient instance.
    """
    return InstagramClient(
        access_token=settings.INSTAGRAM_ACCESS_TOKEN,
        user_id=settings.INSTAGRAM_USER_ID,
        api_version=settings.INSTAGRAM_API_VERSION,
    )


class SyncView(APIView):
    """POST /api/sync/: pull all media from Instagram into local DB.

    Triggers a full account sync. Existing posts are updated (upsert).
    Returns counts of created and updated posts.

    Responses:
        200: Sync completed successfully.
        502: Instagram API returned an error.
    """

    def post(self, request: Request) -> Response:
        service: SyncService = SyncService(client=_make_client())

        try:
            result: SyncResult = service.sync_all()
        except InstagramAPIError as exc:
            logger.error("Sync failed: %s", exc)
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {"created": result.created, "updated": result.updated},
            status=status.HTTP_200_OK,
        )


class PostListView(ListAPIView):
    """GET /api/posts/: list all locally cached posts with cursor pagination.

    Reads from local DB only; never calls Instagram.

    Responses:
        200: Paginated list of posts (cursor-based).
    """

    queryset: ClassVar[QuerySet[Post]] = Post.objects.all()
    serializer_class: ClassVar[type[PostSerializer]] = PostSerializer
    pagination_class: ClassVar[type[PostCursorPagination]] = PostCursorPagination


class CommentView(APIView):
    """POST /api/posts/{pk}/comment/: post a comment to Instagram.

    The {pk} is the internal Post primary key (not the Instagram media ID).

    Request body:
        { "text": "<comment text>" }

    Responses:
        201: Comment published and saved locally.
        400: Request body is invalid (missing or blank text).
        404: No Post with the given pk exists in the local DB.
        502: Post exists locally but Instagram rejected the comment.
    """

    def post(self, request: Request, pk: int) -> Response:
        # Step 1: validate input, raises 400 automatically on failure
        serializer: CommentInputSerializer = CommentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        text: str = serializer.validated_data["text"]

        # Step 2: delegate to service
        service: CommentService = CommentService(client=_make_client())

        try:
            comment: Any = service.post_comment(post_pk=pk, text=text)
        except PostNotFound:
            return Response(
                {"detail": f"Post with id={pk} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except InstagramAPIError as exc:
            logger.error("Failed to publish comment for post pk=%d: %s", pk, exc)
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Step 3: serialise and return the created comment
        return Response(
            CommentSerializer(comment).data,
            status=status.HTTP_201_CREATED,
        )