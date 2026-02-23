"""App push notification operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tuya_agent.client import TuyaClient


class NotificationsMixin:
    """Methods for sending push notifications to Tuya app users."""

    def __init__(self, client: TuyaClient) -> None:
        self._client = client

    async def push(
        self,
        *,
        title: str,
        content: str,
        target_user_ids: list[str],
    ) -> Any:
        """Send a push notification to specified app users."""
        return await self._client.request(
            "POST",
            "/v1.0/iot-03/messages/app-notifications/actions/push",
            body={
                "title": title,
                "content": content,
                "target_user_ids": target_user_ids,
            },
        )
