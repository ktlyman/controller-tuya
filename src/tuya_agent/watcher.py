"""Real-time event watcher that streams Pulsar WebSocket events to SQLite."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any

import websockets

from tuya_agent.client import TuyaClient
from tuya_agent.events import TuyaEvent
from tuya_agent.storage import LogRecord, LogStorage

logger = logging.getLogger(__name__)


def event_to_record(event: TuyaEvent) -> LogRecord:
    """Convert a real-time TuyaEvent into a LogRecord for storage.

    Generates a deterministic ``event_id`` from a hash of the event's
    identifying fields so that duplicate deliveries are deduplicated by
    the storage layer's UNIQUE constraint.
    """
    # Build a deterministic event_id from the event content.
    id_payload = (
        f"{event.device_id}:{event.timestamp}:"
        f"{event.event_type}:{json.dumps(event.data, sort_keys=True)}"
    )
    event_id = int(hashlib.sha256(id_payload.encode()).hexdigest()[:15], 16)

    return LogRecord(
        device_id=event.device_id,
        event_id=event_id,
        event_time=event.timestamp,
        event_from="ws",
        code=event.event_type,
        value=json.dumps(event.data, sort_keys=True),
        status="ws",
        raw_json=json.dumps(event.raw),
    )


class EventWatcher:
    """Streams real-time device events into SQLite storage."""

    def __init__(self, client: TuyaClient, storage: LogStorage) -> None:
        self._client = client
        self._storage = storage
        self._count = 0

    @property
    def count(self) -> int:
        """Number of events stored in this session."""
        return self._count

    async def run(self, *, duration: float | None = None) -> int:
        """Subscribe to Pulsar events and store them.

        Runs indefinitely unless ``duration`` (seconds) is set.
        Returns the number of events stored.
        """
        if duration is not None:
            try:
                await asyncio.wait_for(
                    self._stream(), timeout=duration,
                )
            except (asyncio.TimeoutError, StopAsyncIteration):
                pass
        else:
            await self._stream()

        logger.info("Watcher stopped — %d events stored", self._count)
        return self._count

    async def _stream(self) -> None:
        """Internal loop: subscribe and store each event."""
        logger.info("Connecting to Tuya Pulsar WebSocket...")
        try:
            async for event in self._client.events.subscribe():
                record = event_to_record(event)
                inserted = self._storage.insert_logs([record])

                if inserted:
                    self._count += 1
                    self._storage.set_device_bookmark(
                        event.device_id, event.timestamp,
                    )

                _log_event(event, new=bool(inserted))
        except websockets.exceptions.InvalidStatus as exc:
            if exc.response.status_code == 401:
                logger.error(
                    "Pulsar WebSocket returned 401 Unauthorized. "
                    "Ensure the Message Service is enabled in your Tuya "
                    "cloud project and message rules are active."
                )
            raise

    async def run_with_callback(
        self,
        callback: Any = None,
        *,
        duration: float | None = None,
    ) -> list[dict[str, Any]]:
        """Subscribe, store, and return event summaries.

        Useful for the agent tool interface where a list of events
        is returned after a fixed duration.
        """
        summaries: list[dict[str, Any]] = []

        async def _gather() -> None:
            async for event in self._client.events.subscribe():
                record = event_to_record(event)
                inserted = self._storage.insert_logs([record])
                if inserted:
                    self._count += 1
                    self._storage.set_device_bookmark(
                        event.device_id, event.timestamp,
                    )
                summaries.append({
                    "device_id": event.device_id,
                    "event_type": event.event_type,
                    "data": event.data,
                    "timestamp": event.timestamp,
                    "stored": bool(inserted),
                })
                _log_event(event, new=bool(inserted))

        try:
            await asyncio.wait_for(
                _gather(), timeout=duration or 60,
            )
        except (asyncio.TimeoutError, StopAsyncIteration):
            pass

        return summaries


def _log_event(event: TuyaEvent, *, new: bool) -> None:
    """Log a single event to the console."""
    tag = "NEW" if new else "DUP"
    data_preview = json.dumps(event.data)
    if len(data_preview) > 80:
        data_preview = data_preview[:77] + "..."
    logger.info(
        "  [%s] %s | %s | %s | %s",
        tag, event.device_id, event.event_type, data_preview, event.timestamp,
    )
