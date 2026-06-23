# FastAPI Realtime Rule Engine — Design Spec

**Date:** 2026-06-23
**Location:** `examples/fastapi/`
**Purpose:** Stress-test `supabase-py` SDK — specifically the async Realtime path, per-request JWT injection, Postgres Changes subscriptions, and server-side broadcast from Python.

---

## What We're Building

A FastAPI application where users define **watch rules**: "when `tasks.status` changes to `done`, broadcast to channel `#team-alerts`." A Python background task is the Realtime engine — it holds a persistent `AsyncRealtimeClient` connection, subscribes to Postgres Changes on the `tasks` table, evaluates matching rules, and broadcasts enriched events to configured channels. The browser signs in via Supabase Auth, manages rules via the FastAPI API, and subscribes to broadcast channels using the JS client to display a live event feed.

This example is intentionally designed to surface SDK friction. Every pain point found during implementation is logged in `friction_log.md` at the root of the example directory.

---

## Data Model

### `tasks`
The event source — changes to this table trigger Postgres Changes callbacks in Python.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `title` | `text` | |
| `status` | `text` | `pending \| in_progress \| done` |
| `assigned_to` | `uuid` | references `auth.users` |
| `created_by` | `uuid` | references `auth.users` |
| `created_at` | `timestamptz` | |

**RLS:** Authenticated users can read all tasks; can only update tasks assigned to them.

### `rules`
User-defined watch conditions. The background engine reads all rules using the service role client.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `user_id` | `uuid` | references `auth.users` — RLS owner |
| `watch_column` | `text` | e.g. `"status"` |
| `watch_value` | `text` | e.g. `"done"` |
| `broadcast_channel` | `text` | e.g. `"team-alerts"` |
| `label` | `text` | human-readable name |
| `created_at` | `timestamptz` | |

**RLS:** Users can only read and write their own rules. Service role bypasses RLS for background rule evaluation.

### `rule_events`
Append-only log written exclusively by the background engine.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` PK | |
| `rule_id` | `uuid` | references `rules` |
| `task_id` | `uuid` | the task that triggered the rule |
| `triggered_at` | `timestamptz` | |
| `payload` | `jsonb` | snapshot of the task row at trigger time |

**RLS:** Written by service role only. Users can read events for rules they own (join through `rules.user_id`).

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│ FastAPI process                                      │
│                                                      │
│  ┌──────────────┐   ┌──────────────┐                │
│  │ HTTP routers │   │  engine.py   │                │
│  │ /auth        │   │ (asyncio     │                │
│  │ /tasks       │   │  background  │                │
│  │ /rules       │   │  coroutine)  │                │
│  └──────┬───────┘   └──────┬───────┘                │
│         │                  │                        │
│  per-request           service role                 │
│  AsyncClient           AsyncClient (singleton)      │
│  (JWT from header)                                  │
└─────────┬────────────────┬─────────────────────────┘
          │                │
          ▼                ▼
     Supabase          Supabase
     (PostgREST        (Realtime WS
      + Auth)           + PostgREST)
          ▲
          │
┌─────────┴──────────────────────────────────────────┐
│ Browser                                             │
│  - Jinja2 HTML shell                                │
│  - @supabase/supabase-js (CDN)                      │
│  - JS subscribes to broadcast channels              │
│  - JS tracks presence                               │
└─────────────────────────────────────────────────────┘
```

---

## Components

### `main.py`
Entry point. Mounts all routers. Uses FastAPI `lifespan` to:
1. Create the service role `AsyncClient` singleton and store it on `app.state`
2. Start the `engine.py` background coroutine as an `asyncio.Task`
3. On shutdown, cancel the engine task and close the Realtime connection

### `routers/auth.py`
- `POST /auth/signup` — `client.auth.sign_up()`
- `POST /auth/signin` — `client.auth.sign_in_with_password()`
- `POST /auth/signout` — `client.auth.sign_out()`

Returns the Supabase session (access token + refresh token) to the browser. The browser stores the access token in `localStorage` and sends it as `Authorization: Bearer <token>` on all subsequent API calls.

### `routers/tasks.py`
- `GET /tasks` — list tasks (RLS-filtered)
- `POST /tasks` — create a task
- `PATCH /tasks/{id}` — update task status

Every handler calls `get_client(request)` — a dependency that extracts the JWT from `Authorization` header and constructs a **fresh per-request `AsyncClient`**:
```python
async def get_client(request: Request) -> AsyncClient:
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    options = AsyncClientOptions(
        headers={"Authorization": f"Bearer {token}"}
    )
    return await acreate_client(SUPABASE_URL, SUPABASE_ANON_KEY, options=options)
```
This is the core JWT propagation stress point. RLS fires on the Postgres side based on the token's `sub` claim.

### `routers/rules.py`
- `GET /rules` — list the user's rules (RLS-filtered)
- `POST /rules` — create a rule
- `DELETE /rules/{id}` — delete a rule

Same `get_client` dependency pattern as `tasks.py`.

### `engine.py`
The Realtime engine. A single `asyncio` coroutine launched at startup.

**Startup:**
```python
async def start_engine(service_client: AsyncClient):
    channel = service_client.channel("tasks-watcher")
    channel.on_postgres_changes(
        event="UPDATE",
        schema="public",
        table="tasks",
        callback=on_task_change,
    )
    await service_client.realtime.connect()
    await channel.subscribe()
    # The AsyncRealtimeClient handles WS keepalive internally.
    # We keep this coroutine alive so the lifespan task doesn't exit.
    await asyncio.Event().wait()
```

**On change event:**
```python
async def on_task_change(payload):
    new_record = payload["new"]
    # Load all rules from DB (service role bypasses RLS — intentional).
    # In production you'd cache this; here we re-fetch to stress the
    # PostgREST-inside-Realtime-callback path.
    rules = await service_client.table("rules").select("*").execute()
    for rule in rules.data:
        if rule["watch_column"] == "status" and rule["watch_value"] == new_record.get("status"):
            # Log the event
            await service_client.table("rule_events").insert({
                "rule_id": rule["id"],
                "task_id": new_record["id"],
                "payload": new_record,
            }).execute()
            # Broadcast to the configured channel.
            # NOTE: channel.send() may require an active subscription on the
            # channel first — this is a known SDK friction point to stress and log.
            # We reuse the tasks-watcher channel if same, or create+subscribe a
            # dedicated broadcast channel. The exact behavior needs verification.
            broadcast_channel = service_client.channel(rule["broadcast_channel"])
            await broadcast_channel.subscribe()  # no-op if already subscribed
            await broadcast_channel.send(
                type="broadcast",
                event="rule_fired",
                payload={"rule": rule, "task": new_record},
            )
```

### `templates/`
Minimal Jinja2 HTML. Loads `@supabase/supabase-js` from CDN. A small vanilla JS block:
1. Signs the user in **directly via the JS client** (`supabase.auth.signInWithPassword()`) — the browser owns its own auth session; FastAPI API calls receive the resulting JWT as `Authorization: Bearer`. The FastAPI `/auth/signin` route is not used for browser sign-in; it exists only for programmatic/CLI clients.
2. Subscribes to the user's configured broadcast channels
3. Appends incoming `rule_fired` events to a live feed
4. Tracks presence (who else is watching) via `channel.track()` / `channel.presences`

### `friction_log.md`
Append-only log of every SDK issue found during implementation. Format per entry:
```
## [short title]
**Severity:** low | medium | high
**Where:** file:line or SDK method name
**What happened:** description of the friction
**Recommendation:** suggested SDK improvement
```

---

## Realtime Flow

```
Postgres UPDATE on tasks
  → AsyncRealtimeClient fires on_postgres_changes callback (Python)
    → engine queries all rules via service role client
      → for each matching rule:
          INSERT into rule_events          (service role AsyncClient)
          channel.send(broadcast, ...)     (service role AsyncClient)
            → Supabase Realtime routes broadcast to subscribed channels
              → Browser JS client receives "rule_fired" event
                → DOM updated with new event card
```

---

## SDK Call Map

| Call | Client type | SDK path stressed |
|---|---|---|
| `await acreate_client(url, service_key)` | Service role singleton | Client init, no JWT refresh |
| `await acreate_client(url, anon_key, options=AsyncClientOptions(headers={"Authorization": f"Bearer {jwt}"}))` | Per-request | JWT injection pattern, RLS enforcement |
| `channel.on_postgres_changes(event="UPDATE", schema="public", table="tasks", callback=...)` | Service role | Subscription registration, filter parsing |
| `await service_client.realtime.connect()` | Service role | WS handshake, auth via service key |
| `await channel.subscribe()` | Service role | Channel subscription lifecycle |
| `await channel.send(type="broadcast", event=..., payload=...)` | Service role | **Server-side broadcast from Python** |
| `await client.table("rules").select("*").execute()` | Service role | PostgREST from background task |
| `await client.table("tasks").select("*").execute()` | Per-request | RLS-filtered PostgREST query |
| `await client.auth.sign_in_with_password({"email": ..., "password": ...})` | Anon | Auth flow |
| `await client.auth.sign_up({"email": ..., "password": ...})` | Anon | Auth sign up |

---

## File Structure

```
examples/fastapi/
├── main.py                  # FastAPI app, lifespan, router mounts
├── engine.py                # Realtime background coroutine
├── dependencies.py          # get_client() FastAPI dependency
├── routers/
│   ├── auth.py
│   ├── tasks.py
│   └── rules.py
├── templates/
│   ├── base.html
│   ├── index.html           # task list + live event feed
│   ├── signin.html
│   └── rules.html           # rule management
├── supabase/
│   └── migrations/
│       └── 001_initial.sql  # tables + RLS policies
├── requirements.txt
├── .env.example
├── README.md
└── friction_log.md          # SDK issues found during build
```

---

## What This Stresses in supabase-py

1. **Async client lifecycle** — `acreate_client` called once (service role) vs. per-request. Are there hidden costs to constructing a new `AsyncClient` on every request?
2. **Manual `.connect()` requirement** — the SDK requires explicit `realtime.connect()` before `channel.subscribe()`. No auto-connect. This will be logged.
3. **Server-side broadcast API** — `channel.send()` from a background asyncio task. Does it work reliably without an active subscription on the same channel? Does it block?
4. **Postgres Changes callback threading** — callbacks fire inside the asyncio event loop. Is it safe to `await` PostgREST calls inside a Postgres Changes callback?
5. **Per-request `AsyncClient` with JWT** — no built-in helper for this pattern. Users must manually construct `ClientOptions` with headers. Friction expected.
6. **Long-lived connection management** — what happens when the WS connection drops? Does the SDK reconnect automatically? Does the subscription survive?
7. **Service role vs anon key distinction** — no type-level distinction in the SDK. Easy to accidentally use the wrong client.
