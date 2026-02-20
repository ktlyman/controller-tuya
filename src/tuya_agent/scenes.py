"""Scene and automation (routine) management."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tuya_agent.client import TuyaClient


class ScenesMixin:
    """Methods for managing Tuya scenes (tap-to-run) and automations."""

    def __init__(self, client: TuyaClient) -> None:
        self._client = client

    # -- Tap-to-run scenes ---------------------------------------------------

    async def list_scenes(self, home_id: str) -> list[dict[str, Any]]:
        """List all tap-to-run scenes in a home."""
        return await self._client.request("GET", f"/v1.1/homes/{home_id}/scenes")

    async def trigger_scene(self, home_id: str, scene_id: str) -> bool:
        """Trigger (execute) a tap-to-run scene."""
        await self._client.request(
            "POST", f"/v1.0/homes/{home_id}/scenes/{scene_id}/trigger"
        )
        return True

    async def create_scene(
        self,
        home_id: str,
        *,
        name: str,
        actions: list[dict[str, Any]],
        background: str = "",
    ) -> dict[str, Any]:
        """Create a new tap-to-run scene.

        ``actions`` is a list of action dicts, each typically containing
        ``entity_id``, ``action_executor``, and ``executor_property``.
        """
        body: dict[str, Any] = {"name": name, "actions": actions}
        if background:
            body["background"] = background
        return await self._client.request(
            "POST", f"/v1.0/homes/{home_id}/scenes", body=body
        )

    async def delete_scene(self, home_id: str, scene_id: str) -> bool:
        """Delete a tap-to-run scene."""
        await self._client.request(
            "DELETE", f"/v1.0/homes/{home_id}/scenes/{scene_id}"
        )
        return True

    # -- Automations ---------------------------------------------------------

    async def get_automation(self, home_id: str, automation_id: str) -> dict[str, Any]:
        """Get details for a single automation."""
        return await self._client.request(
            "GET", f"/v1.0/homes/{home_id}/automations/{automation_id}"
        )

    async def create_automation(
        self,
        home_id: str,
        *,
        name: str,
        conditions: list[dict[str, Any]],
        actions: list[dict[str, Any]],
        match_type: int = 1,
        preconditions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create a new automation rule.

        ``match_type``: 1 = all conditions must match, 2 = any condition.
        ``conditions``: list of condition dicts (max 10).
        ``actions``: list of action dicts (max 50).
        ``preconditions``: optional time-window restrictions.
        """
        body: dict[str, Any] = {
            "name": name,
            "conditions": conditions,
            "actions": actions,
            "match_type": match_type,
        }
        if preconditions:
            body["preconditions"] = preconditions
        return await self._client.request(
            "POST", f"/v1.0/homes/{home_id}/automations", body=body
        )

    async def enable_automation(self, home_id: str, automation_id: str) -> bool:
        """Enable a disabled automation."""
        await self._client.request(
            "PUT", f"/v1.0/homes/{home_id}/automations/{automation_id}/actions/enable"
        )
        return True

    async def disable_automation(self, home_id: str, automation_id: str) -> bool:
        """Disable an active automation."""
        await self._client.request(
            "PUT", f"/v1.0/homes/{home_id}/automations/{automation_id}/actions/disable"
        )
        return True
