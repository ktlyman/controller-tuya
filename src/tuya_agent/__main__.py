"""CLI entry point for the Tuya Agent tools.

Usage::

    python -m tuya_agent collect [--daemon] [--interval 21600] [--db tuya_logs.db]
    python -m tuya_agent watch   [--db tuya_logs.db] [--duration SECONDS]
    python -m tuya_agent serve   [--host 127.0.0.1] [--port 8000] [--db tuya_logs.db]
    python -m tuya_agent status  [--db tuya_logs.db]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from tuya_agent.client import TuyaClient
from tuya_agent.collector import CollectorConfig, LogCollector
from tuya_agent.storage import LogStorage
from tuya_agent.watcher import EventWatcher


def main() -> None:
    """Parse arguments and dispatch to the appropriate subcommand."""
    parser = argparse.ArgumentParser(
        prog="tuya_agent",
        description="Tuya IoT agent tools CLI",
    )
    sub = parser.add_subparsers(dest="command")

    # -- collect -------------------------------------------------------------
    collect_p = sub.add_parser("collect", help="Collect device event logs")
    collect_p.add_argument(
        "--daemon", action="store_true", help="Run continuously",
    )
    collect_p.add_argument(
        "--interval", type=int, default=21600,
        help="Poll interval in seconds for daemon mode (default: 21600)",
    )
    collect_p.add_argument(
        "--db", type=Path, default=Path("tuya_logs.db"),
        help="SQLite database path (default: tuya_logs.db)",
    )
    collect_p.add_argument(
        "--delay", type=float, default=2.5,
        help="Delay between API calls in seconds (default: 2.5)",
    )
    collect_p.add_argument(
        "--lookback-days", type=int, default=7,
        help="How far back to look on first run (default: 7)",
    )
    collect_p.add_argument(
        "--event-types", type=str, default="1,2,3,4,5,6,7,8,9,10",
        help="Comma-separated event type codes",
    )

    # -- watch ---------------------------------------------------------------
    watch_p = sub.add_parser(
        "watch", help="Stream real-time device events into SQLite",
    )
    watch_p.add_argument(
        "--db", type=Path, default=Path("tuya_logs.db"),
        help="SQLite database path (default: tuya_logs.db)",
    )
    watch_p.add_argument(
        "--duration", type=float, default=None,
        help="Stop after N seconds (default: run forever)",
    )

    # -- serve ---------------------------------------------------------------
    serve_p = sub.add_parser(
        "serve", help="Start the web dashboard server",
    )
    serve_p.add_argument(
        "--host", type=str, default="127.0.0.1",
        help="Bind address (default: 127.0.0.1)",
    )
    serve_p.add_argument(
        "--port", type=int, default=8000,
        help="Port (default: 8000)",
    )
    serve_p.add_argument(
        "--db", type=Path, default=Path("tuya_logs.db"),
        help="SQLite database path (default: tuya_logs.db)",
    )

    # -- status --------------------------------------------------------------
    status_p = sub.add_parser("status", help="Show collection status")
    status_p.add_argument(
        "--db", type=Path, default=Path("tuya_logs.db"),
        help="SQLite database path",
    )

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    if args.command == "collect":
        asyncio.run(_run_collect(args))
    elif args.command == "watch":
        asyncio.run(_run_watch(args))
    elif args.command == "serve":
        _run_serve(args)
    elif args.command == "status":
        _run_status(args)


async def _run_collect(args: argparse.Namespace) -> None:
    config = CollectorConfig(
        poll_interval=args.interval,
        request_delay=args.delay,
        lookback_days=args.lookback_days,
        event_types=args.event_types,
    )
    with LogStorage(args.db) as storage:
        async with TuyaClient() as client:
            collector = LogCollector(client, storage, config)
            if args.daemon:
                await collector.run_daemon()
            else:
                result = await collector.collect_all()
                print(
                    f"Collected {result.logs_collected} logs "
                    f"from {result.devices_collected}/{result.devices_found} "
                    f"devices in {result.duration_seconds:.1f}s"
                )
                if result.errors:
                    for err in result.errors:
                        print(f"  Error: {err}")


async def _run_watch(args: argparse.Namespace) -> None:
    import websockets

    with LogStorage(args.db) as storage:
        async with TuyaClient() as client:
            watcher = EventWatcher(client, storage)
            label = (
                f"{args.duration:.0f}s" if args.duration else "indefinitely"
            )
            print(f"Watching real-time events ({label}) — Ctrl+C to stop")
            try:
                count = await watcher.run(duration=args.duration)
            except KeyboardInterrupt:
                count = watcher.count
            except websockets.exceptions.InvalidStatus as exc:
                if exc.response.status_code == 401:
                    print(
                        "\nError: Pulsar returned 401 Unauthorized.\n"
                        "Make sure the Message Service is enabled in your "
                        "Tuya cloud project\nand that message rules are "
                        "active for your data center region."
                    )
                    sys.exit(1)
                raise
            print(f"\nDone — {count} events stored to {args.db}")


def _run_serve(args: argparse.Namespace) -> None:
    import uvicorn

    from tuya_agent.server import create_app

    app = create_app(db_path=args.db)
    uvicorn.run(app, host=args.host, port=args.port)


def _run_status(args: argparse.Namespace) -> None:
    with LogStorage(args.db) as storage:
        stats = storage.get_stats()
        print(f"Database: {args.db}")
        print(f"Total logs:     {stats['total_logs']:,}")
        print(f"Total devices:  {stats['total_devices']}")
        print(f"Total runs:     {stats['total_runs']}")

        bookmarks = storage.get_all_bookmarks()
        if bookmarks:
            print("\nDevice bookmarks (last collected event):")
            for device_id, ts in bookmarks:
                dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                print(f"  {device_id}: {dt.isoformat()}")


if __name__ == "__main__":
    main()
