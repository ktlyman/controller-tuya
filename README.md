# tuya-agent-tools

A Python library that provides agent-friendly tools for interacting with the [Tuya IoT](https://developer.tuya.com/) ecosystem. It wraps the Tuya Cloud API into a structured set of async operations — device access and control, real-time event streaming, historic log queries, and scene/automation management — exposed through a JSON-schema tool registry that any agent framework can consume.

## Requirements

- Python >= 3.10
- A Tuya Cloud Development project with an **Access ID** and **Access Secret** (obtain from [iot.tuya.com](https://iot.tuya.com/))

## Installation

```bash
pip install -e .

# With development tools (pytest, ruff, etc.)
pip install -e ".[dev]"
```

## Configuration

The library reads credentials from environment variables:

| Variable | Description | Default |
|---|---|---|
| `TUYA_ACCESS_ID` | Your Tuya Cloud Access ID | *(required)* |
| `TUYA_ACCESS_SECRET` | Your Tuya Cloud Access Secret | *(required)* |
| `TUYA_API_REGION` | Data center region (`us`, `eu`, `cn`, `in`, `us-e`) | `us` |

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

You can also pass a `TuyaConfig` object directly:

```python
from tuya_agent import TuyaConfig, TuyaClient

config = TuyaConfig(access_id="your_id", access_secret="your_secret", api_region="eu")
async with TuyaClient(config) as client:
    ...
```

## Quick Start

### Using the client directly

```python
import asyncio
from tuya_agent import TuyaClient

async def main():
    async with TuyaClient() as client:
        # List all devices
        result = await client.devices.list()
        for device in result["list"]:
            print(f"{device['name']} ({device['id']}) - online: {device['online']}")

        # Get a device's current status
        status = await client.devices.get_status("your_device_id")
        print(status)

        # Control a device
        await client.devices.send_commands("your_device_id", [
            {"code": "switch_led", "value": True},
            {"code": "bright_value", "value": 200},
        ])

asyncio.run(main())
```

### Using the agent tool dispatcher

For agent frameworks, the `tools` module provides machine-readable tool definitions and a unified dispatcher:

```python
from tuya_agent import TuyaClient
from tuya_agent.tools import TOOLS, dispatch

async with TuyaClient() as client:
    # Discover available tools (JSON-schema format)
    for tool in TOOLS:
        print(f"{tool['name']}: {tool['description']}")

    # Dispatch a tool call by name
    result = await dispatch(client, "get_device_status", {"device_id": "abc123"})
```

## Available Agent Tools

### Device Operations

| Tool | Description |
|---|---|
| `list_devices` | List all devices with IDs, names, categories, and online status |
| `get_device` | Get detailed information about a specific device |
| `get_device_status` | Get current data-point values (code/value pairs) |
| `get_device_specification` | Get the device's supported instructions and status data points |
| `get_device_functions` | Get writable functions a device supports (codes and value ranges) |
| `get_sub_devices` | List sub-devices connected to a gateway (Zigbee/BLE mesh) |
| `control_device` | Send control commands (code + value) to a device |

### Event & Log Queries

| Tool | Description |
|---|---|
| `get_device_event_logs` | Query device event history (online, offline, reset, etc.) |
| `get_device_report_logs` | Query historical data-point status reports |
| `get_device_statistics` | Get aggregated statistics (15-min, daily, weekly, monthly) |
| `collect_realtime_events` | Stream real-time events via Tuya Pulsar for a specified duration |

### Scene & Automation Management

| Tool | Description |
|---|---|
| `list_scenes` | List scenes and automations in a space (v2.0 Cloud API) |
| `trigger_scene` | Trigger (execute) a scene or automation rule by ID |

### Log Collection & Storage

| Tool | Description |
|---|---|
| `collect_logs` | Trigger a one-shot collection of device event logs into SQLite |
| `get_collection_status` | Get statistics about the local log database and per-device bookmarks |
| `query_logs` | Search the local log database with device, time, and code filters |
| `get_collection_runs` | Get recent collection run history with timestamps and status |
| `watch_realtime_events` | Subscribe to real-time Pulsar events and store them in SQLite |

### Space & Location

| Tool | Description |
|---|---|
| `resolve_space` | Resolve a space ID to its name and details |
| `list_spaces` | List all Tuya spaces (locations/rooms) with pagination |

### Device Timers

| Tool | Description |
|---|---|
| `list_device_timers` | List all scheduled timer tasks for a device |
| `add_device_timer` | Create a scheduled timer with day-of-week repetition |
| `toggle_device_timer` | Enable or disable a specific timer task |

### Weather

| Tool | Description |
|---|---|
| `get_weather_forecast` | Get weather forecast for a Tuya city ID |
| `get_weather_by_location` | Get current weather at a geographic coordinate |

### Smart Locks

| Tool | Description |
|---|---|
| `unlock_door` | Trigger a password-free unlock on a smart lock |
| `remote_unlock_door` | Remote unlock via the smart-lock API |

### IR Control

| Tool | Description |
|---|---|
| `list_ir_remotes` | List virtual remotes on an infrared control hub |
| `get_ir_remote_keys` | Get available keys (buttons) for a virtual IR remote |
| `send_ir_command` | Send an IR key-press command through a virtual remote |

### Device Location

| Tool | Description |
|---|---|
| `get_device_location` | Get real-time GPS location of a tracking device |

### Firmware

| Tool | Description |
|---|---|
| `get_firmware_info` | Get firmware version info and available upgrades |

### Device Groups

| Tool | Description |
|---|---|
| `list_device_groups` | List device groups with pagination |
| `get_device_group` | Get details of a device group |

### Scene Templates

| Tool | Description |
|---|---|
| `list_scene_templates` | List available pre-built scene templates |

### Notifications

| Tool | Description |
|---|---|
| `send_notification` | Send push notifications to Tuya app users |

## Module Overview

```
src/tuya_agent/
├── __init__.py     # Public API: TuyaClient, TuyaConfig
├── __main__.py     # CLI entry point: collect, watch, serve, status subcommands
├── config.py       # Region-based URL resolution, env var loading via pydantic-settings
├── auth.py         # HMAC-SHA256 request signing, token lifecycle management
├── client.py       # Core async HTTP client with automatic token refresh
├── collector.py    # Periodic API-based log collection across all devices
├── devices.py      # Device list, details, status, control, sub-devices
├── events.py       # Real-time Pulsar WebSocket event subscription
├── firmware.py     # Firmware version info and OTA upgrade triggering
├── groups.py       # Device group CRUD and membership management
├── ir.py           # Infrared control hub: categories, remotes, keys, commands
├── location.py     # Device GPS location, track history, geofences
├── locks.py        # Smart lock operations: password tickets, remote unlock
├── logs.py         # Historic event logs, DP report logs, aggregated statistics
├── notifications.py # Push notifications to Tuya app users
├── scenes.py       # Scene listing and triggering (v2.0 Cloud API) plus automation management
├── spaces.py       # Space resolution, listing, creation, children, and resources
├── server.py       # FastAPI web server with REST endpoints and SSE for the dashboard
├── storage.py      # SQLite storage layer for persisting device logs with deduplication
├── templates.py    # Scene template browsing and application
├── timers.py       # Device timer/scheduled task CRUD (add, modify, toggle, delete)
├── tools.py        # Agent tool registry (JSON-schema descriptors) and dispatcher
├── watcher.py      # Streams real-time Pulsar WebSocket events into SQLite storage
├── weather.py      # Weather forecast by city, coordinates, or IP
└── static/
    └── index.html  # Self-contained HTML/CSS/JS dashboard
```

## Authentication

The library implements Tuya's HMAC-SHA256 signing protocol automatically. When you create a `TuyaClient`, it:

1. Fetches an access token using your credentials (valid for 2 hours)
2. Signs every subsequent request with the token
3. Proactively refreshes the token before expiry

You never need to manage tokens manually.

## Real-Time Events

The `events` module connects to Tuya's Pulsar message service over WebSocket to receive real-time device events:

```python
async with TuyaClient() as client:
    # Collect events for 30 seconds
    events = await client.events.collect(duration_seconds=30, max_events=10)
    for event in events:
        print(f"{event.event_type}: {event.device_id} -> {event.data}")

    # Or iterate as an async stream
    async for event in client.events.subscribe(max_events=50):
        print(event)
```

Event types include `dp_report` (status changes), `online`, `offline`, `bind`, `unbind`, and `reset`.

## Supported Regions

| Region | Code | API Base |
|---|---|---|
| Western America | `us` | `openapi.tuyaus.com` |
| Eastern America | `us-e` | `openapi-us-e.tuyaus.com` |
| Central Europe | `eu` | `openapi.tuyaeu.com` |
| China | `cn` | `openapi.tuyacn.com` |
| India | `in` | `openapi.tuyain.com` |

## CLI Commands

The package includes a CLI for running background services:

```bash
# Collect device event logs into SQLite (one-shot or periodic)
python -m tuya_agent collect [--db tuya_logs.db] [--interval 300]

# Stream real-time Pulsar events into SQLite
python -m tuya_agent watch [--db tuya_logs.db]

# Start the web dashboard
python -m tuya_agent serve [--host 127.0.0.1] [--port 8000] [--db tuya_logs.db]

# Show collection status
python -m tuya_agent status [--db tuya_logs.db]
```

## Web Dashboard

The `serve` command launches a FastAPI server with a self-contained dashboard at `http://localhost:8000`. The dashboard provides:

- **Devices** — live status, grouped by location, with quick controls (locks, switches, dimmers)
- **Scenes** — tap-to-run scenes and automations, organized by space
- **Logs** — searchable event history with device and date filters

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Lint
ruff check src/ tests/

# Auto-fix lint issues
ruff check --fix src/ tests/
```

## License

MIT
