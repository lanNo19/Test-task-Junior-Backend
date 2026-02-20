"""
Pagination configuration for the posts app.

CursorPagination is used for the post list endpoint.
"""

from rest_framework.pagination import CursorPagination


class PostCursorPagination(CursorPagination):
    """Cursor-based pagination for the Post list.

    Ordered with newest first, matching the Post model's default ordering.
    """

    page_size = 20
    ordering = "-timestamp"
    cursor_query_param = "cursor"