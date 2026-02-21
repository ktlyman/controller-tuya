"""Tests for the FastAPI web server."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from httpx import ASGITransport

from tuya_agent.client import TuyaAPIError
from tuya_agent.server import EventBroadcaster, create_app
from tuya_agent.storage import LogRecord, LogStorage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_client() -> MagicMock:
    """Build a mock TuyaClient with nested domain mocks."""
    client = MagicMock()
    client.ensure_token = AsyncMock()
    client.close = AsyncMock()

    # devices
    client.devices.list = AsyncMock(return_value={
        "list": [
            {"id": "dev1", "name": "Light", "online": True, "category": "dj"},
        ],
        "total": 1,
        "has_more": False,
        "last_row_key": "",
    })
    client.devices.get = AsyncMock(return_value={
        "id": "dev1", "name": "Light", "online": True,
    })
    client.devices.get_status = AsyncMock(return_value=[
        {"code": "switch_1", "value": True},
    ])
    client.devices.get_specification = AsyncMock(return_value={
        "category": "dj", "functions": [], "status": [],
    })
    client.devices.get_functions = AsyncMock(return_value={
        "functions": [
            {"code": "switch_1", "type": "Boolean", "values": "{}"},
        ],
    })
    client.devices.send_commands = AsyncMock(return_value=True)

    # scenes
    client.scenes.list_scenes = AsyncMock(return_value=[
        {"scene_id": "sc1", "name": "Good Night"},
    ])
    client.scenes.trigger_scene = AsyncMock(return_value=True)

    # generic request (used by spaces endpoint)
    client.request = AsyncMock(return_value={
        "id": 12345, "name": "My Home", "root_id": 12345, "status": True,
    })

    return client


def _seed_storage(storage: LogStorage) -> None:
    """Insert sample data into an already-opened LogStorage."""
    records = [
        LogRecord(
            device_id="dev1", event_id=1, event_time=1700000000000,
            event_from="1", code="switch_1", value="true",
            status="1", raw_json="{}",
        ),
        LogRecord(
            device_id="dev1", event_id=2, event_time=1700000001000,
            event_from="1", code="temp_current", value="25",
            status="1", raw_json="{}",
        ),
        LogRecord(
            device_id="dev2", event_id=3, event_time=1700000002000,
            event_from="1", code="switch_1", value="false",
            status="1", raw_json="{}",
        ),
    ]
    storage.insert_logs(records)
    storage.set_device_bookmark("dev1", 1700000001000)
    run_id = storage.record_run_start()
    storage.record_run_end(run_id, devices=2, logs=3)


@pytest.fixture
async def client():
    """Async test client with mocked Tuya deps and seeded storage."""
    mock_tuya = _mock_client()
    storage = LogStorage(Path(":memory:"))
    storage.open()
    _seed_storage(storage)
    broadcaster = EventBroadcaster(client=mock_tuya)

    app = create_app(
        _test_state={
            "client": mock_tuya,
            "storage": storage,
            "broadcaster": broadcaster,
        },
    )

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver",
    ) as ac:
        yield ac, mock_tuya, storage

    storage.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRootEndpoint:
    async def test_root_returns_html(self, client) -> None:
        ac, _, _ = client
        resp = await ac.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")


class TestDeviceEndpoints:
    async def test_list_devices(self, client) -> None:
        ac, mock_tuya, _ = client
        resp = await ac.get("/api/devices")
        assert resp.status_code == 200
        data = resp.json()
        assert "list" in data
        mock_tuya.devices.list.assert_called_once()

    async def test_get_device(self, client) -> None:
        ac, mock_tuya, _ = client
        resp = await ac.get("/api/devices/dev1")
        assert resp.status_code == 200
        assert resp.json()["id"] == "dev1"
        mock_tuya.devices.get.assert_called_once_with("dev1")

    async def test_get_device_status(self, client) -> None:
        ac, _, _ = client
        resp = await ac.get("/api/devices/dev1/status")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["code"] == "switch_1"

    async def test_get_device_specification(self, client) -> None:
        ac, _, _ = client
        resp = await ac.get("/api/devices/dev1/specification")
        assert resp.status_code == 200
        assert "category" in resp.json()

    async def test_get_device_functions(self, client) -> None:
        ac, _, _ = client
        resp = await ac.get("/api/devices/dev1/functions")
        assert resp.status_code == 200
        assert "functions" in resp.json()

    async def test_send_commands(self, client) -> None:
        ac, mock_tuya, _ = client
        resp = await ac.post(
            "/api/devices/dev1/commands",
            json={"commands": [{"code": "switch_1", "value": True}]},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        mock_tuya.devices.send_commands.assert_called_once()

    async def test_tuya_api_error_returns_502(self, client) -> None:
        ac, mock_tuya, _ = client
        mock_tuya.devices.list = AsyncMock(
            side_effect=TuyaAPIError(1010, "token invalid"),
        )
        resp = await ac.get("/api/devices")
        assert resp.status_code == 502
        assert resp.json()["detail"]["tuya_code"] == 1010


class TestSceneEndpoints:
    async def test_list_scenes(self, client) -> None:
        ac, _, _ = client
        resp = await ac.get("/api/homes/home1/scenes")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["name"] == "Good Night"

    async def test_trigger_scene(self, client) -> None:
        ac, mock_tuya, _ = client
        resp = await ac.post("/api/homes/home1/scenes/sc1/trigger")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        mock_tuya.scenes.trigger_scene.assert_called_once_with(
            "home1", "sc1",
        )


class TestSpaceEndpoints:
    async def test_get_space(self, client) -> None:
        ac, mock_tuya, _ = client
        resp = await ac.get("/api/spaces/12345")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "My Home"
        mock_tuya.request.assert_called_once_with(
            "GET", "/v2.0/cloud/space/12345",
        )


class TestStorageEndpoints:
    async def test_query_logs(self, client) -> None:
        ac, _, _ = client
        resp = await ac.get("/api/logs")
        assert resp.status_code == 200
        data = resp.json()
        assert "logs" in data
        assert data["total"] == 3

    async def test_query_logs_with_device_filter(self, client) -> None:
        ac, _, _ = client
        resp = await ac.get("/api/logs?device_id=dev1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert all(row["device_id"] == "dev1" for row in data["logs"])

    async def test_query_logs_with_code_filter(self, client) -> None:
        ac, _, _ = client
        resp = await ac.get("/api/logs?code=switch_1")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    async def test_get_stats(self, client) -> None:
        ac, _, _ = client
        resp = await ac.get("/api/logs/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_logs"] == 3
        assert data["total_devices"] == 2
        assert data["total_runs"] == 1

    async def test_get_bookmarks(self, client) -> None:
        ac, _, _ = client
        resp = await ac.get("/api/logs/bookmarks")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["device_id"] == "dev1"

    async def test_get_runs(self, client) -> None:
        ac, _, _ = client
        resp = await ac.get("/api/logs/runs")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["status"] == "completed"


class TestSSEEndpoint:
    async def test_event_stream_content_type(self, client) -> None:
        import asyncio

        ac, _, _ = client

        async def _check() -> None:
            async with ac.stream("GET", "/api/events/stream") as resp:
                assert resp.status_code == 200
                assert "text/event-stream" in resp.headers.get(
                    "content-type", "",
                )

        # The SSE endpoint streams forever; we only need the headers.
        try:
            await asyncio.wait_for(_check(), timeout=2.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass  # Expected — we just needed to verify the headers.
