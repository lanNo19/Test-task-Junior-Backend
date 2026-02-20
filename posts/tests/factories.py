"""
Test data factories.

Uses factory_boy to generate realistic Post and Comment instances
without requiring real Instagram API calls. Every test that needs
a persisted post or comment should use these factories.
"""

from __future__ import annotations

from typing import ClassVar

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from posts.models import Comment, Post


class PostFactory(DjangoModelFactory):
    """Creates a persisted Post instance with sensible defaults.

    Usage:
        post = PostFactory()                          # one post
        posts = PostFactory.create_batch(10)          # ten posts
        post = PostFactory(caption="Custom caption")  # override field
    """

    class Meta:
        model = type[Post]

    instagram_id: ClassVar[factory.Sequence] = factory.Sequence(
        lambda n: f"ig_post_{n:06d}"
    )
    caption: ClassVar[factory.Faker] = factory.Faker("sentence", nb_words=8)
    media_type: ClassVar[str] = Post.MediaType.IMAGE
    media_url: ClassVar[factory.LazyAttribute] = factory.LazyAttribute(
        lambda o: f"https://cdn.instagram.com/media/{o.instagram_id}.jpg"
    )
    permalink: ClassVar[factory.LazyAttribute] = factory.LazyAttribute(
        lambda o: f"https://www.instagram.com/p/{o.instagram_id}/"
    )
    timestamp: ClassVar[factory.LazyFunction] = factory.LazyFunction(timezone.now)
    synced_at: ClassVar[factory.LazyFunction] = factory.LazyFunction(timezone.now)


class CommentFactory(DjangoModelFactory):
    """Creates a persisted Comment instance linked to a Post.

    Usage:
        comment = CommentFactory()
        comment = CommentFactory(post=my_post, text="Custom text")
    """

    class Meta:
        model = type[Comment]

    post: ClassVar[factory.SubFactory] = factory.SubFactory(PostFactory)
    instagram_comment_id: ClassVar[factory.Sequence] = factory.Sequence(
        lambda n: f"ig_comment_{n:06d}"
    )
    text: ClassVar[factory.Faker] = factory.Faker("sentence", nb_words=5)