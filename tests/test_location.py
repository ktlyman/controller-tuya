"""Tests for the LocationMixin."""

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


class TestLocationMixin:
    @pytest.mark.asyncio
    async def test_get_realtime_location(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={"success": True, "result": {"lon": -122.4, "lat": 37.7}}
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.location.get_realtime_location("dev1")
        assert result["lon"] == -122.4
        req = httpx_mock.get_requests()[-1]
        assert "device_id=dev1" in str(req.url)
        await client.close()

    @pytest.mark.asyncio
    async def test_get_track_history(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={
                "success": True,
                "result": [
                    {"lon": -122.4, "lat": 37.7, "time": 1700000000000},
                ],
            }
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.location.get_track_history(
            "dev1", start_time=1700000000000, end_time=1700003600000,
        )
        assert len(result) == 1
        req = httpx_mock.get_requests()[-1]
        assert "start_time=" in str(req.url)
        await client.close()

    @pytest.mark.asyncio
    async def test_list_geofences(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={
                "success": True,
                "result": [{"fence_id": "f1", "name": "Home"}],
            }
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.location.list_geofences("dev1")
        assert result[0]["fence_id"] == "f1"
        await client.close()
