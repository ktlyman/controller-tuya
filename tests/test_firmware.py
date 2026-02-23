"""Tests for the FirmwareMixin."""

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


class TestFirmwareMixin:
    @pytest.mark.asyncio
    async def test_get_info(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={
                "success": True,
                "result": [
                    {"module": "main", "version": "1.2.3", "upgrade_available": False},
                ],
            }
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.firmware.get_info("dev1")
        assert result[0]["version"] == "1.2.3"
        req = httpx_mock.get_requests()[-1]
        assert "/v2.0/cloud/thing/dev1/firmware" in str(req.url)
        assert req.method == "GET"
        await client.close()

    @pytest.mark.asyncio
    async def test_trigger_upgrade(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(json={"success": True, "result": True})
        client = TuyaClient(config=_config())
        await client._fetch_token()
        ok = await client.firmware.trigger_upgrade("dev1")
        assert ok is True
        req = httpx_mock.get_requests()[-1]
        assert "/firmware/upgrade" in str(req.url)
        assert req.method == "POST"
        await client.close()
