"""
Property-based tests for the Comment model.

Uses Hypothesis to verify the text length invariants hold for arbitrary inputs.

According to design doc:
  Property: for all text where 1 <= len(text) <= 2200: Comment.full_clean() must not raise.
  Property: for all text where len(text) > 2200:        Comment.full_clean() must raise.
"""

from __future__ import annotations

from typing import Final

import pytest
from django.core.exceptions import ValidationError
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from posts.models import Comment
from posts.tests.factories import PostFactory

# Boundary constants — mirror the model's own MAX_TEXT_LENGTH.
# Defined here so tests read as specifications, not magic numbers.
_MAX_VALID_LENGTH: Final[int] = 2200
_MIN_OVER_LIMIT: Final[int] = _MAX_VALID_LENGTH + 1


@pytest.mark.django_db
class TestCommentTextInvariants:
    """Property-based verification of Comment.text length contract.

    Each test targets a distinct region of the input space:
      - Valid range:    1 <= len(text) <= 2200
      - Over limit:     len(text) > 2200
      - Boundary exact: len(text) == 2200  and  len(text) == 2201
      - Blank inputs:   empty / whitespace-only strings
    """

    @pytest.mark.django_db
    @given(text=st.text(min_size=1, max_size=_MAX_VALID_LENGTH))
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_valid_text_always_passes_validation(self, text: str) -> None:
        """For any text t where 1 <= len(t) <= 2200, full_clean must not raise."""
        post = PostFactory()
        comment: Comment = Comment(
            post=post, text=text, instagram_comment_id="fake_id"
        )
        comment.full_clean()

    @pytest.mark.django_db
    @given(text=st.text(min_size=_MIN_OVER_LIMIT, max_size=3000))
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_text_exceeding_limit_always_fails_validation(self, text: str) -> None:
        """For any text t where len(t) > 2200, full_clean must raise ValidationError."""
        post = PostFactory()
        comment: Comment = Comment(
            post=post, text=text, instagram_comment_id="fake_id"
        )
        with pytest.raises(ValidationError):
            comment.full_clean()

    @pytest.mark.parametrize("text", ["", " ", "\t", "\n"])
    def test_blank_text_fails_validation(self, text: str) -> None:
        """Boundary: empty or whitespace-only text raises ValidationError."""
        post = PostFactory()
        comment: Comment = Comment(
            post=post, text=text, instagram_comment_id="fake_id"
        )
        with pytest.raises(ValidationError):
            comment.full_clean()

    def test_exactly_max_length_passes(self) -> None:
        """Boundary: exactly 2200 characters is valid (inclusive upper bound)."""
        post = PostFactory()
        comment: Comment = Comment(
            post=post,
            text="a" * _MAX_VALID_LENGTH,
            instagram_comment_id="fake_id",
        )
        comment.full_clean()

    def test_one_over_max_length_fails(self) -> None:
        """Boundary: 2201 characters exceeds the limit by exactly one."""
        post = PostFactory()
        comment: Comment = Comment(
            post=post,
            text="a" * _MIN_OVER_LIMIT,
            instagram_comment_id="fake_id",
        )
        with pytest.raises(ValidationError):
            comment.full_clean()