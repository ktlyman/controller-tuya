"""Tests for the CLI entry point (__main__.py)."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tuya_agent.__main__ import _run_status, main
from tuya_agent.collector import CollectionResult
from tuya_agent.storage import LogStorage


class TestMainParser:
    """Verify argument parsing and subcommand dispatch."""

    def test_no_command_prints_help_and_exits(self, capsys: pytest.CaptureFixture[str]) -> None:
        with patch("sys.argv", ["tuya_agent"]):
            with pytest.raises(SystemExit, match="1"):
                main()

    def test_collect_parses_defaults(self) -> None:
        with (
            patch("sys.argv", ["tuya_agent", "collect"]),
            patch("tuya_agent.__main__.asyncio") as mock_asyncio,
            patch("tuya_agent.__main__.logging"),
        ):
            main()
            mock_asyncio.run.assert_called_once()

    def test_serve_parses_host_port(self) -> None:
        with (
            patch("sys.argv", [
                "tuya_agent", "serve", "--host", "0.0.0.0", "--port", "9000",
            ]),
            patch("tuya_agent.__main__._run_serve") as mock_serve,
            patch("tuya_agent.__main__.logging"),
        ):
            main()
            args = mock_serve.call_args[0][0]
            assert args.host == "0.0.0.0"
            assert args.port == 9000

    def test_watch_parses_duration(self) -> None:
        with (
            patch("sys.argv", ["tuya_agent", "watch", "--duration", "30"]),
            patch("tuya_agent.__main__.asyncio") as mock_asyncio,
            patch("tuya_agent.__main__.logging"),
        ):
            main()
            mock_asyncio.run.assert_called_once()


class TestRunStatus:
    """Test the status subcommand output."""

    def test_status_prints_stats(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        db_path = tmp_path / "test.db"
        with LogStorage(db_path):
            pass  # Just create the empty DB

        args = argparse.Namespace(db=db_path)
        _run_status(args)

        output = capsys.readouterr().out
        assert "Total logs:" in output
        assert "Total devices:" in output
        assert "Total runs:" in output

    def test_status_shows_bookmarks(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        db_path = tmp_path / "test.db"
        with LogStorage(db_path) as storage:
            storage.set_device_bookmark("dev1", 1700000000000)

        args = argparse.Namespace(db=db_path)
        _run_status(args)

        output = capsys.readouterr().out
        assert "dev1" in output
        assert "Device bookmarks" in output


class TestRunCollect:
    """Test the collect subcommand."""

    @pytest.mark.asyncio
    async def test_collect_oneshot(self, tmp_path: Path) -> None:
        from tuya_agent.__main__ import _run_collect

        mock_result = CollectionResult(
            devices_found=3,
            devices_collected=3,
            logs_collected=10,
            duration_seconds=1.5,
        )

        with (
            patch("tuya_agent.__main__.TuyaClient") as mock_cls,
            patch("tuya_agent.__main__.LogCollector") as mock_col_cls,
        ):
            mock_client_inst = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client_inst,
            )
            mock_cls.return_value.__aexit__ = AsyncMock()

            mock_collector = MagicMock()
            mock_collector.collect_all = AsyncMock(
                return_value=mock_result,
            )
            mock_col_cls.return_value = mock_collector

            args = argparse.Namespace(
                db=tmp_path / "test.db",
                daemon=False,
                interval=21600,
                delay=2.5,
                lookback_days=7,
                event_types="1,2,3",
            )
            await _run_collect(args)
            mock_collector.collect_all.assert_called_once()
