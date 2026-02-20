"""Real-time event subscription via Tuya Pulsar (WebSocket)."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import websockets
from websockets.asyncio.client import ClientConnection

if TYPE_CHECKING:
    from tuya_agent.client import TuyaClient

logger = logging.getLogger(__name__)


@dataclass
class TuyaEvent:
    """A decoded real-time event from the Tuya Pulsar stream."""

    event_type: str  # e.g. "dp_report", "online", "offline"
    device_id: str
    product_id: str
    data: dict[str, Any]
    timestamp: int
    raw: dict[str, Any] = field(repr=False)


class EventsMixin:
    """Real-time device event subscription via Tuya's Pulsar WebSocket service."""

    def __init__(self, client: TuyaClient) -> None:
        self._client = client

    def _build_ws_url(self) -> str:
        config = self._client.config
        topic = "event"
        return (
            f"{config.pulsar_url}ws/v2/consumer/persistent/"
            f"{config.access_id}/out/{topic}/{topic}"
            f"-sub?ackTimeoutMillis=3000"
        )

    def _ws_headers(self) -> dict[str, str]:
        config = self._client.config
        password = _ws_password(config.access_id, config.access_secret)
        username = config.access_id
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    async def subscribe(
        self,
        *,
        on_event: Callable[[TuyaEvent], Any] | None = None,
        max_events: int | None = None,
    ) -> AsyncIterator[TuyaEvent]:
        """Connect to the Tuya Pulsar WebSocket and yield events.

        If ``on_event`` is provided it is called for each event in addition to
        yielding.  If ``max_events`` is set the iterator stops after that many
        events.
        """
        url = self._build_ws_url()
        headers = self._ws_headers()

        count = 0
        async for ws in websockets.connect(url, additional_headers=headers):
            try:
                async for raw_msg in ws:
                    try:
                        msg = json.loads(raw_msg)
                        event = _decode_message(msg)
                    except Exception:
                        logger.warning("Failed to decode Pulsar message", exc_info=True)
                        await _ack(ws, msg.get("messageId", ""))
                        continue

                    if event is not None:
                        if on_event:
                            on_event(event)
                        yield event
                        count += 1

                    await _ack(ws, msg.get("messageId", ""))

                    if max_events and count >= max_events:
                        return
            except websockets.ConnectionClosed:
                logger.info("Pulsar WebSocket closed, reconnecting...")
                await asyncio.sleep(1)
                continue

    async def collect(
        self,
        *,
        duration_seconds: float = 60,
        max_events: int | None = None,
    ) -> list[TuyaEvent]:
        """Collect events for up to ``duration_seconds`` and return them as a list."""
        events: list[TuyaEvent] = []

        async def _gather() -> None:
            async for event in self.subscribe(max_events=max_events):
                events.append(event)

        try:
            await asyncio.wait_for(_gather(), timeout=duration_seconds)
        except (asyncio.TimeoutError, StopAsyncIteration):
            pass
        return events


# -- helpers -----------------------------------------------------------------


def _ws_password(access_id: str, access_secret: str) -> str:
    """Compute the Pulsar WebSocket password as md5(access_id + md5(access_secret))."""
    secret_hash = hashlib.md5(access_secret.encode()).hexdigest()[8:24]
    return hashlib.md5((access_id + secret_hash).encode()).hexdigest()[8:24]


def _decode_message(msg: dict[str, Any]) -> TuyaEvent | None:
    payload_b64 = msg.get("payload")
    if not payload_b64:
        return None
    try:
        payload_bytes = base64.b64decode(payload_b64)
        payload = json.loads(payload_bytes)
    except Exception:
        return None

    data = payload.get("data", {})
    return TuyaEvent(
        event_type=payload.get("bizCode", "unknown"),
        device_id=payload.get("devId", ""),
        product_id=payload.get("productKey", ""),
        data=data if isinstance(data, dict) else {"value": data},
        timestamp=payload.get("ts", int(time.time() * 1000)),
        raw=payload,
    )


async def _ack(ws: ClientConnection, message_id: str) -> None:
    if message_id:
        await ws.send(json.dumps({"messageId": message_id}))
