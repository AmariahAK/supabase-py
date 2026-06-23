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
