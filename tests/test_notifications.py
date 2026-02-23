"""Tests for the NotificationsMixin."""

import json

import pytest
import pytest_httpx

from tuya_agent.client import TuyaClient
from tuya_agent.config import TuyaConfig


def _config() -> TuyaConfig:
    return TuyaConfig(access_id="test_id", access_secret="test_secret", api_region="us")


def _token_response():
    return {
        "success": True,
        "result": {
            "access_token": "tok_abc",
            "refresh_token": "ref_xyz",
            "expire_time": 7200,
            "uid": "u123",
        },
    }


class TestNotificationsMixin:
    @pytest.mark.asyncio
    async def test_push(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(json={"success": True, "result": True})
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.notifications.push(
            title="Alert",
            content="Motion detected",
            target_user_ids=["u1", "u2"],
        )
        assert result is True
        req = httpx_mock.get_requests()[-1]
        assert "/app-notifications/actions/push" in str(req.url)
        body = json.loads(req.content)
        assert body["title"] == "Alert"
        assert body["target_user_ids"] == ["u1", "u2"]
        await client.close()
