"""Historic event and routine logging queries."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tuya_agent.client import TuyaClient


class LogsMixin:
    """Methods for querying device logs, status history, and statistics."""

    def __init__(self, client: TuyaClient) -> None:
        self._client = client

    # -- Device event logs ---------------------------------------------------

    async def get_device_logs(
        self,
        device_id: str,
        *,
        start_time: int,
        end_time: int,
        event_types: str = "1,2,3,4,5,6,7,8,9,10",
        page_size: int = 20,
        last_row_key: str | None = None,
    ) -> dict[str, Any]:
        """Query device event logs (online/offline/activation/reset etc.).

        ``event_types`` is a comma-separated string of event type codes.
        Common types: 1=online, 2=offline, 3=activate, 7=upgrade.

        Times are 13-digit Unix timestamps in milliseconds.
        """
        params: dict[str, Any] = {
            "event_types": event_types,
            "start_time": start_time,
            "end_time": end_time,
            "size": page_size,
        }
        if last_row_key:
            params["last_row_key"] = last_row_key
        return await self._client.request(
            "GET", f"/v1.0/iot-03/devices/{device_id}/logs", params=params
        )

    # -- Data-point status history -------------------------------------------

    async def get_report_logs(
        self,
        device_id: str,
        *,
        start_time: int,
        end_time: int,
        codes: str | None = None,
        page_size: int = 20,
        last_row_key: str | None = None,
    ) -> dict[str, Any]:
        """Query historical data-point (DP) status reports for a device.

        ``codes`` is an optional comma-separated list of DP codes to filter by.
        Times are 13-digit Unix timestamps in milliseconds.

        Returns a dict with ``logs`` (list of records) and ``last_row_key``
        for cursor-based pagination.
        """
        params: dict[str, Any] = {
            "start_time": start_time,
            "end_time": end_time,
            "size": page_size,
        }
        if codes:
            params["codes"] = codes
        if last_row_key:
            params["last_row_key"] = last_row_key
        return await self._client.request(
            "GET", f"/v2.0/cloud/thing/{device_id}/report-logs", params=params
        )

    # -- Aggregated statistics -----------------------------------------------

    async def get_statistics(
        self,
        device_id: str,
        *,
        interval: str = "days",
        start_time: int,
        end_time: int,
        code: str,
    ) -> dict[str, Any]:
        """Get aggregated device statistics.

        ``interval`` can be one of: ``quarters`` (15 min), ``days``, ``weeks``,
        ``months``.  ``code`` is the DP code to aggregate (e.g. ``"cur_power"``).
        """
        valid = {"quarters", "days", "weeks", "months"}
        if interval not in valid:
            raise ValueError(f"interval must be one of {valid}")
        return await self._client.request(
            "GET",
            f"/v1.0/devices/{device_id}/statistics/{interval}",
            params={
                "start_time": start_time,
                "end_time": end_time,
                "code": code,
            },
        )

    async def get_statistic_types(self, device_id: str) -> list[dict[str, Any]]:
        """List available statistic types for a device."""
        return await self._client.request(
            "GET", f"/v1.0/devices/{device_id}/all-statistic-type"
        )
