# CLAUDE.md

## Validation Commands

- You MUST run `python -m pytest tests/ -v` to execute the full test suite before committing
- You MUST run `ruff check src/ tests/` to verify linting passes; instead of committing with errors, fix them first
- You SHOULD run `ruff check --fix src/ tests/` to auto-fix simple lint violations before manual review

## Architecture

- `src/tuya_agent/` contains all library source code as a single flat Python package
- `src/tuya_agent/client.py` is the core async HTTP client; all domain modules depend on it
- `src/tuya_agent/auth.py` handles HMAC-SHA256 request signing and token lifecycle
- `src/tuya_agent/devices.py`, `src/tuya_agent/logs.py`, `src/tuya_agent/scenes.py`, `src/tuya_agent/events.py` are domain mixins attached to the client
- `src/tuya_agent/tools.py` provides the agent-facing tool registry and `dispatch()` entry point
- `src/tuya_agent/storage.py` is the SQLite storage layer for persisting device logs with deduplication
- `src/tuya_agent/collector.py` orchestrates periodic API-based log collection across all devices
- `src/tuya_agent/watcher.py` streams real-time Pulsar WebSocket events into SQLite storage
- `src/tuya_agent/__main__.py` is the CLI entry point with `collect`, `watch`, and `status` subcommands
- You SHOULD follow the existing pattern where each test file mirrors a source module (e.g. `tests/test_auth.py` tests `src/tuya_agent/auth.py`)

## Code Standards

- You MUST target Python 3.10+ and use `from __future__ import annotations` in every module
- You MUST use `httpx.AsyncClient` for all HTTP calls; NEVER use `requests` or synchronous I/O
- You MUST use `pydantic` models or `dataclass` for structured data; AVOID raw dicts for internal state
- You SHOULD keep line length at or below 100 characters as configured in `pyproject.toml`
- You MUST NOT add external dependencies without updating `pyproject.toml`; prefer minimal deps

## Error Handling

- You MUST raise `TuyaAPIError` for all non-success API responses; instead of swallowing errors, let them propagate
- You SHOULD use structured logging via `logging.getLogger(__name__)`; instead of bare `print()`, prefer the logger
- You MUST wrap WebSocket reconnection logic in try/except for `websockets.ConnectionClosed`

## Security

- You MUST NEVER commit `.env` files, API keys, or the Tuya Access Secret; instead, use environment variables loaded at runtime
- Credentials MUST be loaded from environment variables via `TuyaConfig` (pydantic-settings)
- The `.gitignore` MUST include `.env` to prevent accidental credential exposure
- You MUST NOT log or print the `access_secret` or raw `access_token` values in any output
- You SHOULD use the `.env.example` template as reference; it contains only sample values for documentation

## Testing

- You MUST add or update tests in `tests/` for any new or changed functionality
- You MUST use `pytest-httpx` to mock HTTP interactions; instead of real API calls, use `httpx_mock` fixtures
- You SHOULD maintain test coverage for auth signing, client token flow, and tool registry integrity
- You MUST mark async test functions with the `pytest.mark.asyncio` decorator
