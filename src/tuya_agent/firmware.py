"""Product firmware management operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tuya_agent.client import TuyaClient


class FirmwareMixin:
    """Methods for querying and managing device firmware."""

    def __init__(self, client: TuyaClient) -> None:
        self._client = client

    async def get_info(self, device_id: str) -> list[dict[str, Any]]:
        """Get firmware version info and available upgrades for a device."""
        return await self._client.request(
            "GET", f"/v2.0/cloud/thing/{device_id}/firmware",
        )

    async def trigger_upgrade(self, device_id: str) -> bool:
        """Trigger an OTA firmware upgrade on a device.

        This is a potentially destructive operation — only call when
        explicitly requested.
        """
        await self._client.request(
            "POST", f"/v2.0/cloud/thing/{device_id}/firmware/upgrade",
        )
        return True
