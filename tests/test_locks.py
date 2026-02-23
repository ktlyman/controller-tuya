"""Tests for the LocksMixin."""

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


class TestLocksMixin:
    @pytest.mark.asyncio
    async def test_get_password_ticket(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={"success": True, "result": {"ticket_id": "tk1", "expire_time": 120}}
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.locks.get_password_ticket("lock1")
        assert result["ticket_id"] == "tk1"
        req = httpx_mock.get_requests()[-1]
        assert "/door-lock/password-ticket" in str(req.url)
        assert req.method == "POST"
        await client.close()

    @pytest.mark.asyncio
    async def test_password_free_unlock(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(json={"success": True, "result": True})
        client = TuyaClient(config=_config())
        await client._fetch_token()
        ok = await client.locks.password_free_unlock("lock1")
        assert ok is True
        req = httpx_mock.get_requests()[-1]
        assert "/password-free/open-door" in str(req.url)
        await client.close()

    @pytest.mark.asyncio
    async def test_remote_unlock(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(json={"success": True, "result": True})
        client = TuyaClient(config=_config())
        await client._fetch_token()
        ok = await client.locks.remote_unlock("lock1")
        assert ok is True
        req = httpx_mock.get_requests()[-1]
        assert "/smart-lock/devices/lock1/password-free/door-operate" in str(req.url)
        await client.close()
