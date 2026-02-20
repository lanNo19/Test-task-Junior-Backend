"""
Unit tests for InstagramClient.

Covers design doc test table
All HTTP is mocked, no real network calls are made.
"""

from __future__ import annotations

from typing import Any, Final
from unittest.mock import MagicMock, patch

import icontract
import pytest

from posts.clients.instagram import InstagramClient
from posts.exceptions import InstagramAPIError

# Shared valid constructor args — reused across tests.
_VALID_TOKEN: Final[str] = "test_token"
_VALID_USER_ID: Final[str] = "123456"
_VALID_API_VERSION: Final[str] = "v21.0"


def _make_client() -> InstagramClient:
    """Build a valid InstagramClient for use in tests."""
    return InstagramClient(
        access_token=_VALID_TOKEN,
        user_id=_VALID_USER_ID,
        api_version=_VALID_API_VERSION,
    )


def _ok_response(data: dict[str, Any]) -> MagicMock:
    """Build a mock successful HTTP response."""
    mock: MagicMock = MagicMock()
    mock.ok = True
    mock.json.return_value = data
    return mock


def _error_response(status_code: int, message: str) -> MagicMock:
    """Build a mock failed HTTP response."""
    mock: MagicMock = MagicMock()
    mock.ok = False
    mock.status_code = status_code
    mock.json.return_value = {"error": {"message": message}}
    return mock


# ---------------------------------------------------------------------------
# fetch_all_media — table-driven
# ---------------------------------------------------------------------------

class TestFetchAllMedia:
    """U1–U4: fetch_all_media pagination and error handling."""

    def test_single_page_no_next(self) -> None:
        """U1: Single page with no 'next' cursor returns all items."""
        client: InstagramClient = _make_client()
        fake_response: MagicMock = _ok_response({
            "data": [{"id": "1"}, {"id": "2"}],
            "paging": {},
        })

        with patch.object(client._session, "get", return_value=fake_response) as mock_get:
            result: list[dict[str, Any]] = client.fetch_all_media()

        assert len(result) == 2
        assert mock_get.call_count == 1

    def test_two_pages_concatenated(self) -> None:
        """U2: Two pages are fetched and concatenated into one list."""
        client: InstagramClient = _make_client()
        page1: MagicMock = _ok_response({
            "data": [{"id": "1"}, {"id": "2"}],
            "paging": {"next": "https://graph.instagram.com/v21.0/123456/media?after=cursor1"},
        })
        page2: MagicMock = _ok_response({
            "data": [{"id": "3"}],
            "paging": {},
        })

        with patch.object(client._session, "get", side_effect=[page1, page2]) as mock_get:
            result: list[dict[str, Any]] = client.fetch_all_media()

        assert len(result) == 3
        assert [r["id"] for r in result] == ["1", "2", "3"]
        assert mock_get.call_count == 2

    def test_401_raises_instagram_api_error(self) -> None:
        """U3: HTTP 401 raises InstagramAPIError."""
        client: InstagramClient = _make_client()
        fake_response: MagicMock = _error_response(401, "Invalid token.")

        with patch.object(client._session, "get", return_value=fake_response):
            with pytest.raises(InstagramAPIError) as exc_info:
                client.fetch_all_media()

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail

    def test_500_on_second_page_raises_instagram_api_error(self) -> None:
        """U4: HTTP 500 on page 2 raises InstagramAPIError."""
        client: InstagramClient = _make_client()
        page1: MagicMock = _ok_response({
            "data": [{"id": "1"}],
            "paging": {"next": "https://graph.instagram.com/next"},
        })
        page2: MagicMock = _error_response(500, "Internal error.")

        with patch.object(client._session, "get", side_effect=[page1, page2]):
            with pytest.raises(InstagramAPIError) as exc_info:
                client.fetch_all_media()

        assert exc_info.value.status_code == 500

    def test_empty_data_field(self) -> None:
        """Edge: Response with empty 'data' array returns empty list."""
        client: InstagramClient = _make_client()
        fake_response: MagicMock = _ok_response({"data": [], "paging": {}})

        with patch.object(client._session, "get", return_value=fake_response):
            result: list[dict[str, Any]] = client.fetch_all_media()

        assert result == []


# ---------------------------------------------------------------------------
# publish_comment — table-driven
# ---------------------------------------------------------------------------

class TestPublishComment:
    """C1–C3: publish_comment success and error handling."""

    def test_success_returns_comment_id(self) -> None:
        """C1: HTTP 200 returns the comment ID string."""
        client: InstagramClient = _make_client()
        fake_response: MagicMock = _ok_response({"id": "ig_comment_abc"})

        with patch.object(client._session, "post", return_value=fake_response):
            result: str = client.publish_comment(media_id="media_1", text="Hello!")

        assert result == "ig_comment_abc"

    def test_403_raises_instagram_api_error(self) -> None:
        """C2: HTTP 403 (comments disabled) raises InstagramAPIError."""
        client: InstagramClient = _make_client()
        fake_response: MagicMock = _error_response(
            403, "Comments are disabled for this media."
        )

        with patch.object(client._session, "post", return_value=fake_response):
            with pytest.raises(InstagramAPIError) as exc_info:
                client.publish_comment(media_id="media_1", text="Hello!")

        assert exc_info.value.status_code == 403

    def test_404_raises_instagram_api_error(self) -> None:
        """C3: HTTP 404 (media deleted upstream) raises InstagramAPIError."""
        client: InstagramClient = _make_client()
        fake_response: MagicMock = _error_response(404, "Media not found.")

        with patch.object(client._session, "post", return_value=fake_response):
            with pytest.raises(InstagramAPIError) as exc_info:
                client.publish_comment(media_id="media_1", text="Hello!")

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------------

class TestInstagramClientConstruction:
    """Verifies icontract preconditions on __init__."""

    def test_empty_token_raises_violation(self) -> None:
        """Empty access_token violates the icontract precondition."""
        with pytest.raises(icontract.ViolationError):
            InstagramClient(access_token="", user_id="123")

    def test_empty_user_id_raises_violation(self) -> None:
        """Empty user_id violates the icontract precondition."""
        with pytest.raises(icontract.ViolationError):
            InstagramClient(access_token="token", user_id="")