"""Agent-facing tool definitions for the Tuya ecosystem.

Each tool is a standalone async function with a JSON-schema-style descriptor
that agents can discover and invoke. The ``TOOLS`` list provides machine-
readable definitions compatible with common agent frameworks.
"""

from __future__ import annotations

from typing import Any

from tuya_agent.client import TuyaClient

# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = []


def _register(schema: dict[str, Any]):
    """Decorator that adds a tool schema to the TOOLS registry."""

    def decorator(fn):
        schema["function"] = fn.__name__
        TOOLS.append(schema)
        return fn

    return decorator


# ---------------------------------------------------------------------------
# Device tools
# ---------------------------------------------------------------------------


@_register(
    {
        "name": "list_devices",
        "description": (
            "List all Tuya devices in the cloud project. "
            "Returns device IDs, names, categories, and online status."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "page_size": {
                    "type": "integer",
                    "description": "Number of devices per page (default 20).",
                },
                "last_row_key": {
                    "type": "string",
                    "description": "Pagination cursor from a previous response.",
                },
            },
        },
    }
)
async def list_devices(
    client: TuyaClient,
    page_size: int = 20,
    last_row_key: str | None = None,
) -> dict[str, Any]:
    return await client.devices.list(page_size=page_size, last_row_key=last_row_key)


@_register(
    {
        "name": "get_device",
        "description": (
            "Get detailed information about a specific device including "
            "its current status, category, product info, and network state."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "The Tuya device ID.",
                },
            },
            "required": ["device_id"],
        },
    }
)
async def get_device(client: TuyaClient, device_id: str) -> dict[str, Any]:
    return await client.devices.get(device_id)


@_register(
    {
        "name": "get_device_status",
        "description": (
            "Get the current data-point values (status) of a device. "
            "Returns a list of code/value pairs."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "The Tuya device ID.",
                },
            },
            "required": ["device_id"],
        },
    }
)
async def get_device_status(
    client: TuyaClient, device_id: str
) -> list[dict[str, Any]]:
    return await client.devices.get_status(device_id)


@_register(
    {
        "name": "get_device_specification",
        "description": (
            "Get the full specification of a device including its "
            "supported instructions and status data points."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "The Tuya device ID.",
                },
            },
            "required": ["device_id"],
        },
    }
)
async def get_device_specification(
    client: TuyaClient, device_id: str
) -> dict[str, Any]:
    return await client.devices.get_specification(device_id)


@_register(
    {
        "name": "control_device",
        "description": (
            "Send control commands to a Tuya device. "
            "Each command specifies a data-point code and value."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "The Tuya device ID.",
                },
                "commands": {
                    "type": "array",
                    "description": (
                        "List of command objects with "
                        '"code" (string) and "value" (any).'
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"},
                            "value": {},
                        },
                        "required": ["code", "value"],
                    },
                },
            },
            "required": ["device_id", "commands"],
        },
    }
)
async def control_device(
    client: TuyaClient,
    device_id: str,
    commands: list[dict[str, Any]],
) -> bool:
    return await client.devices.send_commands(device_id, commands)


@_register(
    {
        "name": "get_device_functions",
        "description": (
            "Get the writable functions (commands) a device supports. "
            "Use this to discover what codes and value ranges "
            "you can send to control_device."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "The Tuya device ID.",
                },
            },
            "required": ["device_id"],
        },
    }
)
async def get_device_functions(
    client: TuyaClient, device_id: str
) -> dict[str, Any]:
    return await client.devices.get_functions(device_id)


@_register(
    {
        "name": "get_sub_devices",
        "description": (
            "List sub-devices connected to a gateway device. "
            "Use this for Zigbee or BLE mesh gateways to "
            "discover their child devices."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "gateway_id": {
                    "type": "string",
                    "description": "The gateway device ID.",
                },
            },
            "required": ["gateway_id"],
        },
    }
)
async def get_sub_devices(
    client: TuyaClient, gateway_id: str
) -> list[dict[str, Any]]:
    return await client.devices.get_sub_devices(gateway_id)


# ---------------------------------------------------------------------------
# Logging tools
# ---------------------------------------------------------------------------


@_register(
    {
        "name": "get_device_event_logs",
        "description": (
            "Query device event logs such as online, offline, "
            "activation, and reset events within a time range."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "The Tuya device ID.",
                },
                "start_time": {
                    "type": "integer",
                    "description": "Start time (13-digit ms timestamp).",
                },
                "end_time": {
                    "type": "integer",
                    "description": "End time (13-digit ms timestamp).",
                },
                "event_types": {
                    "type": "string",
                    "description": "Comma-separated event type codes.",
                },
                "page_size": {
                    "type": "integer",
                    "description": "Results per page (default 20).",
                },
            },
            "required": ["device_id", "start_time", "end_time"],
        },
    }
)
async def get_device_event_logs(
    client: TuyaClient,
    device_id: str,
    start_time: int,
    end_time: int,
    event_types: str = "1,2,3,4,5,6,7,8,9,10",
    page_size: int = 20,
) -> dict[str, Any]:
    return await client.logs.get_device_logs(
        device_id,
        start_time=start_time,
        end_time=end_time,
        event_types=event_types,
        page_size=page_size,
    )


@_register(
    {
        "name": "get_device_report_logs",
        "description": (
            "Query historical data-point status reports for a device. "
            "Shows the history of value changes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "The Tuya device ID.",
                },
                "start_time": {
                    "type": "integer",
                    "description": "Start time (13-digit ms timestamp).",
                },
                "end_time": {
                    "type": "integer",
                    "description": "End time (13-digit ms timestamp).",
                },
                "codes": {
                    "type": "string",
                    "description": "Comma-separated DP codes to filter.",
                },
                "page_size": {
                    "type": "integer",
                    "description": "Results per page (default 20).",
                },
            },
            "required": ["device_id", "start_time", "end_time"],
        },
    }
)
async def get_device_report_logs(
    client: TuyaClient,
    device_id: str,
    start_time: int,
    end_time: int,
    codes: str | None = None,
    page_size: int = 20,
) -> dict[str, Any]:
    return await client.logs.get_report_logs(
        device_id,
        start_time=start_time,
        end_time=end_time,
        codes=codes,
        page_size=page_size,
    )


@_register(
    {
        "name": "get_device_statistics",
        "description": (
            "Get aggregated statistics for a device data point. "
            "Supports 15-min, daily, weekly, and monthly intervals."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "The Tuya device ID.",
                },
                "code": {
                    "type": "string",
                    "description": "DP code to aggregate.",
                },
                "interval": {
                    "type": "string",
                    "enum": ["quarters", "days", "weeks", "months"],
                    "description": "Aggregation interval (default: days).",
                },
                "start_time": {
                    "type": "integer",
                    "description": "Start time (13-digit ms timestamp).",
                },
                "end_time": {
                    "type": "integer",
                    "description": "End time (13-digit ms timestamp).",
                },
            },
            "required": ["device_id", "code", "start_time", "end_time"],
        },
    }
)
async def get_device_statistics(
    client: TuyaClient,
    device_id: str,
    code: str,
    start_time: int,
    end_time: int,
    interval: str = "days",
) -> dict[str, Any]:
    return await client.logs.get_statistics(
        device_id,
        interval=interval,
        start_time=start_time,
        end_time=end_time,
        code=code,
    )


# ---------------------------------------------------------------------------
# Scene / automation tools
# ---------------------------------------------------------------------------


@_register(
    {
        "name": "list_scenes",
        "description": (
            "List scenes and automations in a space using the v2.0 Cloud API. "
            "Returns rules with type, status, name, and actions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "space_id": {
                    "type": "string",
                    "description": (
                        "The Tuya space ID (bindSpaceId from a device)."
                    ),
                },
                "rule_type": {
                    "type": "string",
                    "description": (
                        "Filter by type: 'scene' for tap-to-run, "
                        "'automation' for automations, or '' for both."
                    ),
                },
            },
            "required": ["space_id"],
        },
    }
)
async def list_scenes(
    client: TuyaClient,
    space_id: str,
    rule_type: str = "",
) -> dict[str, Any]:
    return await client.scenes.list_rules(space_id, rule_type=rule_type)


@_register(
    {
        "name": "trigger_scene",
        "description": "Trigger (execute) a scene or automation rule by its ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "rule_id": {
                    "type": "string",
                    "description": "The rule/scene ID to trigger.",
                },
            },
            "required": ["rule_id"],
        },
    }
)
async def trigger_scene(
    client: TuyaClient, rule_id: str
) -> bool:
    return await client.scenes.trigger_rule(rule_id)


# ---------------------------------------------------------------------------
# Real-time event tools
# ---------------------------------------------------------------------------


@_register(
    {
        "name": "collect_realtime_events",
        "description": (
            "Collect real-time device events for a specified duration. "
            "Connects to Tuya's Pulsar message service."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "duration_seconds": {
                    "type": "number",
                    "description": "How long to listen (default 60s).",
                },
                "max_events": {
                    "type": "integer",
                    "description": "Stop after this many events.",
                },
            },
        },
    }
)
async def collect_realtime_events(
    client: TuyaClient,
    duration_seconds: float = 60,
    max_events: int | None = None,
) -> list[dict[str, Any]]:
    events = await client.events.collect(
        duration_seconds=duration_seconds,
        max_events=max_events,
    )
    return [
        {
            "event_type": e.event_type,
            "device_id": e.device_id,
            "product_id": e.product_id,
            "data": e.data,
            "timestamp": e.timestamp,
        }
        for e in events
    ]


# ---------------------------------------------------------------------------
# Log collector tools
# ---------------------------------------------------------------------------


@_register(
    {
        "name": "collect_logs",
        "description": (
            "Trigger a one-shot collection of device event logs from all devices. "
            "Stores logs in a local SQLite database for long-term retention."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "db_path": {
                    "type": "string",
                    "description": "Path to SQLite database (default: tuya_logs.db).",
                },
                "lookback_days": {
                    "type": "integer",
                    "description": (
                        "Days to look back on first collection (default: 7)."
                    ),
                },
            },
        },
    }
)
async def collect_logs(
    client: TuyaClient,
    db_path: str = "tuya_logs.db",
    lookback_days: int = 7,
) -> dict[str, Any]:
    from pathlib import Path

    from tuya_agent.collector import CollectorConfig, LogCollector
    from tuya_agent.storage import LogStorage

    config = CollectorConfig(lookback_days=lookback_days)
    with LogStorage(Path(db_path)) as storage:
        collector = LogCollector(client, storage, config)
        result = await collector.collect_all()
    return {
        "devices_found": result.devices_found,
        "devices_collected": result.devices_collected,
        "logs_collected": result.logs_collected,
        "duration_seconds": result.duration_seconds,
        "errors": result.errors,
    }


@_register(
    {
        "name": "get_collection_status",
        "description": (
            "Get statistics about the local log collection database "
            "including total logs stored and per-device bookmark status."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "db_path": {
                    "type": "string",
                    "description": "Path to SQLite database (default: tuya_logs.db).",
                },
            },
        },
    }
)
async def get_collection_status(
    client: TuyaClient,
    db_path: str = "tuya_logs.db",
) -> dict[str, Any]:
    from pathlib import Path

    from tuya_agent.storage import LogStorage

    with LogStorage(Path(db_path)) as storage:
        stats = storage.get_stats()
        bookmarks = storage.get_all_bookmarks()
    stats["bookmarks"] = {did: ts for did, ts in bookmarks}
    return stats


@_register(
    {
        "name": "query_logs",
        "description": (
            "Search the local SQLite log database with optional filters. "
            "Returns matching log entries and total count."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "db_path": {
                    "type": "string",
                    "description": (
                        "Path to SQLite database (default: tuya_logs.db)."
                    ),
                },
                "device_id": {
                    "type": "string",
                    "description": "Filter by device ID.",
                },
                "start_time": {
                    "type": "integer",
                    "description": "Start time (13-digit ms timestamp).",
                },
                "end_time": {
                    "type": "integer",
                    "description": "End time (13-digit ms timestamp).",
                },
                "code": {
                    "type": "string",
                    "description": "Filter by DP code.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 100).",
                },
                "offset": {
                    "type": "integer",
                    "description": "Pagination offset (default 0).",
                },
            },
        },
    }
)
async def query_logs(
    client: TuyaClient,
    db_path: str = "tuya_logs.db",
    device_id: str | None = None,
    start_time: int | None = None,
    end_time: int | None = None,
    code: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    from pathlib import Path

    from tuya_agent.storage import LogStorage

    with LogStorage(Path(db_path)) as storage:
        rows, total = storage.query_logs(
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            code=code,
            limit=limit,
            offset=offset,
        )
    return {"logs": rows, "total": total}


@_register(
    {
        "name": "get_collection_runs",
        "description": (
            "Get recent log collection run history from the local "
            "database, including timestamps, device counts, and status."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "db_path": {
                    "type": "string",
                    "description": (
                        "Path to SQLite database (default: tuya_logs.db)."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": "Max runs to return (default 50).",
                },
            },
        },
    }
)
async def get_collection_runs(
    client: TuyaClient,
    db_path: str = "tuya_logs.db",
    limit: int = 50,
) -> list[dict[str, Any]]:
    from pathlib import Path

    from tuya_agent.storage import LogStorage

    with LogStorage(Path(db_path)) as storage:
        return storage.get_runs(limit=limit)


# ---------------------------------------------------------------------------
# Space tools
# ---------------------------------------------------------------------------


@_register(
    {
        "name": "resolve_space",
        "description": (
            "Resolve a Tuya space ID to its details including name "
            "and location. Use device bindSpaceId as the space_id."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "space_id": {
                    "type": "string",
                    "description": "The Tuya space ID.",
                },
            },
            "required": ["space_id"],
        },
    }
)
async def resolve_space(
    client: TuyaClient, space_id: str
) -> dict[str, Any]:
    return await client.spaces.get(space_id)


# ---------------------------------------------------------------------------
# Real-time watcher tools
# ---------------------------------------------------------------------------


@_register(
    {
        "name": "watch_realtime_events",
        "description": (
            "Subscribe to real-time Tuya Pulsar events and store them in "
            "a local SQLite database. Returns event summaries after the "
            "specified duration."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "db_path": {
                    "type": "string",
                    "description": (
                        "Path to the SQLite database (default: tuya_logs.db)."
                    ),
                },
                "duration_seconds": {
                    "type": "number",
                    "description": (
                        "How long to listen for events in seconds (default: 60)."
                    ),
                },
            },
        },
    }
)
async def watch_realtime_events(
    client: TuyaClient,
    db_path: str = "tuya_logs.db",
    duration_seconds: float = 60,
) -> dict[str, Any]:
    from pathlib import Path

    from tuya_agent.storage import LogStorage
    from tuya_agent.watcher import EventWatcher

    with LogStorage(Path(db_path)) as storage:
        watcher = EventWatcher(client, storage)
        summaries = await watcher.run_with_callback(
            duration=duration_seconds,
        )
    return {
        "events_stored": watcher.count,
        "duration_seconds": duration_seconds,
        "events": summaries,
    }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


async def dispatch(
    client: TuyaClient, tool_name: str, arguments: dict[str, Any]
) -> Any:
    """Look up a tool by name and call it with the given arguments.

    This is the primary entry point for agent frameworks to invoke tools.
    """
    for tool in TOOLS:
        if tool["name"] == tool_name:
            fn = globals()[tool["function"]]
            return await fn(client, **arguments)
    raise ValueError(f"Unknown tool: {tool_name}")
