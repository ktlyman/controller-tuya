"""Tests for the SQLite storage layer."""

from __future__ import annotations

from pathlib import Path

from tuya_agent.storage import LogRecord, LogStorage


def _make_record(
    device_id: str = "dev1",
    event_id: int = 1,
    event_time: int = 1700000000000,
    **kwargs: str,
) -> LogRecord:
    return LogRecord(
        device_id=device_id,
        event_id=event_id,
        event_time=event_time,
        event_from=kwargs.get("event_from", "1"),
        code=kwargs.get("code", "switch_1"),
        value=kwargs.get("value", "true"),
        status=kwargs.get("status", "1"),
        raw_json=kwargs.get("raw_json", "{}"),
    )


class TestLogStorage:
    def test_open_creates_tables(self) -> None:
        with LogStorage(Path(":memory:")) as storage:
            # Tables should exist without error.
            row = storage.conn.execute(
                "SELECT COUNT(*) FROM device_logs"
            ).fetchone()
            assert row[0] == 0

    def test_insert_and_retrieve_stats(self) -> None:
        with LogStorage(Path(":memory:")) as storage:
            records = [
                _make_record(),
                _make_record(event_id=2, event_time=1700000001000),
            ]
            inserted = storage.insert_logs(records)
            assert inserted == 2
            stats = storage.get_stats()
            assert stats["total_logs"] == 2
            assert stats["total_devices"] == 1

    def test_deduplication(self) -> None:
        with LogStorage(Path(":memory:")) as storage:
            record = _make_record()
            storage.insert_logs([record])
            inserted = storage.insert_logs([record])
            assert inserted == 0
            assert storage.get_stats()["total_logs"] == 1

    def test_bookmark_round_trip(self) -> None:
        with LogStorage(Path(":memory:")) as storage:
            assert storage.get_device_bookmark("dev1") is None
            storage.set_device_bookmark("dev1", 1700000000000)
            assert storage.get_device_bookmark("dev1") == 1700000000000
            # Update should overwrite.
            storage.set_device_bookmark("dev1", 1700000001000)
            assert storage.get_device_bookmark("dev1") == 1700000001000

    def test_get_all_bookmarks(self) -> None:
        with LogStorage(Path(":memory:")) as storage:
            storage.set_device_bookmark("dev_b", 2000)
            storage.set_device_bookmark("dev_a", 1000)
            bookmarks = storage.get_all_bookmarks()
            assert bookmarks == [("dev_a", 1000), ("dev_b", 2000)]

    def test_run_tracking(self) -> None:
        with LogStorage(Path(":memory:")) as storage:
            run_id = storage.record_run_start()
            assert run_id is not None
            storage.record_run_end(run_id, devices=3, logs=42)
            stats = storage.get_stats()
            assert stats["total_runs"] == 1

    def test_insert_different_devices(self) -> None:
        with LogStorage(Path(":memory:")) as storage:
            records = [
                _make_record(device_id="dev1"),
                _make_record(device_id="dev2"),
            ]
            storage.insert_logs(records)
            stats = storage.get_stats()
            assert stats["total_devices"] == 2

    def test_from_api_factory(self) -> None:
        entry = {
            "event_id": 7,
            "event_time": 1700000000000,
            "event_from": "1",
            "code": "switch_1",
            "value": "true",
            "status": "1",
        }
        record = LogRecord.from_api("dev1", entry)
        assert record.device_id == "dev1"
        assert record.event_id == 7
        assert record.code == "switch_1"
        assert record.value == "true"

    # -- query_logs ----------------------------------------------------------

    def test_query_logs_returns_all(self) -> None:
        with LogStorage(Path(":memory:")) as storage:
            storage.insert_logs([
                _make_record(device_id="d1", event_id=1),
                _make_record(device_id="d2", event_id=2),
            ])
            rows, total = storage.query_logs()
            assert total == 2
            assert len(rows) == 2

    def test_query_logs_filter_by_device(self) -> None:
        with LogStorage(Path(":memory:")) as storage:
            storage.insert_logs([
                _make_record(device_id="d1", event_id=1),
                _make_record(device_id="d2", event_id=2),
            ])
            rows, total = storage.query_logs(device_id="d1")
            assert total == 1
            assert rows[0]["device_id"] == "d1"

    def test_query_logs_filter_by_code(self) -> None:
        with LogStorage(Path(":memory:")) as storage:
            storage.insert_logs([
                _make_record(event_id=1, code="switch_1"),
                _make_record(event_id=2, code="temp_current"),
            ])
            rows, total = storage.query_logs(code="temp_current")
            assert total == 1
            assert rows[0]["code"] == "temp_current"

    def test_query_logs_filter_by_time_range(self) -> None:
        with LogStorage(Path(":memory:")) as storage:
            storage.insert_logs([
                _make_record(event_id=1, event_time=1000),
                _make_record(event_id=2, event_time=2000),
                _make_record(event_id=3, event_time=3000),
            ])
            rows, total = storage.query_logs(
                start_time=1500, end_time=2500,
            )
            assert total == 1
            assert rows[0]["event_time"] == 2000

    def test_query_logs_pagination(self) -> None:
        with LogStorage(Path(":memory:")) as storage:
            storage.insert_logs([
                _make_record(event_id=i, event_time=1000 + i)
                for i in range(5)
            ])
            rows, total = storage.query_logs(limit=2, offset=0)
            assert total == 5
            assert len(rows) == 2

    def test_query_logs_empty(self) -> None:
        with LogStorage(Path(":memory:")) as storage:
            rows, total = storage.query_logs()
            assert total == 0
            assert rows == []

    # -- get_runs ------------------------------------------------------------

    def test_get_runs_returns_completed(self) -> None:
        with LogStorage(Path(":memory:")) as storage:
            rid = storage.record_run_start()
            storage.record_run_end(rid, devices=2, logs=10)
            runs = storage.get_runs()
            assert len(runs) == 1
            assert runs[0]["status"] == "completed"
            assert runs[0]["devices_count"] == 2
            assert runs[0]["logs_collected"] == 10

    def test_get_runs_order_and_limit(self) -> None:
        with LogStorage(Path(":memory:")) as storage:
            for _ in range(3):
                rid = storage.record_run_start()
                storage.record_run_end(rid, devices=1, logs=1)
            runs = storage.get_runs(limit=2)
            assert len(runs) == 2
            # Most recent first.
            assert runs[0]["id"] > runs[1]["id"]

    def test_get_runs_empty(self) -> None:
        with LogStorage(Path(":memory:")) as storage:
            assert storage.get_runs() == []
