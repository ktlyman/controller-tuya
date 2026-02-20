"""Tests for the TuyaClient request signing and token flow."""

import json

import pytest
import pytest_httpx

from tuya_agent.client import TuyaAPIError, TuyaClient
from tuya_agent.config import TuyaConfig


def _config() -> TuyaConfig:
    return TuyaConfig(access_id="test_id", access_secret="test_secret", api_region="us")


def _token_response(access_token: str = "tok_abc", refresh_token: str = "ref_xyz"):
    return {
        "success": True,
        "result": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expire_time": 7200,
            "uid": "u123",
        },
    }


class TestTuyaClient:
    @pytest.mark.asyncio
    async def test_fetch_token(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        client = TuyaClient(config=_config())
        token = await client._fetch_token()
        assert token == "tok_abc"
        assert client._token is not None
        assert client._token.refresh_token == "ref_xyz"
        await client.close()

    @pytest.mark.asyncio
    async def test_request_raises_on_api_error(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={"success": False, "code": 1010, "msg": "token invalid"}
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        with pytest.raises(TuyaAPIError, match="1010"):
            await client.request("GET", "/v1.0/devices/fake")
        await client.close()

    @pytest.mark.asyncio
    async def test_request_returns_result(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={
                "success": True,
                "result": [{"code": "switch", "value": True}],
            }
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.request("GET", "/v1.0/iot-03/devices/dev1/status")
        assert result == [{"code": "switch", "value": True}]
        await client.close()

    @pytest.mark.asyncio
    async def test_request_sends_body_for_post(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(json={"success": True, "result": True})
        client = TuyaClient(config=_config())
        await client._fetch_token()
        await client.request(
            "POST",
            "/v1.0/iot-03/devices/dev1/commands",
            body={"commands": [{"code": "switch", "value": True}]},
        )
        request = httpx_mock.get_requests()[-1]
        assert request.method == "POST"
        body = json.loads(request.content)
        assert body["commands"][0]["code"] == "switch"
        await client.close()
