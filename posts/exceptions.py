"""
Exceptions for the posts app.

These are raised by the service/client layer and translated to
HTTP responses in views. Not in views.py is for decoupling
from HTTP.
"""


class PostNotFound(Exception):
    """Raised when a Post primary key does not exist in the local DB.

    Args:
        pk: primary key that was looked up.
    """

    def __init__(self, pk: int) -> None:
        self.pk = pk
        super().__init__(f"Post with pk={pk} not found in local database.")


class InstagramAPIError(Exception):
    """Raised when the Instagram Graph API returns not 200s response.

    Args:
        status_code: HTTP status code (int) or a short string for network-level errors.
        detail: Human-readable message from the API error body.
    """

    def __init__(self, status_code: int | str, detail: str = "") -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Instagram API error [{status_code}]: {detail}")