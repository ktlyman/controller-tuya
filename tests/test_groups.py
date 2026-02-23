"""Tests for the GroupsMixin."""

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


class TestGroupsMixin:
    @pytest.mark.asyncio
    async def test_list_groups(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={
                "success": True,
                "result": {"total": 1, "list": [{"group_id": "g1"}]},
            }
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.groups.list_groups(page_no=1, page_size=10)
        assert result["total"] == 1
        req = httpx_mock.get_requests()[-1]
        assert "page_no=1" in str(req.url)
        await client.close()

    @pytest.mark.asyncio
    async def test_create(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={"success": True, "result": {"group_id": "g_new"}}
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.groups.create(
            name="Living Room", product_id="p1", device_ids=["d1", "d2"],
        )
        assert result["group_id"] == "g_new"
        req = httpx_mock.get_requests()[-1]
        body = json.loads(req.content)
        assert body["name"] == "Living Room"
        assert body["device_ids"] == ["d1", "d2"]
        await client.close()

    @pytest.mark.asyncio
    async def test_get(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={
                "success": True,
                "result": {"group_id": "g1", "name": "Kitchen"},
            }
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.groups.get("g1")
        assert result["name"] == "Kitchen"
        req = httpx_mock.get_requests()[-1]
        assert "/group/g1" in str(req.url)
        await client.close()

    @pytest.mark.asyncio
    async def test_list_devices(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={
                "success": True,
                "result": [{"device_id": "d1"}, {"device_id": "d2"}],
            }
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.groups.list_devices("g1")
        assert len(result) == 2
        req = httpx_mock.get_requests()[-1]
        assert "/group/g1/devices" in str(req.url)
        await client.close()

    @pytest.mark.asyncio
    async def test_delete(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(json={"success": True, "result": True})
        client = TuyaClient(config=_config())
        await client._fetch_token()
        ok = await client.groups.delete("g1")
        assert ok is True
        req = httpx_mock.get_requests()[-1]
        assert req.method == "DELETE"
        assert "/group/g1" in str(req.url)
        await client.close()
