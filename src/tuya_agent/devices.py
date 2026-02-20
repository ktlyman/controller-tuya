"""Device access and control operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tuya_agent.client import TuyaClient


class DevicesMixin:
    """Methods for listing, inspecting, and controlling Tuya devices."""

    def __init__(self, client: TuyaClient) -> None:
        self._client = client

    async def list(
        self,
        *,
        page_size: int = 20,
        last_row_key: str | None = None,
    ) -> dict[str, Any]:
        """List devices under the cloud project.

        Returns a dict with ``list`` (device records) and ``last_row_key``
        for pagination.
        """
        params: dict[str, Any] = {"size": page_size}
        if last_row_key:
            params["last_row_key"] = last_row_key
        return await self._client.request("GET", "/v2.0/cloud/thing/device", params=params)

    async def get(self, device_id: str) -> dict[str, Any]:
        """Get full details for a single device."""
        return await self._client.request("GET", f"/v1.0/devices/{device_id}")

    async def get_status(self, device_id: str) -> list[dict[str, Any]]:
        """Get the current data-point status of a device."""
        return await self._client.request(
            "GET", f"/v1.0/iot-03/devices/{device_id}/status"
        )

    async def get_specification(self, device_id: str) -> dict[str, Any]:
        """Get the device specification including instruction set and status set."""
        return await self._client.request(
            "GET", f"/v1.0/iot-03/devices/{device_id}/specification"
        )

    async def get_functions(self, device_id: str) -> dict[str, Any]:
        """Get the supported controllable functions for a device."""
        return await self._client.request("GET", f"/v1.0/devices/{device_id}/functions")

    async def send_commands(
        self,
        device_id: str,
        commands: list[dict[str, Any]],
    ) -> bool:
        """Send control commands to a device.

        ``commands`` is a list of dicts with ``code`` and ``value`` keys, e.g.::

            [{"code": "switch_led", "value": True}]
        """
        await self._client.request(
            "POST",
            f"/v1.0/iot-03/devices/{device_id}/commands",
            body={"commands": commands},
        )
        return True

    async def get_sub_devices(self, gateway_id: str) -> list[dict[str, Any]]:
        """List sub-devices attached to a gateway."""
        return await self._client.request(
            "GET", f"/v1.0/iot-03/devices/{gateway_id}/sub-devices"
        )
