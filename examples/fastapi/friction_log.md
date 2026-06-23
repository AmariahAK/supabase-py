# supabase-py Friction Log

Issues discovered while building the FastAPI Realtime Rule Engine example.
Append entries as they are found during implementation.

---

## Per-request JWT injection is not ergonomic

**Severity:** medium
**Where:** `dependencies.py` / `AsyncClientOptions`
**What happened:** Passing `headers={...}` to `AsyncClientOptions(headers={...})`
replaces the entire default dict, silently dropping `X-Client-Info` and any
other default headers. The correct pattern is to construct `AsyncClientOptions()`
and then mutate `.headers["Authorization"]` — but this is not documented and not
obvious from the constructor signature.
**Recommendation:** Add a `with_auth(token: str) -> AsyncClientOptions` factory
method that returns a copy of the default options with only the Authorization
header overridden, making the per-request pattern a one-liner.

---

## Manual connect() required before subscribe()

**Severity:** medium
**Where:** `engine.py:start_engine` / `AsyncRealtimeClient`
**What happened:** Calling `channel.subscribe()` without first calling
`service_client.realtime.connect()` results in the subscription silently
failing or raising. There is no auto-connect behavior.
**Recommendation:** Either auto-connect when the first `channel.subscribe()`
is called (matching the JS SDK behavior), or raise an explicit error with a
clear message if `subscribe()` is called before `connect()`.

---

## Realtime callback async support is undocumented

**Severity:** high
**Where:** `engine.py` / `channel.on_postgres_changes(callback=...)`
**What happened:** It is unclear from the SDK docs or type annotations whether
`on_postgres_changes` accepts an async callable. The sync wrapper with
`asyncio.create_task()` is a workaround discovered by trial and error.
**Recommendation:** Add explicit support for async callbacks in
`on_postgres_changes` (detect with `asyncio.iscoroutinefunction`) and document
this in the method docstring and README.

---

## Broadcast requires a prior subscribe() on the channel

**Severity:** high
**Where:** `engine.py:on_task_change` / `channel.send()`
**What happened:** Calling `channel.send()` on a freshly created channel without
first calling `channel.subscribe()` either raises or silently no-ops. Creating
and subscribing a new channel per broadcast event is expensive and semantically
odd (subscribing implies receiving, but we only want to send).
**Recommendation:** Add a `channel.broadcast(event, payload)` method that
connects and sends without requiring a full subscription lifecycle, matching the
common server-side fire-and-forget pattern.
