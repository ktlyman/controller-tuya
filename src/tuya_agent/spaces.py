"""Space (location) resolution operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tuya_agent.client import TuyaClient


class SpacesMixin:
    """Methods for resolving Tuya spaces (locations)."""

    def __init__(self, client: TuyaClient) -> None:
        self._client = client

    async def get(self, space_id: str) -> dict[str, Any]:
        """Get details for a space including its name and hierarchy."""
        return await self._client.request(
            "GET", f"/v2.0/cloud/space/{space_id}",
        )
