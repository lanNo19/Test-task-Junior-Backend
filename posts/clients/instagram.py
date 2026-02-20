"""
Instagram Graph API client.

This module is an only place in code that knows about:
  - The Graph API base URL and versioning.
  - HTTP request mechanics (sessions, timeouts, retries).
  - Pagination (following 'next' cursors until exhausted).
  - Translating HTTP errors into domain exceptions.

Callers never see requests.Session, pagination cursors, or raw HTTP status codes.

Public interface:
  client.fetch_all_media(fields)       -> list[dict]
  client.publish_comment(media_id, text) -> str
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar, Final

import icontract
import requests

from posts.exceptions import InstagramAPIError

logger = logging.getLogger(__name__)


DEFAULT_MEDIA_FIELDS: Final[list[str]] = [
    "id",
    "caption",
    "media_type",
    "media_url",
    "permalink",
    "timestamp",
]


class InstagramClient:
    """HTTP client for the Instagram Graph API.

    Wraps all outbound calls to Instagram so that the rest of the application
    is entirely decoupled from HTTP concerns.

    Args:
        access_token: Long-lived Graph API access token.
        user_id: Numeric Instagram user ID
        api_version: Graph API version string
        timeout: Request timeout in seconds. Applied to every API call
    """

    BASE_URL: ClassVar[Final[str]] = "https://graph.instagram.com"

    @icontract.require(lambda access_token: len(access_token) > 0,
                       description="access_token must not be empty.")
    @icontract.require(lambda user_id: len(user_id) > 0,
                       description="user_id must not be empty.")
    def __init__(
        self,
        access_token: str,
        user_id: str,
        api_version: str = "v21.0",
        timeout: int = 30,
    ) -> None:
        self._token: str = access_token
        self._user_id: str = user_id
        self._api_version: str = api_version
        self._timeout: int = timeout

        # Reuse a session for connection pooling across paginated calls.
        self._session: requests.Session = requests.Session()
        self._session.params = {"access_token": self._token}  # type: ignore[assignment]


    @icontract.ensure(lambda result: isinstance(result, list),
                      description="must return a list.")
    def fetch_all_media(
        self,
        fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch every media object for the account, following all pages.

        Automatically follows 'pagination.next' cursors until the API
        returns no further pages.

        Args:
            fields: List of Graph API field names to request per media node.
                    Defaults to DEFAULT_MEDIA_FIELDS.

        Returns:
            A list of raw media dicts, one per Instagram media object.
            Empty list if the account has no media.

        Raises:
            InstagramAPIError: If any page request returns a not 200s response or a network error occurs.
        """
        resolved_fields: list[str] = fields or DEFAULT_MEDIA_FIELDS
        url: str = f"{self.BASE_URL}/{self._api_version}/{self._user_id}/media"
        params: dict[str, str] = {"fields": ",".join(resolved_fields)}

        all_media: list[dict[str, Any]] = []
        page: int = 0

        while url:
            page += 1
            logger.debug("Fetching media page %d from %s", page, url)
            data: dict[str, Any] = self._get(url, params=params)

            items: list[dict[str, Any]] = data.get("data", [])
            all_media.extend(items)
            logger.info("Page %d: received %d media items.", page, len(items))

            # Follow the next cursor; stop when there is none.
            url = data.get("paging", {}).get("next", "")
            # The next URL already contains all query parameters.
            params = {}

        logger.info("fetch_all_media complete: %d total items.", len(all_media))
        return all_media

    @icontract.require(lambda media_id: len(media_id) > 0,
                       description="media_id must not be empty.")
    @icontract.require(lambda text: 1 <= len(text) <= 2200,
                       description="text must be between 1 and 2200 characters.")
    @icontract.ensure(lambda result: len(result) > 0,
                      description="returned comment id must be non-empty.")
    def publish_comment(self, media_id: str, text: str) -> str:
        """Post a text comment to an Instagram media object.

        Args:
            media_id: The Instagram media ID (instagram_id on the Post model).
            text: Comment text. Must be 1–2200 characters.

        Returns:
            The instagram_comment_id string assigned by the API.

        Raises:
            InstagramAPIError: If the Graph API rejects the request (e.g.
                media deleted, comments disabled, token invalid).
        """
        url: str = f"{self.BASE_URL}/{self._api_version}/{media_id}/comments"
        logger.debug("Publishing comment to media %s", media_id)

        response_data: dict[str, Any] = self._post(url, json_body={"message": text})
        comment_id: str = response_data["id"]
        logger.info("Comment published: instagram_comment_id=%s", comment_id)
        return comment_id


    def _get(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Execute a GET request and return the parsed JSON body.

        Raises:
            InstagramAPIError: On non-200s status or network failure.
        """
        try:
            response: requests.Response = self._session.get(
                url, params=params, timeout=self._timeout
            )
        except requests.exceptions.Timeout:
            raise InstagramAPIError("timeout", "Request to Instagram timed out.")
        except requests.exceptions.ConnectionError as exc:
            raise InstagramAPIError("connection_error", str(exc))

        return self._parse_response(response)

    def _post(
        self,
        url: str,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a POST request and return the parsed JSON body.

        Raises:
            InstagramAPIError: On non-2xx status or network failure.
        """
        try:
            response: requests.Response = self._session.post(
                url, json=json_body, timeout=self._timeout
            )
        except requests.exceptions.Timeout:
            raise InstagramAPIError("timeout", "Request to Instagram timed out.")
        except requests.exceptions.ConnectionError as exc:
            raise InstagramAPIError("connection_error", str(exc))

        return self._parse_response(response)

    @staticmethod
    def _parse_response(response: requests.Response) -> dict[str, Any]:
        """Parse a Graph API response, raising InstagramAPIError on failure.

        The Graph API returns error details in the JSON body even if 400/500 is sent,
        so we always attempt JSON parsing before raising.

        Raises:
            InstagramAPIError: If HTTP status is not 2xx.
        """
        try:
            body: dict[str, Any] = response.json()
        except ValueError:
            body = {}

        if not response.ok:
            error: dict[str, Any] = body.get("error", {})
            detail: str = error.get("message", response.text[:200])
            logger.error(
                "Instagram API error: status=%d detail=%s",
                response.status_code,
                detail,
            )
            raise InstagramAPIError(status_code=response.status_code, detail=detail)

        return body