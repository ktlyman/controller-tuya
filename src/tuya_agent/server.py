"""FastAPI backend for the Tuya IoT dashboard.

Wraps :class:`TuyaClient` and :class:`LogStorage` behind REST endpoints and
provides a Server-Sent Events stream for real-time device events.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import websockets
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from tuya_agent.client import TuyaAPIError, TuyaClient
from tuya_agent.events import TuyaEvent
from tuya_agent.storage import LogStorage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class SendCommandsRequest(BaseModel):
    """Body schema for ``POST /api/devices/{device_id}/commands``."""

    commands: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# EventBroadcaster — fans out Pulsar events to SSE clients
# ---------------------------------------------------------------------------


@dataclass
class EventBroadcaster:
    """Subscribes to Tuya Pulsar events and broadcasts them to SSE clients.

    Each connected SSE client receives a copy of every event via its own
    :class:`asyncio.Queue`.
    """

    client: TuyaClient
    _subscribers: list[asyncio.Queue[dict[str, Any]]] = field(
        default_factory=list,
    )
    _task: asyncio.Task[None] | None = field(
        default=None, repr=False,
    )

    # -- lifecycle -----------------------------------------------------------

    def start(self) -> None:
        """Start the background Pulsar subscription task."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._subscribe_loop())
            logger.info("EventBroadcaster started")

    async def stop(self) -> None:
        """Cancel the background task and drain subscriber queues."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._subscribers.clear()
        logger.info("EventBroadcaster stopped")

    # -- subscriber management -----------------------------------------------

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """Register a new SSE client and return its event queue."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(
            maxsize=256,
        )
        self._subscribers.append(queue)
        logger.debug(
            "SSE client subscribed (%d total)", len(self._subscribers),
        )
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Remove a previously registered SSE client queue."""
        try:
            self._subscribers.remove(queue)
        except ValueError:
            pass
        logger.debug(
            "SSE client unsubscribed (%d remaining)",
            len(self._subscribers),
        )

    # -- internal ------------------------------------------------------------

    async def _subscribe_loop(self) -> None:
        """Connect to Pulsar and push decoded events to all subscribers."""
        while True:
            try:
                async for event in self.client.events.subscribe():
                    self._fan_out(event)
            except websockets.exceptions.InvalidStatus as exc:
                status = getattr(
                    getattr(exc, "response", None),
                    "status_code",
                    None,
                )
                if status == 401:
                    logger.error(
                        "Pulsar returned 401 Unauthorized — "
                        "ensure the Message Service is enabled in "
                        "your Tuya cloud project."
                    )
                    return  # stop; don't crash the server
                logger.exception("Pulsar connection error")
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "Unexpected error in EventBroadcaster; "
                    "reconnecting in 5 s"
                )
                await asyncio.sleep(5)

    def _fan_out(self, event: TuyaEvent) -> None:
        """Push a serialised event dict to every subscriber queue."""
        payload = {
            "event_type": event.event_type,
            "device_id": event.device_id,
            "product_id": event.product_id,
            "data": event.data,
            "timestamp": event.timestamp,
        }
        dead: list[asyncio.Queue[dict[str, Any]]] = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(queue)
        for q in dead:
            self.unsubscribe(q)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app(
    db_path: Path = Path("tuya_logs.db"),
    *,
    _test_state: dict[str, Any] | None = None,
) -> FastAPI:
    """Build and return a configured :class:`FastAPI` application.

    The *db_path* controls which SQLite database is used by the
    :class:`LogStorage` instance.

    The private ``_test_state`` parameter is used by tests to inject
    pre-built ``client``, ``storage``, and ``broadcaster`` objects so
    that the lifespan can be skipped.
    """

    # Mutable holders so the lifespan can share state with endpoints.
    state: dict[str, Any] = dict(_test_state) if _test_state else {}

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        if _test_state:
            yield
            return

        # -- startup ---------------------------------------------------------
        storage = LogStorage(db_path)
        storage.open()
        logger.info("LogStorage opened at %s", db_path)

        client = TuyaClient()
        await client.ensure_token()
        logger.info("TuyaClient authenticated")

        broadcaster = EventBroadcaster(client=client)
        broadcaster.start()

        state["storage"] = storage
        state["client"] = client
        state["broadcaster"] = broadcaster

        yield

        # -- shutdown --------------------------------------------------------
        await broadcaster.stop()
        await client.close()
        storage.close()
        logger.info("Server resources released")

    app = FastAPI(
        title="Tuya IoT Dashboard",
        lifespan=lifespan,
    )

    # -- CORS (permissive for local dev) ---------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -- helpers ---------------------------------------------------------

    def _client() -> TuyaClient:
        return state["client"]

    def _storage() -> LogStorage:
        return state["storage"]

    def _broadcaster() -> EventBroadcaster:
        return state["broadcaster"]

    def _handle_tuya_error(exc: TuyaAPIError) -> None:
        """Translate a TuyaAPIError into an HTTPException."""
        raise HTTPException(
            status_code=502,
            detail={"tuya_code": exc.code, "tuya_msg": exc.msg},
        )

    # ===================================================================
    # Static / root
    # ===================================================================

    @app.get("/", include_in_schema=False)
    async def root() -> FileResponse:
        static_dir = Path(__file__).parent / "static"
        index = static_dir / "index.html"
        return FileResponse(index)

    # ===================================================================
    # Device endpoints
    # ===================================================================

    @app.get("/api/devices")
    async def list_devices(
        page_size: int = Query(20, ge=1, le=100),
        last_row_key: str | None = Query(None),
    ) -> Any:
        try:
            result = await _client().devices.list(
                page_size=page_size,
                last_row_key=last_row_key,
            )
            # The Tuya API may return a plain list or a dict with
            # pagination metadata — normalise to a consistent shape.
            if isinstance(result, list):
                return {"list": result, "total": len(result)}
            return result
        except TuyaAPIError as exc:
            _handle_tuya_error(exc)

    @app.get("/api/devices/{device_id}")
    async def get_device(device_id: str) -> dict[str, Any]:
        try:
            return await _client().devices.get(device_id)
        except TuyaAPIError as exc:
            _handle_tuya_error(exc)

    @app.get("/api/devices/{device_id}/status")
    async def get_device_status(
        device_id: str,
    ) -> list[dict[str, Any]]:
        try:
            return await _client().devices.get_status(device_id)
        except TuyaAPIError as exc:
            _handle_tuya_error(exc)

    @app.get("/api/devices/{device_id}/specification")
    async def get_device_specification(
        device_id: str,
    ) -> dict[str, Any]:
        try:
            return await _client().devices.get_specification(
                device_id,
            )
        except TuyaAPIError as exc:
            _handle_tuya_error(exc)

    @app.get("/api/devices/{device_id}/functions")
    async def get_device_functions(
        device_id: str,
    ) -> dict[str, Any]:
        try:
            return await _client().devices.get_functions(device_id)
        except TuyaAPIError as exc:
            _handle_tuya_error(exc)

    @app.post("/api/devices/{device_id}/commands")
    async def send_commands(
        device_id: str,
        body: SendCommandsRequest,
    ) -> dict[str, bool]:
        try:
            result = await _client().devices.send_commands(
                device_id, body.commands,
            )
            return {"success": result}
        except TuyaAPIError as exc:
            _handle_tuya_error(exc)

    # ===================================================================
    # Scene endpoints
    # ===================================================================

    @app.get("/api/spaces/{space_id}/scenes")
    async def list_scenes(space_id: str) -> Any:
        try:
            return await _client().scenes.list_rules(space_id)
        except TuyaAPIError as exc:
            _handle_tuya_error(exc)

    @app.post("/api/scenes/{rule_id}/trigger")
    async def trigger_scene(rule_id: str) -> dict[str, bool]:
        try:
            result = await _client().scenes.trigger_rule(rule_id)
            return {"success": result}
        except TuyaAPIError as exc:
            _handle_tuya_error(exc)

    # ===================================================================
    # Space endpoints
    # ===================================================================

    @app.get("/api/spaces/{space_id}")
    async def get_space(space_id: str) -> dict[str, Any]:
        try:
            return await _client().request(
                "GET", f"/v2.0/cloud/space/{space_id}",
            )
        except TuyaAPIError as exc:
            _handle_tuya_error(exc)

    # ===================================================================
    # Log / storage endpoints
    # ===================================================================

    @app.get("/api/logs")
    async def query_logs(
        device_id: str | None = Query(None),
        start_time: int | None = Query(None),
        end_time: int | None = Query(None),
        code: str | None = Query(None),
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ) -> dict[str, Any]:
        rows, total = _storage().query_logs(
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            code=code,
            limit=limit,
            offset=offset,
        )
        return {"logs": rows, "total": total}

    @app.get("/api/logs/stats")
    async def get_stats() -> dict[str, int]:
        return _storage().get_stats()

    @app.get("/api/logs/bookmarks")
    async def get_bookmarks() -> list[dict[str, Any]]:
        pairs = _storage().get_all_bookmarks()
        return [
            {"device_id": did, "last_event_time": ts}
            for did, ts in pairs
        ]

    @app.get("/api/logs/runs")
    async def get_runs(
        limit: int = Query(50, ge=1, le=500),
    ) -> list[dict[str, Any]]:
        return _storage().get_runs(limit=limit)

    # ===================================================================
    # Server-Sent Events (real-time stream)
    # ===================================================================

    @app.get("/api/events/stream")
    async def event_stream() -> StreamingResponse:
        broadcaster = _broadcaster()
        queue = broadcaster.subscribe()

        async def _generate() -> AsyncGenerator[str, None]:
            try:
                while True:
                    try:
                        event = await asyncio.wait_for(
                            queue.get(), timeout=30.0,
                        )
                        data = json.dumps(event)
                        yield f"data: {data}\n\n"
                    except asyncio.TimeoutError:
                        # Send a keepalive comment to prevent
                        # proxy / client timeouts.
                        yield ": keepalive\n\n"
            except asyncio.CancelledError:
                pass
            finally:
                broadcaster.unsubscribe(queue)

        return StreamingResponse(
            _generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return app
