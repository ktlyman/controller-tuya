"""Smart lock operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tuya_agent.client import TuyaClient


class LocksMixin:
    """Methods for smart lock control via the Tuya Smart Lock API."""

    def __init__(self, client: TuyaClient) -> None:
        self._client = client

    async def get_password_ticket(self, device_id: str) -> dict[str, Any]:
        """Request a temporary password ticket for door-lock operations."""
        return await self._client.request(
            "POST",
            f"/v1.0/devices/{device_id}/door-lock/password-ticket",
        )

    async def password_free_unlock(self, device_id: str) -> bool:
        """Trigger a password-free door open on a smart lock."""
        await self._client.request(
            "POST",
            f"/v1.0/devices/{device_id}/door-lock/password-free/open-door",
        )
        return True

    async def remote_unlock(self, device_id: str) -> bool:
        """Remote unlock via the smart-lock password-free API."""
        await self._client.request(
            "POST",
            f"/v1.0/smart-lock/devices/{device_id}/password-free/door-operate",
        )
        return True
