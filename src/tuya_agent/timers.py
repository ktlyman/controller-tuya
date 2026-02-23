"""Device timer / scheduled task operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tuya_agent.client import TuyaClient


class TimersMixin:
    """Methods for managing device timers (scheduled tasks)."""

    def __init__(self, client: TuyaClient) -> None:
        self._client = client

    async def list_tasks(self, device_id: str) -> list[dict[str, Any]]:
        """List all timer tasks for a device."""
        return await self._client.request(
            "GET", f"/v2.0/cloud/timer/device/{device_id}",
        )

    async def add_task(
        self,
        device_id: str,
        *,
        timer_type: int = 0,
        category: str = "scheduler",
        loops: str = "0000000",
        time_zone: str = "",
        functions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create a new timer task on a device.

        ``functions`` is a list of dicts with ``code`` and ``value`` keys
        that define what the device should do when the timer fires.
        ``loops`` is a 7-char string for day-of-week repetition (0=off, 1=on).
        """
        body: dict[str, Any] = {
            "timer_type": timer_type,
            "category": category,
            "loops": loops,
            "functions": functions,
        }
        if time_zone:
            body["time_zone"] = time_zone
        return await self._client.request(
            "POST", f"/v2.0/cloud/timer/device/{device_id}", body=body,
        )

    async def modify_task(
        self,
        device_id: str,
        *,
        timer_id: str,
        loops: str | None = None,
        functions: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Modify an existing timer task."""
        body: dict[str, Any] = {"timer_id": timer_id}
        if loops is not None:
            body["loops"] = loops
        if functions is not None:
            body["functions"] = functions
        await self._client.request(
            "PUT", f"/v2.0/cloud/timer/device/{device_id}", body=body,
        )
        return True

    async def set_task_state(
        self,
        device_id: str,
        *,
        timer_id: str,
        state: bool,
    ) -> bool:
        """Enable or disable a timer task."""
        await self._client.request(
            "PUT",
            f"/v2.0/cloud/timer/device/{device_id}/state",
            body={"timer_id": timer_id, "state": state},
        )
        return True

    async def clear_tasks(self, device_id: str) -> bool:
        """Delete all timer tasks for a device."""
        await self._client.request(
            "DELETE", f"/v2.0/cloud/timer/device/{device_id}",
        )
        return True

    async def batch_delete_tasks(
        self,
        device_id: str,
        *,
        timer_ids: list[str],
    ) -> bool:
        """Delete specific timer tasks by their IDs."""
        await self._client.request(
            "DELETE",
            f"/v2.0/cloud/timer/device/{device_id}/batch",
            body={"timer_ids": timer_ids},
        )
        return True
