"""Tests for the real-time event watcher."""

from __future__ import annotations

import json
from pathlib import Path

from tuya_agent.events import TuyaEvent
from tuya_agent.storage import LogStorage
from tuya_agent.watcher import event_to_record


def _make_event(
    device_id: str = "dev1",
    event_type: str = "dp_report",
    data: dict | None = None,
    timestamp: int = 1700000000000,
    product_id: str = "prod1",
) -> TuyaEvent:
    if data is None:
        data = {"switch_1": True}
    return TuyaEvent(
        event_type=event_type,
        device_id=device_id,
        product_id=product_id,
        data=data,
        timestamp=timestamp,
        raw={"devId": device_id, "bizCode": event_type, "ts": timestamp},
    )


class TestEventToRecord:
    def test_basic_conversion(self) -> None:
        event = _make_event()
        record = event_to_record(event)
        assert record.device_id == "dev1"
        assert record.event_time == 1700000000000
        assert record.event_from == "ws"
        assert record.code == "dp_report"
        assert record.status == "ws"
        assert json.loads(record.value) == {"switch_1": True}
        assert record.raw_json  # non-empty

    def test_event_id_is_deterministic(self) -> None:
        event = _make_event()
        r1 = event_to_record(event)
        r2 = event_to_record(event)
        assert r1.event_id == r2.event_id

    def test_different_events_get_different_ids(self) -> None:
        e1 = _make_event(timestamp=1700000000000)
        e2 = _make_event(timestamp=1700000001000)
        assert event_to_record(e1).event_id != event_to_record(e2).event_id

    def test_different_data_get_different_ids(self) -> None:
        e1 = _make_event(data={"switch_1": True})
        e2 = _make_event(data={"switch_1": False})
        assert event_to_record(e1).event_id != event_to_record(e2).event_id

    def test_event_id_is_positive_integer(self) -> None:
        record = event_to_record(_make_event())
        assert isinstance(record.event_id, int)
        assert record.event_id > 0

    def test_raw_json_roundtrips(self) -> None:
        event = _make_event()
        record = event_to_record(event)
        parsed = json.loads(record.raw_json)
        assert parsed["devId"] == "dev1"
        assert parsed["bizCode"] == "dp_report"


class TestWatcherStorage:
    def test_converted_record_inserts(self) -> None:
        event = _make_event()
        record = event_to_record(event)
        with LogStorage(Path(":memory:")) as storage:
            inserted = storage.insert_logs([record])
            assert inserted == 1

    def test_dedup_same_event(self) -> None:
        event = _make_event()
        record = event_to_record(event)
        with LogStorage(Path(":memory:")) as storage:
            storage.insert_logs([record])
            dup = storage.insert_logs([record])
            assert dup == 0
            assert storage.get_stats()["total_logs"] == 1

    def test_multiple_events_insert(self) -> None:
        events = [
            _make_event(device_id="dev1", timestamp=1700000000000),
            _make_event(device_id="dev2", timestamp=1700000001000),
            _make_event(
                device_id="dev1",
                timestamp=1700000002000,
                event_type="online",
                data={},
            ),
        ]
        records = [event_to_record(e) for e in events]
        with LogStorage(Path(":memory:")) as storage:
            inserted = storage.insert_logs(records)
            assert inserted == 3
            stats = storage.get_stats()
            assert stats["total_logs"] == 3
            assert stats["total_devices"] == 2

    def test_ws_events_distinct_from_api_events(self) -> None:
        """WebSocket records should have event_from='ws' and status='ws'."""
        event = _make_event()
        record = event_to_record(event)
        assert record.event_from == "ws"
        assert record.status == "ws"
