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
| `list_scenes` | List all tap-to-run scenes in a home |
| `trigger_scene` | Execute a tap-to-run scene |
| `get_automation` | Get details for an automation rule |
| `enable_automation` | Enable a disabled automation |
| `disable_automation` | Disable an active automation |

## Module Overview

```
src/tuya_agent/
├── __init__.py     # Public API: TuyaClient, TuyaConfig
├── config.py       # Region-based URL resolution, env var loading via pydantic-settings
├── auth.py         # HMAC-SHA256 request signing, token lifecycle management
├── client.py       # Core async HTTP client with automatic token refresh
├── devices.py      # Device list, details, status, control, sub-devices
├── events.py       # Real-time Pulsar WebSocket event subscription
├── logs.py         # Historic event logs, DP report logs, aggregated statistics
├── scenes.py       # Scene CRUD and automation enable/disable
└── tools.py        # Agent tool registry (JSON-schema descriptors) and dispatcher
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
