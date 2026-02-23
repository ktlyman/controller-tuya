"""Infrared (IR) control hub operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tuya_agent.client import TuyaClient


class IRMixin:
    """Methods for controlling IR blasters and their virtual remotes."""

    def __init__(self, client: TuyaClient) -> None:
        self._client = client

    async def list_categories(
        self, infrared_id: str,
    ) -> list[dict[str, Any]]:
        """List the device categories supported by an IR hub."""
        return await self._client.request(
            "GET", f"/v2.0/infrareds/{infrared_id}/categories",
        )

    async def list_remotes(
        self, infrared_id: str,
    ) -> list[dict[str, Any]]:
        """List virtual remotes configured on an IR hub."""
        return await self._client.request(
            "GET", f"/v2.0/infrareds/{infrared_id}/remotes",
        )

    async def get_remote_keys(
        self,
        infrared_id: str,
        remote_id: str,
    ) -> dict[str, Any]:
        """Get the available keys (buttons) for a virtual remote."""
        return await self._client.request(
            "GET",
            f"/v2.0/infrareds/{infrared_id}/remotes/{remote_id}/keys",
        )

    async def send_command(
        self,
        infrared_id: str,
        remote_id: str,
        *,
        key: str,
    ) -> bool:
        """Send a key-press command through an IR remote."""
        await self._client.request(
            "POST",
            f"/v2.0/infrareds/{infrared_id}/remotes/{remote_id}/command",
            body={"key": key},
        )
        return True

    async def save_learned_code(
        self,
        infrared_id: str,
        *,
        remote_name: str,
        category_id: str,
        key_name: str,
        code: str,
    ) -> dict[str, Any]:
        """Save a learned IR code to a new virtual remote."""
        return await self._client.request(
            "POST",
            f"/v2.0/infrareds/{infrared_id}/learning-codes",
            body={
                "remote_name": remote_name,
                "category_id": category_id,
                "key_name": key_name,
                "code": code,
            },
        )
