"""
Data models for the posts app.

Post  — local mirror of one Instagram media object (ADT §6.1).
Comment — a comment posted to Instagram, stored locally (ADT §6.2).
"""

from typing import Any, ClassVar, Final

import icontract
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from django.utils import timezone


class Post(models.Model):
    """Instagram media object.

    Fields are the same as in the Instagram Graph API media node. Once synced,
    all reads are served from this table and never from Instagram.

    Invariants:
        inv-1: instagram_id is unique across all Post rows (DB constraint).
        inv-2: timestamp <= synced_at.
        inv-3: media_type ∈ {IMAGE, VIDEO, CAROUSEL_ALBUM}.
    """

    class MediaType(models.TextChoices):
        IMAGE = "IMAGE", "Image"
        VIDEO = "VIDEO", "Video"
        CAROUSEL_ALBUM = "CAROUSEL_ALBUM", "Carousel Album"

    # Internal pk: exposed in /api/posts/ and used as {id} in comment url
    id = models.BigAutoField(primary_key=True)
    # Unique id assigned by Instagram. Used as the upsert key.
    instagram_id = models.CharField(max_length=64, unique=True, db_index=True)
    caption = models.TextField(blank=True, null=True)
    media_type = models.CharField(
        max_length=20,
        choices=MediaType.choices,
        default=MediaType.IMAGE,
    )
    # Presigned CDN url — may expire, so updated on every sync.
    media_url = models.URLField(max_length=2048, blank=True, null=True)
    permalink = models.URLField(max_length=2048)
    # Publication time on Instagram (from API response).
    timestamp = models.DateTimeField()
    # Time of the most recent local sync; updated on every upsert.
    synced_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Post"
        verbose_name_plural = "Posts"

    def __str__(self) -> str:
        return f"Post(id={self.pk}, instagram_id={self.instagram_id})"

    @classmethod
    @icontract.require(
        lambda data: "id" in data and "permalink" in data
                     and "timestamp" in data and "media_type" in data,
        description="data must contain keys: id, permalink, timestamp, media_type",
    )
    @icontract.ensure(
        lambda data, result: result[0].instagram_id == data["id"],
        description="returned post must have instagram_id matching data['id']",
    )
    def upsert(cls, data: dict[str, Any]) -> tuple["Post", bool]:
        """Create or update a Post from an Instagram API data payload.

        Implements upsert semantics: if a Post with the given instagram_id
        already exists, its fields are updated. Otherwise a new Post is created.

        Args:
            data: Raw dict from the Instagram Graph API media node.
                  Must contain keys: id, permalink, timestamp, media_type.

        Returns:
            Tuple of (post_instance, created) where created is True if a new
            row was inserted, False if an existing row was updated.
        """
        defaults: dict[str, Any] = {
            "caption": data.get("caption"),
            "media_type": data.get("media_type", cls.MediaType.IMAGE),
            "media_url": data.get("media_url"),
            "permalink": data["permalink"],
            "timestamp": data["timestamp"],
            "synced_at": timezone.now(),
        }
        post, created = cls.objects.update_or_create(
            instagram_id=data["id"],
            defaults=defaults,
        )
        return post, created


class Comment(models.Model):
    """A comment posted to Instagram, mirrored locally.

    Created ONLY after a successful publish_comment call to Instagram.
    The instagram_comment_id returned by the API is stored for auditability.

    Invariants:
        inv-1: 1 <= len(text) <= 2200 (enforced by validators + DB).
        inv-2: instagram_comment_id is non-empty.
        inv-3: post is a persisted Post (FK constraint, never null).
    """

    MAX_TEXT_LENGTH: ClassVar[Final[int]] = 2200

    @staticmethod
    def _validate_not_blank(value: str) -> None:
        """Reject strings that are empty or whitespace-only."""
        if not value.strip():
            raise DjangoValidationError(
                "Comment text cannot be blank or whitespace only."
            )

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    # id assigned by Instagram after successful comment creation.
    instagram_comment_id = models.CharField(max_length=64)
    text = models.TextField(
        blank=False,
        validators=[
            lambda v: Comment._validate_not_blank(v),
            MinLengthValidator(1),
            MaxLengthValidator(MAX_TEXT_LENGTH),
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Comment"
        verbose_name_plural = "Comments"

    def __str__(self) -> str:
        return f"Comment(id={self.pk}, post={self.post_id})"
