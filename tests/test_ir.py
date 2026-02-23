"""Tests for the IRMixin."""

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


class TestIRMixin:
    @pytest.mark.asyncio
    async def test_list_categories(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={"success": True, "result": [{"category_id": "1", "name": "TV"}]}
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.ir.list_categories("ir1")
        assert result == [{"category_id": "1", "name": "TV"}]
        req = httpx_mock.get_requests()[-1]
        assert "/v2.0/infrareds/ir1/categories" in str(req.url)
        await client.close()

    @pytest.mark.asyncio
    async def test_list_remotes(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={"success": True, "result": [{"remote_id": "r1", "name": "LG TV"}]}
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.ir.list_remotes("ir1")
        assert result[0]["remote_id"] == "r1"
        await client.close()

    @pytest.mark.asyncio
    async def test_get_remote_keys(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={
                "success": True,
                "result": {"keys": ["power", "vol_up", "vol_down"]},
            }
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.ir.get_remote_keys("ir1", "r1")
        assert "keys" in result
        req = httpx_mock.get_requests()[-1]
        assert "/remotes/r1/keys" in str(req.url)
        await client.close()

    @pytest.mark.asyncio
    async def test_send_command(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(json={"success": True, "result": True})
        client = TuyaClient(config=_config())
        await client._fetch_token()
        ok = await client.ir.send_command("ir1", "r1", key="power")
        assert ok is True
        req = httpx_mock.get_requests()[-1]
        assert req.method == "POST"
        body = json.loads(req.content)
        assert body["key"] == "power"
        await client.close()

    @pytest.mark.asyncio
    async def test_save_learned_code(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={"success": True, "result": {"remote_id": "r_new"}}
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.ir.save_learned_code(
            "ir1",
            remote_name="Custom AC",
            category_id="2",
            key_name="cool",
            code="AABB1122",
        )
        assert result["remote_id"] == "r_new"
        req = httpx_mock.get_requests()[-1]
        assert "/learning-codes" in str(req.url)
        body = json.loads(req.content)
        assert body["remote_name"] == "Custom AC"
        await client.close()
