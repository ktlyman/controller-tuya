"""Periodic log collector for long-term Tuya device event retention."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from tuya_agent.client import TuyaAPIError, TuyaClient
from tuya_agent.storage import LogRecord, LogStorage

logger = logging.getLogger(__name__)

# Tuya free tier retains logs for 7 days.
MAX_LOOKBACK_MS = 7 * 24 * 60 * 60 * 1000
DEFAULT_POLL_INTERVAL = 6 * 60 * 60  # 6 hours
REQUEST_DELAY = 2.5  # seconds between API calls
PAGE_SIZE = 50
MAX_PAGES_PER_DEVICE = 100
MAX_RETRIES = 3

RATE_LIMIT_CODE = 40000309


@dataclass
class CollectorConfig:
    """Configuration for the log collector."""

    poll_interval: int = DEFAULT_POLL_INTERVAL
    request_delay: float = REQUEST_DELAY
    page_size: int = PAGE_SIZE
    event_types: str = "1,2,3,4,5,6,7,8,9,10"
    lookback_days: int = 7


@dataclass
class CollectionResult:
    """Summary of a single collection run."""

    devices_found: int = 0
    devices_collected: int = 0
    devices_failed: int = 0
    logs_collected: int = 0
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


class LogCollector:
    """Collects device event logs from Tuya and stores them in SQLite."""

    def __init__(
        self,
        client: TuyaClient,
        storage: LogStorage,
        config: CollectorConfig | None = None,
    ) -> None:
        self._client = client
        self._storage = storage
        self._config = config or CollectorConfig()

    # -- Device discovery ----------------------------------------------------

    async def discover_devices(self) -> list[dict[str, Any]]:
        """List all devices in the cloud project, handling pagination."""
        devices: list[dict[str, Any]] = []
        last_row_key: str | None = None

        while True:
            result = await self._client.devices.list(
                page_size=20, last_row_key=last_row_key,
            )
            # The API may return a plain list or a dict with "list" key.
            if isinstance(result, list):
                devices.extend(result)
                break
            batch = result.get("list", [])
            devices.extend(batch)

            last_row_key = result.get("last_row_key", "")
            if not batch or not last_row_key:
                break
            await asyncio.sleep(self._config.request_delay)

        logger.info("Discovered %d devices", len(devices))
        return devices

    # -- Per-device log collection -------------------------------------------

    async def collect_device_logs(
        self,
        device_id: str,
        start_time: int,
        end_time: int,
    ) -> list[LogRecord]:
        """Fetch all log pages for a device within the time range."""
        records: list[LogRecord] = []
        last_row_key: str | None = None
        prev_row_key: str | None = None
        page = 0

        while page < MAX_PAGES_PER_DEVICE:
            data = await self._fetch_logs_page(
                device_id, start_time, end_time, last_row_key,
            )
            if data is None:
                break

            for entry in data.get("logs", []):
                records.append(LogRecord.from_api(device_id, entry))

            if not data.get("has_next"):
                break

            new_row_key = data.get("next_row_key", "")
            if not new_row_key or new_row_key == prev_row_key:
                break

            prev_row_key = last_row_key
            last_row_key = new_row_key
            page += 1
            await asyncio.sleep(self._config.request_delay)

        return records

    async def _fetch_logs_page(
        self,
        device_id: str,
        start_time: int,
        end_time: int,
        last_row_key: str | None,
    ) -> dict[str, Any] | None:
        """Fetch a single page of logs with retry on rate limit."""
        for attempt in range(MAX_RETRIES):
            try:
                return await self._client.logs.get_device_logs(
                    device_id,
                    start_time=start_time,
                    end_time=end_time,
                    event_types=self._config.event_types,
                    page_size=self._config.page_size,
                    last_row_key=last_row_key,
                )
            except TuyaAPIError as exc:
                if exc.code == RATE_LIMIT_CODE:
                    delay = 10 * (2 ** attempt)
                    logger.warning(
                        "Rate limited on %s, retrying in %ds (attempt %d/%d)",
                        device_id, delay, attempt + 1, MAX_RETRIES,
                    )
                    await asyncio.sleep(delay)
                    continue
                raise
        logger.error("Exhausted retries for device %s", device_id)
        return None

    # -- Full collection run -------------------------------------------------

    async def collect_all(self) -> CollectionResult:
        """Run a one-shot collection across all devices."""
        t0 = time.monotonic()
        result = CollectionResult()
        run_id = self._storage.record_run_start()

        try:
            devices = await self.discover_devices()
            result.devices_found = len(devices)

            for device in devices:
                device_id = device.get("id", "")
                device_name = device.get("customName") or device.get("name", "")
                if not device_id:
                    continue

                try:
                    await self._collect_one_device(
                        device_id, device_name, result,
                    )
                except Exception as exc:
                    result.devices_failed += 1
                    msg = f"{device_name} ({device_id}): {exc}"
                    result.errors.append(msg)
                    logger.error("Failed to collect %s: %s", device_id, exc)

                await asyncio.sleep(self._config.request_delay)
        finally:
            result.duration_seconds = time.monotonic() - t0
            status = "completed" if not result.errors else "completed_with_errors"
            self._storage.record_run_end(
                run_id,
                devices=result.devices_collected,
                logs=result.logs_collected,
                status=status,
            )

        logger.info(
            "Collection complete: %d logs from %d/%d devices in %.1fs",
            result.logs_collected,
            result.devices_collected,
            result.devices_found,
            result.duration_seconds,
        )
        return result

    async def _collect_one_device(
        self,
        device_id: str,
        device_name: str,
        result: CollectionResult,
    ) -> None:
        """Collect logs for a single device and store them."""
        now_ms = int(time.time() * 1000)
        bookmark = self._storage.get_device_bookmark(device_id)

        if bookmark is not None:
            # Overlap by 1 second for same-millisecond edge cases.
            start_time = bookmark - 1000
        else:
            lookback_ms = self._config.lookback_days * 24 * 60 * 60 * 1000
            start_time = now_ms - lookback_ms

        records = await self.collect_device_logs(
            device_id, start_time, now_ms,
        )

        if records:
            inserted = self._storage.insert_logs(records)
            max_time = max(r.event_time for r in records)
            self._storage.set_device_bookmark(device_id, max_time)
            result.logs_collected += inserted
            logger.info(
                "  %s: %d logs fetched, %d new",
                device_name or device_id, len(records), inserted,
            )
        else:
            logger.debug("  %s: no new logs", device_name or device_id)

        result.devices_collected += 1

    # -- Daemon mode ---------------------------------------------------------

    async def run_daemon(self) -> None:
        """Run the collector in a loop, sleeping between runs."""
        logger.info(
            "Starting log collector daemon (interval=%ds)",
            self._config.poll_interval,
        )
        while True:
            try:
                result = await self.collect_all()
                if result.errors:
                    for err in result.errors:
                        logger.warning("  Error: %s", err)
            except Exception:
                logger.exception("Collection run failed")

            logger.info(
                "Sleeping %ds until next run...",
                self._config.poll_interval,
            )
            await asyncio.sleep(self._config.poll_interval)
