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

    async def list_spaces(
        self,
        *,
        page_no: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List all spaces with pagination."""
        return await self._client.request(
            "GET",
            "/v2.0/cloud/space",
            params={"page_no": page_no, "page_size": page_size},
        )

    async def create(
        self,
        *,
        name: str,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new space, optionally under a parent space."""
        body: dict[str, Any] = {"name": name}
        if parent_id is not None:
            body["parent_id"] = parent_id
        return await self._client.request(
            "POST", "/v2.0/cloud/space", body=body,
        )

    async def get_children(self, space_id: str) -> list[dict[str, Any]]:
        """Get child spaces of a given space."""
        return await self._client.request(
            "GET", f"/v2.0/cloud/space/{space_id}/children",
        )

    async def get_resources(self, space_id: str) -> list[dict[str, Any]]:
        """Get resources (devices, etc.) assigned to a space."""
        return await self._client.request(
            "GET", f"/v2.0/cloud/space/{space_id}/resources",
        )
