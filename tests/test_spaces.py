"""Tests for the SpacesMixin."""

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


class TestSpacesMixin:
    @pytest.mark.asyncio
    async def test_get(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={
                "success": True,
                "result": {"space_id": "sp1", "name": "Home"},
            }
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.spaces.get("sp1")
        assert result["name"] == "Home"
        req = httpx_mock.get_requests()[-1]
        assert "/v2.0/cloud/space/sp1" in str(req.url)
        await client.close()

    @pytest.mark.asyncio
    async def test_list_spaces(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={
                "success": True,
                "result": {
                    "total": 2,
                    "list": [{"space_id": "sp1"}, {"space_id": "sp2"}],
                },
            }
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.spaces.list_spaces(page_no=1, page_size=10)
        assert result["total"] == 2
        req = httpx_mock.get_requests()[-1]
        assert "page_no=1" in str(req.url)
        await client.close()

    @pytest.mark.asyncio
    async def test_create(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={"success": True, "result": {"space_id": "sp_new"}}
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.spaces.create(name="Bedroom", parent_id="sp1")
        assert result["space_id"] == "sp_new"
        req = httpx_mock.get_requests()[-1]
        body = json.loads(req.content)
        assert body["name"] == "Bedroom"
        assert body["parent_id"] == "sp1"
        await client.close()

    @pytest.mark.asyncio
    async def test_get_children(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={
                "success": True,
                "result": [{"space_id": "sp2", "name": "Living Room"}],
            }
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.spaces.get_children("sp1")
        assert result[0]["name"] == "Living Room"
        req = httpx_mock.get_requests()[-1]
        assert "/space/sp1/children" in str(req.url)
        await client.close()

    @pytest.mark.asyncio
    async def test_get_resources(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={
                "success": True,
                "result": [{"resource_id": "d1", "type": "device"}],
            }
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.spaces.get_resources("sp1")
        assert result[0]["type"] == "device"
        req = httpx_mock.get_requests()[-1]
        assert "/space/sp1/resources" in str(req.url)
        await client.close()
