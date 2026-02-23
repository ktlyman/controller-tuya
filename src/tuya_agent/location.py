"""Device location and geofence operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tuya_agent.client import TuyaClient


class LocationMixin:
    """Methods for querying device location and geofences."""

    def __init__(self, client: TuyaClient) -> None:
        self._client = client

    async def get_realtime_location(
        self, device_id: str,
    ) -> dict[str, Any]:
        """Get the real-time GPS location of a device."""
        return await self._client.request(
            "GET",
            "/v2.0/iot-01/tracks/location",
            params={"device_id": device_id},
        )

    async def get_track_history(
        self,
        device_id: str,
        *,
        start_time: int,
        end_time: int,
    ) -> list[dict[str, Any]]:
        """Get historical location track for a device.

        Times are 13-digit millisecond timestamps.
        """
        return await self._client.request(
            "GET",
            "/v2.0/iot-01/tracks/detail",
            params={
                "device_id": device_id,
                "start_time": start_time,
                "end_time": end_time,
            },
        )

    async def list_geofences(self, device_id: str) -> list[dict[str, Any]]:
        """List geofences configured for a device."""
        return await self._client.request(
            "GET",
            "/v2.0/iot-01/fences/list",
            params={"device_id": device_id},
        )
