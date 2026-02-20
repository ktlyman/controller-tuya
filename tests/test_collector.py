"""Tests for the log collector orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from tuya_agent.client import TuyaClient
from tuya_agent.collector import CollectorConfig, LogCollector
from tuya_agent.config import TuyaConfig
from tuya_agent.storage import LogStorage


def _config() -> TuyaConfig:
    return TuyaConfig(
        access_id="test_id", access_secret="test_secret", api_region="us",
    )


def _token_response() -> dict:
    return {
        "success": True,
        "result": {
            "access_token": "tok",
            "refresh_token": "ref",
            "expire_time": 7200,
        },
    }


def _device_list_response(
    devices: list[dict], last_row_key: str = "",
) -> dict:
    return {
        "success": True,
        "result": {
            "list": devices,
            "last_row_key": last_row_key,
            "total": len(devices),
            "has_more": bool(last_row_key),
        },
    }


def _logs_response(
    logs: list[dict],
    has_next: bool = False,
    next_row_key: str = "",
) -> dict:
    return {
        "success": True,
        "result": {
            "logs": logs,
            "has_next": has_next,
            "next_row_key": next_row_key,
            "current_row_key": "",
            "device_id": "",
        },
    }


class TestLogCollector:
    @pytest.mark.asyncio
    async def test_discover_devices(self, httpx_mock) -> None:
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json=_device_list_response([
                {"id": "dev1", "name": "Light"},
                {"id": "dev2", "name": "Plug"},
            ]),
        )

        client = TuyaClient(config=_config())
        await client._fetch_token()
        with LogStorage(Path(":memory:")) as storage:
            collector = LogCollector(
                client, storage, CollectorConfig(request_delay=0),
            )
            devices = await collector.discover_devices()
            assert len(devices) == 2
            assert devices[0]["id"] == "dev1"
        await client.close()

    @pytest.mark.asyncio
    async def test_collect_all_stores_logs(self, httpx_mock) -> None:
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json=_device_list_response([{"id": "dev1", "name": "Light"}]),
        )
        httpx_mock.add_response(
            json=_logs_response([
                {
                    "event_id": 1,
                    "event_time": 1700000000000,
                    "event_from": "1",
                    "status": "1",
                },
                {
                    "event_id": 7,
                    "event_time": 1700000001000,
                    "event_from": "1",
                    "code": "switch_1",
                    "value": "true",
                    "status": "1",
                },
            ]),
        )

        client = TuyaClient(config=_config())
        await client._fetch_token()
        with LogStorage(Path(":memory:")) as storage:
            collector = LogCollector(
                client, storage, CollectorConfig(request_delay=0),
            )
            result = await collector.collect_all()
            assert result.logs_collected == 2
            assert result.devices_found == 1
            assert result.devices_collected == 1
            # Bookmark should be set to the latest event_time.
            bm = storage.get_device_bookmark("dev1")
            assert bm == 1700000001000
        await client.close()

    @pytest.mark.asyncio
    async def test_collect_handles_pagination(self, httpx_mock) -> None:
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json=_device_list_response([{"id": "dev1", "name": "Light"}]),
        )
        # Page 1.
        httpx_mock.add_response(
            json=_logs_response(
                [{"event_id": 1, "event_time": 1700000000000,
                  "event_from": "1", "status": "1"}],
                has_next=True,
                next_row_key="page2key",
            ),
        )
        # Page 2.
        httpx_mock.add_response(
            json=_logs_response(
                [{"event_id": 7, "event_time": 1700000001000,
                  "event_from": "1", "status": "1"}],
            ),
        )

        client = TuyaClient(config=_config())
        await client._fetch_token()
        with LogStorage(Path(":memory:")) as storage:
            collector = LogCollector(
                client, storage, CollectorConfig(request_delay=0),
            )
            result = await collector.collect_all()
            assert result.logs_collected == 2
        await client.close()

    @pytest.mark.asyncio
    async def test_incremental_uses_bookmark(self, httpx_mock) -> None:
        """Second run should start from the bookmark."""
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json=_device_list_response([{"id": "dev1", "name": "Light"}]),
        )
        httpx_mock.add_response(
            json=_logs_response([
                {"event_id": 8, "event_time": 1700000002000,
                 "event_from": "1", "status": "1"},
            ]),
        )

        client = TuyaClient(config=_config())
        await client._fetch_token()
        with LogStorage(Path(":memory:")) as storage:
            # Pre-set a bookmark as if we already collected.
            storage.set_device_bookmark("dev1", 1700000001000)
            collector = LogCollector(
                client, storage, CollectorConfig(request_delay=0),
            )
            result = await collector.collect_all()
            assert result.logs_collected == 1
            # Bookmark should advance.
            assert storage.get_device_bookmark("dev1") == 1700000002000
        await client.close()

    @pytest.mark.asyncio
    async def test_empty_logs_no_error(self, httpx_mock) -> None:
        """Devices with no log data should not cause failures."""
        httpx_mock.add_response(json=_token_response())
        httpx_mock.add_response(
            json=_device_list_response([{"id": "dev1", "name": "Sensor"}]),
        )
        httpx_mock.add_response(json=_logs_response([]))

        client = TuyaClient(config=_config())
        await client._fetch_token()
        with LogStorage(Path(":memory:")) as storage:
            collector = LogCollector(
                client, storage, CollectorConfig(request_delay=0),
            )
            result = await collector.collect_all()
            assert result.logs_collected == 0
            assert result.devices_collected == 1
            assert not result.errors
        await client.close()
