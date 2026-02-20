"""URL patterns for the posts app.

Registered under /api/ in config/urls.py, so the full paths are:
  POST /api/sync/
  GET  /api/posts/
  POST /api/posts/<pk>/comment/
"""

from typing import Final

from django.urls import URLPattern, path

from posts.views import CommentView, PostListView, SyncView

app_name: Final[str] = "posts"

urlpatterns: Final[list[URLPattern]] = [
    path("sync/", SyncView.as_view(), name="sync"),
    path("posts/", PostListView.as_view(), name="post-list"),
    path("posts/<int:pk>/comment/", CommentView.as_view(), name="comment-create"),
]