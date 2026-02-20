"""
DRF serializers for the posts app.

PostSerializer: read-only representation of a cached Instagram post.
CommentInputSerializer: validates the request body for comment creation.
CommentSerializer: read representation of a persisted comment.
"""

from typing import Any, ClassVar

from rest_framework import serializers

from posts.models import Comment, Post


class PostSerializer(serializers.ModelSerializer):
    """Read-only serializer for the Post model.

    Used by GET /api/posts/ to render cached Instagram media objects.
    All fields are read-only; posts are created only by the sync endpoint.
    """

    class Meta:
        model = type[Post]
        fields: ClassVar[list[str]] = [
            "id",
            "instagram_id",
            "caption",
            "media_type",
            "media_url",
            "permalink",
            "timestamp",
            "synced_at",
        ]
        read_only_fields: ClassVar[list[str]] = fields


class CommentInputSerializer(serializers.Serializer):
    """Validates the request body for POST /api/posts/{id}/comment/.

    Input-only serializer. Does not use ModelSerializer here because
    the 'text' validation (non-empty, ≤2200 chars) is better
    stated explicitly and decoupled from the model instance lifecycle.
    """

    text: serializers.CharField = serializers.CharField(
        min_length=1,
        max_length=Comment.MAX_TEXT_LENGTH,
        trim_whitespace=False,
        error_messages={
            "blank": "Comment text may not be blank.",
            "max_length": (
                f"Comment text may not exceed {Comment.MAX_TEXT_LENGTH} characters."
            ),
        },
    )

    def validate_text(self, value: str) -> str:
        """Explicit field validator for text.

        DRF calls this automatically after the field-level checks pass.
        Provides a clear hook for any future text-level rules
        without messing with the field definition.

        Args:
            value: The cleaned text string after DRF's own validation.

        Returns:
            The validated text unchanged.
        """
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Object-level validator, runs after all field validators pass.

        Currently a passthrough. The right place to add cross-field
        validation if the serializer grows more fields in future.

        Args:
            attrs: Dict of all validated field values.

        Returns:
            The attrs dict unchanged.
        """
        return attrs


class CommentSerializer(serializers.ModelSerializer):
    """Read serializer for a persisted Comment.

    Returned as the 201 response body after a successful comment creation.
    """

    class Meta:
        model = type[Comment]
        fields: ClassVar[list[str]] = [
            "id",
            "post",
            "instagram_comment_id",
            "text",
            "created_at",
        ]
        read_only_fields: ClassVar[list[str]] = fields