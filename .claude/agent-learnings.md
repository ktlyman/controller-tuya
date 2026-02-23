# Agent Learnings: Tuya IoT Controller

Hard-won lessons from building an async Python ↔ Tuya Cloud ↔ web dashboard pipeline,
collected across 15 iterative commits over multiple agent sessions.

---

## 1. Tuya API Gotchas

### Field names are camelCase, not snake_case
The Tuya Cloud API returns `isOnline`, `customName`, `bindSpaceId`, `activeTime` — not
their snake_case equivalents. If your frontend or backend expects `is_online`, nothing
will match. **Always log a raw response first** and build your field access from that,
or support both forms:

```javascript
const sid = device.bindSpaceId || device.bind_space_id;
```

### v1.x APIs may require unsubscribed permissions
The v1.1 `/homes/{home_id}/scenes` endpoint returned error `28841101: "No permissions.
This API is not subscribed."` Our project credentials didn't include the Homes API
subscription. The fix was switching to the v2.0 Cloud API (`/v2.0/cloud/scene/rule`)
which uses `space_id` instead of `home_id` and works under the standard IoT Core
subscription.

**Pattern**: when a v1.x endpoint returns a permission error, search for a v2.0
equivalent — it often exists and uses a different (often more accessible) auth scope.

### `space_id` ≠ `home_id`
These are distinct concepts in Tuya's data model. Devices have a `bindSpaceId` field
that maps to spaces (locations), not homes. The v2.0 Cloud APIs use `space_id`; the
legacy v1.x APIs use `home_id`. Don't substitute one for the other.

### Raw-type data points are Base64-encoded blobs
The `ble_unlock_check` command on smart locks is a Raw-type DP. Its value looks like
`"AAH//zk2MjY4ODU5AWlYc18AAA=="` — not a boolean. Sending `true` does nothing.
You must read the current value from device status and send it back. This applies to
all Raw-type DPs across the Tuya ecosystem.

### Rate limiting uses code `40000309`
When you hit the API too fast (common during bulk log collection), Tuya returns this
code. Handle it with exponential backoff, not immediate failure:

```python
if exc.code == 40000309:
    await asyncio.sleep(10 * (2 ** attempt))
```

### Device categories are terse codes
`jtmspro` = lock, `cz` = plug, `kg` = switch, `dj` = dimmer, `tdq` = remote,
`wg2` = gateway. There's no friendly name field — you need a lookup table for icons
or labels.

---

## 2. Architecture Patterns That Paid Off

### Mixin composition over monolith
Each API domain (devices, scenes, logs, events) is a separate mixin class that holds
a reference to the shared HTTP client. This kept files small, testable in isolation,
and allowed adding v2.0 methods to `ScenesMixin` without touching any other module.

### Single-file dashboard
Keeping the entire frontend in one `index.html` with inline CSS and vanilla JS
eliminated all build tooling. It loads instantly, deploys as a static asset, and is
trivially served by FastAPI's `StaticFiles`. The tradeoff is a large file (~1800 lines)
but it's still navigable with clear section comments and a module-like JS structure.

### `_test_state` injection on `create_app()`
The FastAPI factory accepts a `_test_state` dict that bypasses the lifespan manager.
Tests pass pre-built mocks directly. This is cleaner than monkeypatching and makes
test setup explicit:

```python
state = {"client": mock_client, "storage": mock_storage}
app = create_app(_test_state=state)
```

### SQLite deduplication via UNIQUE + INSERT OR IGNORE
Both the log collector and event watcher write to the same SQLite tables. Deduplication
is handled entirely by the database — a UNIQUE constraint on
`(device_id, event_id, event_time)` with `INSERT OR IGNORE`. No application-level
duplicate tracking needed. The watcher generates deterministic event IDs via SHA-256
hash of (device_id, timestamp, event_type, data).

### Cursor-based pagination everywhere
Tuya's APIs use `last_row_key` cursors, not page numbers. The collector loops until
no next cursor is returned. This pattern was replicated for our own SQLite queries to
avoid OFFSET-based pagination performance issues.

---

## 3. Frontend Lessons (Vanilla JS)

### localStorage for UI state persistence
Card ordering (drag-and-drop) and expand/collapse state survive page reloads via
localStorage. Keys are namespaced per space to avoid collisions:

```javascript
const order = JSON.parse(localStorage.getItem('tuya_card_order') || '{}');
```

### Edit mode gates destructive UI interactions
Drag-and-drop reordering is hidden behind an explicit edit mode toggle. Without this,
users accidentally drag cards while scrolling on mobile or when they just want to click.

### Promise.all for parallel space queries
The scenes page discovers all unique `bindSpaceId` values from the device list, then
fetches scenes from all spaces in parallel:

```javascript
const results = await Promise.all(
  [...spaceIds].map(sid => api.get(`/api/spaces/${sid}/scenes`))
);
state.scenes = results.flat();
```

### Inline SVG favicons avoid extra files
A `data:image/svg+xml` URI in a `<link rel="icon">` tag eliminates the need for a
separate `.ico` or `.png` file and the server route to serve it.

---

## 4. Debugging & Iteration Patterns

### Always hit the live API first
When something doesn't work, `curl` the actual endpoint (or use a quick Python script)
to see the raw response. The scenes fix started with observing error 28841101 in the
browser network tab, then hitting the v2.0 endpoint directly to confirm it returned
data. Don't guess at response shapes — inspect them.

### Stale servers on fixed ports
When restarting the FastAPI server during development, the old process often lingers.
Always kill the port before starting:

```bash
lsof -ti :8000 | xargs kill 2>/dev/null
```

### Incremental delivery over big-bang
Each commit in this project added one coherent capability. The unlock button went
through three iterations:
1. `reverse_lock` → didn't work (wrong command)
2. `ble_unlock_check` with value `true` → didn't work (wrong value type)
3. `ble_unlock_check` with actual cached Base64 value → worked

Each attempt was a separate commit that could be reverted. Small commits with live
testing between them caught integration errors early.

### Mock at the right layer
Server tests mock the `TuyaClient` service methods (e.g., `client.scenes.list_rules`),
not the HTTP transport. This validates endpoint wiring and response shaping without
coupling tests to Tuya API URL patterns. Transport-level tests (`pytest-httpx`) live
in the client/auth test files where URL construction is the thing under test.

---

## 5. Tool & Workflow Recommendations

### For Tuya Cloud API integration
- **Start with v2.0 Cloud APIs** (`/v2.0/cloud/...`) — they're newer, better documented,
  and generally don't require extra API subscriptions.
- **Always check the `success` field** in responses. Tuya wraps everything; the HTTP
  status is always 200 even on failure.
- **Cache device status** client-side. Status polling is expensive and rate-limited.
  Use SSE/WebSocket for real-time updates.

### For async Python projects
- **`httpx.AsyncClient`** over `aiohttp` or `requests` — cleaner API, better typing,
  and `pytest-httpx` makes mocking trivial.
- **Pydantic-settings for config** — environment variable loading with validation and
  defaults in one class. No manual `os.getenv()` chains.
- **`asyncio.Queue` for fan-out** — one producer, N consumers. The EventBroadcaster
  uses this to deliver SSE events to all connected dashboard clients.

### For single-file web dashboards
- **Vanilla JS scales further than you think** — this dashboard has device control,
  drag-and-drop, SSE streaming, and multi-page routing in ~1800 lines with no framework.
- **Use CSS custom properties** for theming from the start. When dark mode is the
  default, you'll thank yourself.
- **`innerHTML` with template literals** is fine for dashboards — it's simple, fast
  for development, and easy for agents to modify. Reserve reactive frameworks for
  apps with complex state dependencies.

### For CI/quality
- **`claude-md-lint`** catches documentation staleness early. The `--fail-under` flag
  prevents CLAUDE.md from degrading over time. Set the threshold high (95+) and fix
  issues immediately rather than letting them accumulate.
- **`ruff`** replaces flake8 + isort + pyupgrade in one fast tool. The
  `ruff check --fix` auto-fix pass catches most issues before manual review.

---

## 6. Common Failure Modes & Recovery

| Symptom | Root Cause | Fix |
|---|---|---|
| API returns `28841101` | Missing API subscription | Switch to v2.0 Cloud API equivalent |
| Device fields are `undefined` | camelCase vs snake_case mismatch | Check raw response, use actual field names |
| Unlock button does nothing | Sending wrong value type for Raw DP | Read cached value and re-send it |
| Scenes page is empty | Using `home_id` where `space_id` is needed | Use `bindSpaceId` from device list |
| Log collection stops mid-run | Rate limit code `40000309` | Add exponential backoff retry loop |
| Server won't start | Port already in use from previous run | `lsof -ti :PORT \| xargs kill` |
| SSE events not arriving | EventBroadcaster queue overflow | Increase queue size or drop slow consumers |
| Drag-and-drop fires on scroll | No edit mode gate | Add explicit edit mode toggle |
| Tests fail after endpoint change | Mocks use old paths/methods | Update mock method names and assertions |
