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
# Timer tools
# ---------------------------------------------------------------------------


@_register(
    {
        "name": "list_device_timers",
        "description": (
            "List all scheduled timer tasks for a device. "
            "Returns timer IDs, schedules, and associated commands."
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
async def list_device_timers(
    client: TuyaClient, device_id: str
) -> list[dict[str, Any]]:
    return await client.timers.list_tasks(device_id)


@_register(
    {
        "name": "add_device_timer",
        "description": (
            "Create a scheduled timer on a device. Specify when "
            "and what commands to execute on a schedule."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "The Tuya device ID.",
                },
                "loops": {
                    "type": "string",
                    "description": (
                        "7-char day-of-week mask (e.g. '0111110' "
                        "for Mon-Fri). '0000000' for one-shot."
                    ),
                },
                "time_zone": {
                    "type": "string",
                    "description": "IANA time zone (e.g. 'America/Los_Angeles').",
                },
                "functions": {
                    "type": "array",
                    "description": (
                        "Commands to run when timer fires. "
                        "Each has 'code' and 'value'."
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
            "required": ["device_id", "functions"],
        },
    }
)
async def add_device_timer(
    client: TuyaClient,
    device_id: str,
    functions: list[dict[str, Any]],
    loops: str = "0000000",
    time_zone: str = "",
) -> dict[str, Any]:
    return await client.timers.add_task(
        device_id, loops=loops, time_zone=time_zone, functions=functions,
    )


@_register(
    {
        "name": "toggle_device_timer",
        "description": "Enable or disable a specific timer task on a device.",
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "The Tuya device ID.",
                },
                "timer_id": {
                    "type": "string",
                    "description": "The timer task ID.",
                },
                "state": {
                    "type": "boolean",
                    "description": "True to enable, false to disable.",
                },
            },
            "required": ["device_id", "timer_id", "state"],
        },
    }
)
async def toggle_device_timer(
    client: TuyaClient,
    device_id: str,
    timer_id: str,
    state: bool,
) -> bool:
    return await client.timers.set_task_state(
        device_id, timer_id=timer_id, state=state,
    )


# ---------------------------------------------------------------------------
# Weather tools
# ---------------------------------------------------------------------------


@_register(
    {
        "name": "get_weather_forecast",
        "description": (
            "Get weather forecast for a Tuya city ID. "
            "Returns temperature, humidity, conditions, etc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "city_id": {
                    "type": "string",
                    "description": "The Tuya city ID.",
                },
            },
            "required": ["city_id"],
        },
    }
)
async def get_weather_forecast(
    client: TuyaClient, city_id: str
) -> dict[str, Any]:
    return await client.weather.get_forecast(city_id)


@_register(
    {
        "name": "get_weather_by_location",
        "description": (
            "Get current weather at a geographic coordinate "
            "(longitude/latitude)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "lon": {
                    "type": "number",
                    "description": "Longitude.",
                },
                "lat": {
                    "type": "number",
                    "description": "Latitude.",
                },
            },
            "required": ["lon", "lat"],
        },
    }
)
async def get_weather_by_location(
    client: TuyaClient, lon: float, lat: float
) -> dict[str, Any]:
    return await client.weather.get_current_by_location(lon=lon, lat=lat)


# ---------------------------------------------------------------------------
# Lock tools
# ---------------------------------------------------------------------------


@_register(
    {
        "name": "unlock_door",
        "description": (
            "Trigger a password-free unlock on a smart lock. "
            "The lock must support password-free open-door."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "The smart lock device ID.",
                },
            },
            "required": ["device_id"],
        },
    }
)
async def unlock_door(
    client: TuyaClient, device_id: str
) -> bool:
    return await client.locks.password_free_unlock(device_id)


@_register(
    {
        "name": "remote_unlock_door",
        "description": (
            "Remote unlock via the smart-lock API. Uses a different "
            "endpoint from unlock_door for locks that support it."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "device_id": {
                    "type": "string",
                    "description": "The smart lock device ID.",
                },
            },
            "required": ["device_id"],
        },
    }
)
async def remote_unlock_door(
    client: TuyaClient, device_id: str
) -> bool:
    return await client.locks.remote_unlock(device_id)


# ---------------------------------------------------------------------------
# IR control tools
# ---------------------------------------------------------------------------


@_register(
    {
        "name": "list_ir_remotes",
        "description": (
            "List virtual remotes configured on an infrared control hub."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "infrared_id": {
                    "type": "string",
                    "description": "The IR hub device ID.",
                },
            },
            "required": ["infrared_id"],
        },
    }
)
async def list_ir_remotes(
    client: TuyaClient, infrared_id: str
) -> list[dict[str, Any]]:
    return await client.ir.list_remotes(infrared_id)


@_register(
    {
        "name": "get_ir_remote_keys",
        "description": (
            "Get available keys (buttons) for a virtual IR remote."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "infrared_id": {
                    "type": "string",
                    "description": "The IR hub device ID.",
                },
                "remote_id": {
                    "type": "string",
                    "description": "The virtual remote ID.",
                },
            },
            "required": ["infrared_id", "remote_id"],
        },
    }
)
async def get_ir_remote_keys(
    client: TuyaClient, infrared_id: str, remote_id: str
) -> dict[str, Any]:
    return await client.ir.get_remote_keys(infrared_id, remote_id)


@_register(
    {
        "name": "send_ir_command",
        "description": (
            "Send an IR key-press command through a virtual remote "
            "on an IR hub."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "infrared_id": {
                    "type": "string",
                    "description": "The IR hub device ID.",
                },
                "remote_id": {
                    "type": "string",
                    "description": "The virtual remote ID.",
                },
                "key": {
                    "type": "string",
                    "description": "The key/button name to press.",
                },
            },
            "required": ["infrared_id", "remote_id", "key"],
        },
    }
)
async def send_ir_command(
    client: TuyaClient,
    infrared_id: str,
    remote_id: str,
    key: str,
) -> bool:
    return await client.ir.send_command(
        infrared_id, remote_id, key=key,
    )


# ---------------------------------------------------------------------------
# Location tools
# ---------------------------------------------------------------------------


@_register(
    {
        "name": "get_device_location",
        "description": (
            "Get the real-time GPS location of a device "
            "that supports location tracking."
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
async def get_device_location(
    client: TuyaClient, device_id: str
) -> dict[str, Any]:
    return await client.location.get_realtime_location(device_id)


# ---------------------------------------------------------------------------
# Firmware tools
# ---------------------------------------------------------------------------


@_register(
    {
        "name": "get_firmware_info",
        "description": (
            "Get firmware version info and available upgrades "
            "for a device."
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
async def get_firmware_info(
    client: TuyaClient, device_id: str
) -> list[dict[str, Any]]:
    return await client.firmware.get_info(device_id)


# ---------------------------------------------------------------------------
# Group tools
# ---------------------------------------------------------------------------


@_register(
    {
        "name": "list_device_groups",
        "description": (
            "List device groups with pagination. "
            "Returns group IDs, names, and device counts."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "page_no": {
                    "type": "integer",
                    "description": "Page number (default 1).",
                },
                "page_size": {
                    "type": "integer",
                    "description": "Results per page (default 20).",
                },
            },
        },
    }
)
async def list_device_groups(
    client: TuyaClient,
    page_no: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    return await client.groups.list_groups(
        page_no=page_no, page_size=page_size,
    )


@_register(
    {
        "name": "get_device_group",
        "description": (
            "Get details of a device group including its "
            "member devices."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "group_id": {
                    "type": "string",
                    "description": "The device group ID.",
                },
            },
            "required": ["group_id"],
        },
    }
)
async def get_device_group(
    client: TuyaClient, group_id: str
) -> dict[str, Any]:
    return await client.groups.get(group_id)


# ---------------------------------------------------------------------------
# Scene template tools
# ---------------------------------------------------------------------------


@_register(
    {
        "name": "list_scene_templates",
        "description": (
            "List available pre-built scene templates with pagination."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "page_no": {
                    "type": "integer",
                    "description": "Page number (default 1).",
                },
                "page_size": {
                    "type": "integer",
                    "description": "Results per page (default 20).",
                },
            },
        },
    }
)
async def list_scene_templates(
    client: TuyaClient,
    page_no: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    return await client.templates.list_templates(
        page_no=page_no, page_size=page_size,
    )


# ---------------------------------------------------------------------------
# Extended space tools
# ---------------------------------------------------------------------------


@_register(
    {
        "name": "list_spaces",
        "description": (
            "List all Tuya spaces (locations/rooms) with pagination."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "page_no": {
                    "type": "integer",
                    "description": "Page number (default 1).",
                },
                "page_size": {
                    "type": "integer",
                    "description": "Results per page (default 20).",
                },
            },
        },
    }
)
async def list_spaces(
    client: TuyaClient,
    page_no: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    return await client.spaces.list_spaces(
        page_no=page_no, page_size=page_size,
    )


# ---------------------------------------------------------------------------
# Notification tools
# ---------------------------------------------------------------------------


@_register(
    {
        "name": "send_notification",
        "description": (
            "Send a push notification to Tuya app users. "
            "Specify title, content, and target user IDs."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Notification title.",
                },
                "content": {
                    "type": "string",
                    "description": "Notification body text.",
                },
                "target_user_ids": {
                    "type": "array",
                    "description": "List of Tuya user IDs to notify.",
                    "items": {"type": "string"},
                },
            },
            "required": ["title", "content", "target_user_ids"],
        },
    }
)
async def send_notification(
    client: TuyaClient,
    title: str,
    content: str,
    target_user_ids: list[str],
) -> Any:
    return await client.notifications.push(
        title=title, content=content, target_user_ids=target_user_ids,
    )


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
