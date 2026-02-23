"""Device group operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tuya_agent.client import TuyaClient


class GroupsMixin:
    """Methods for managing device groups."""

    def __init__(self, client: TuyaClient) -> None:
        self._client = client

    async def list_groups(
        self,
        *,
        page_no: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List device groups with pagination."""
        return await self._client.request(
            "GET",
            "/v2.0/cloud/thing/group",
            params={"page_no": page_no, "page_size": page_size},
        )

    async def create(
        self,
        *,
        name: str,
        product_id: str,
        device_ids: list[str],
    ) -> dict[str, Any]:
        """Create a new device group."""
        return await self._client.request(
            "POST",
            "/v2.0/cloud/thing/group",
            body={
                "name": name,
                "product_id": product_id,
                "device_ids": device_ids,
            },
        )

    async def get(self, group_id: str) -> dict[str, Any]:
        """Get details of a device group."""
        return await self._client.request(
            "GET", f"/v2.0/cloud/thing/group/{group_id}",
        )

    async def list_devices(self, group_id: str) -> list[dict[str, Any]]:
        """List all devices in a group."""
        return await self._client.request(
            "GET", f"/v2.0/cloud/thing/group/{group_id}/devices",
        )

    async def delete(self, group_id: str) -> bool:
        """Delete a device group."""
        await self._client.request(
            "DELETE", f"/v2.0/cloud/thing/group/{group_id}",
        )
        return True
