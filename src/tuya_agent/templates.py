"""Scene template operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tuya_agent.client import TuyaClient


class TemplatesMixin:
    """Methods for browsing and applying pre-built scene templates."""

    def __init__(self, client: TuyaClient) -> None:
        self._client = client

    async def list_templates(
        self,
        *,
        page_no: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List available scene templates with pagination."""
        return await self._client.request(
            "GET",
            "/v1.0/iot-03/scene-templates",
            params={"page_no": page_no, "page_size": page_size},
        )

    async def get_template(self, template_id: str) -> dict[str, Any]:
        """Get details of a specific scene template."""
        return await self._client.request(
            "GET", f"/v1.0/iot-03/scene-templates/{template_id}",
        )

    async def apply_template(
        self,
        template_id: str,
        asset_id: str,
    ) -> dict[str, Any]:
        """Apply a scene template to a specific asset (space)."""
        return await self._client.request(
            "POST",
            f"/v1.0/iot-03/scene-templates/{template_id}"
            f"/assets/{asset_id}/actions/apply",
        )
