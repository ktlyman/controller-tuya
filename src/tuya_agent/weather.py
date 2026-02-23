"""Weather service operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tuya_agent.client import TuyaClient


class WeatherMixin:
    """Methods for querying weather data from the Tuya Weather Service."""

    def __init__(self, client: TuyaClient) -> None:
        self._client = client

    async def get_forecast(self, city_id: str) -> dict[str, Any]:
        """Get weather forecast for a city by Tuya city ID."""
        return await self._client.request(
            "GET", f"/v1.0/cities/{city_id}/weather-forecast",
        )

    async def get_current_by_location(
        self,
        *,
        lon: float,
        lat: float,
    ) -> dict[str, Any]:
        """Get current weather at a geographic coordinate."""
        return await self._client.request(
            "GET",
            "/v1.0/position/weather",
            params={"lon": lon, "lat": lat},
        )

    async def get_forecast_by_ip(self) -> dict[str, Any]:
        """Get weather forecast based on the caller's IP address."""
        return await self._client.request(
            "GET", "/v1.0/ip/weather-forecast",
        )
