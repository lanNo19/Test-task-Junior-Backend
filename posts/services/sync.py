"""
Sync service: fetches all media from Instagram and upserts into local DB.

This service only implements the business logic of syncing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import icontract

from posts.clients.instagram import InstagramClient

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Summary returned after a sync operation.

    Attributes:
        created: Number of new Post rows inserted.
        updated: Number of existing Post rows updated.
    """

    created: int
    updated: int

    @property
    def total(self) -> int:
        """Total media objects processed."""
        return self.created + self.updated


class SyncService:
    """Class for the full sync from Instagram to the local database.

    Args:
        client: A configured InstagramClient instance.
    """

    @icontract.require(
        lambda client: client is not None,
        description="client must not be None.",
    )
    def __init__(self, client: InstagramClient) -> None:
        self._client: InstagramClient = client

    @icontract.ensure(
        lambda result: result.created >= 0 and result.updated >= 0,
        description="created and updated counts must be non-negative.",
    )
    @icontract.ensure(
        lambda result: result.total == result.created + result.updated,
        description="total must equal created + updated.",
    )
    def sync_all(self) -> SyncResult:
        """Fetch all media from Instagram and upsert into local DB.

        Retrieves every media object the account has published, following
        pagination automatically (delegated to InstagramClient). Each item
        is upserted with Post.upsert(): new posts are created, existing ones
        are updated with fresh data.

        Returns:
            SyncResult with counts of created and updated posts.

        Raises:
            InstagramAPIError: inherited from InstagramClient if any API
                call fails. In that case no DB changes are made for the
                failed page, but previous pages may already be committed.
        """
        # to avoid circular imports
        from posts.models import Post

        logger.info("Starting full media sync.")
        media_list: list[dict[str, Any]] = self._client.fetch_all_media()

        created_count: int = 0
        updated_count: int = 0

        for media_data in media_list:
            _post, created = Post.upsert(media_data)
            if created:
                created_count += 1
            else:
                updated_count += 1

        result: SyncResult = SyncResult(created=created_count, updated=updated_count)
        logger.info(
            "Sync complete: %d created, %d updated, %d total.",
            result.created,
            result.updated,
            result.total,
        )
        return result