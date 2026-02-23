"""Tests for the WeatherMixin."""

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


class TestWeatherMixin:
    @pytest.mark.asyncio
    async def test_get_forecast(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={"success": True, "result": {"temp": 72, "humidity": 45}}
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.weather.get_forecast("city123")
        assert result == {"temp": 72, "humidity": 45}
        req = httpx_mock.get_requests()[-1]
        assert "/v1.0/cities/city123/weather-forecast" in str(req.url)
        await client.close()

    @pytest.mark.asyncio
    async def test_get_current_by_location(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={"success": True, "result": {"temp": 68, "wind": "5mph"}}
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.weather.get_current_by_location(lon=-122.4, lat=37.7)
        assert result == {"temp": 68, "wind": "5mph"}
        req = httpx_mock.get_requests()[-1]
        assert "lon=" in str(req.url)
        assert "lat=" in str(req.url)
        await client.close()

    @pytest.mark.asyncio
    async def test_get_forecast_by_ip(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={"success": True, "result": {"city": "SF", "temp": 65}}
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.weather.get_forecast_by_ip()
        assert result == {"city": "SF", "temp": 65}
        req = httpx_mock.get_requests()[-1]
        assert "/v1.0/ip/weather-forecast" in str(req.url)
        await client.close()
