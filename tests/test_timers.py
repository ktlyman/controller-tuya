"""Tests for the TimersMixin."""

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


class TestTimersMixin:
    @pytest.mark.asyncio
    async def test_list_tasks(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={"success": True, "result": [{"timer_id": "t1", "status": 1}]}
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.timers.list_tasks("dev1")
        assert result == [{"timer_id": "t1", "status": 1}]
        req = httpx_mock.get_requests()[-1]
        assert "/v2.0/cloud/timer/device/dev1" in str(req.url)
        assert req.method == "GET"
        await client.close()

    @pytest.mark.asyncio
    async def test_add_task(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json={"success": True, "result": {"timer_id": "t2"}}
        )
        client = TuyaClient(config=_config())
        await client._fetch_token()
        result = await client.timers.add_task(
            "dev1",
            loops="0111110",
            time_zone="America/Los_Angeles",
            functions=[{"code": "switch", "value": True}],
        )
        assert result == {"timer_id": "t2"}
        req = httpx_mock.get_requests()[-1]
        assert req.method == "POST"
        body = json.loads(req.content)
        assert body["loops"] == "0111110"
        assert body["functions"] == [{"code": "switch", "value": True}]
        await client.close()

    @pytest.mark.asyncio
    async def test_modify_task(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(json={"success": True, "result": True})
        client = TuyaClient(config=_config())
        await client._fetch_token()
        ok = await client.timers.modify_task("dev1", timer_id="t1", loops="1111111")
        assert ok is True
        req = httpx_mock.get_requests()[-1]
        assert req.method == "PUT"
        body = json.loads(req.content)
        assert body["timer_id"] == "t1"
        assert body["loops"] == "1111111"
        await client.close()

    @pytest.mark.asyncio
    async def test_set_task_state(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(json={"success": True, "result": True})
        client = TuyaClient(config=_config())
        await client._fetch_token()
        ok = await client.timers.set_task_state("dev1", timer_id="t1", state=False)
        assert ok is True
        req = httpx_mock.get_requests()[-1]
        assert "/state" in str(req.url)
        body = json.loads(req.content)
        assert body["state"] is False
        await client.close()

    @pytest.mark.asyncio
    async def test_clear_tasks(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(json={"success": True, "result": True})
        client = TuyaClient(config=_config())
        await client._fetch_token()
        ok = await client.timers.clear_tasks("dev1")
        assert ok is True
        req = httpx_mock.get_requests()[-1]
        assert req.method == "DELETE"
        await client.close()

    @pytest.mark.asyncio
    async def test_batch_delete_tasks(self, httpx_mock: pytest_httpx.HTTPXMock):
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(json={"success": True, "result": True})
        client = TuyaClient(config=_config())
        await client._fetch_token()
        ok = await client.timers.batch_delete_tasks("dev1", timer_ids=["t1", "t2"])
        assert ok is True
        req = httpx_mock.get_requests()[-1]
        assert "/batch" in str(req.url)
        body = json.loads(req.content)
        assert body["timer_ids"] == ["t1", "t2"]
        await client.close()
