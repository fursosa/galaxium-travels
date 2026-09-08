# AGENTS.md — Agent (coding) mode

This file provides guidance to agents when working with code in this repository.

## Non-obvious coding rules

- **Adding a REST endpoint auto-registers an MCP tool** — `FastApiMCP` introspects all routes at mount time; no separate MCP registration needed. The route's docstring becomes the tool description — keep it precise.
- **Two session patterns; do not mix them.** REST handlers: `Depends(get_db)`. Everything else (seed.py, any code outside a request context): `db = SessionLocal(); try: ... finally: db.close()`.
- **Service functions must return `Model | ErrorResponse`** — never raise from a service function. The REST layer does `isinstance(result, ErrorResponse)` and maps `error_code` → HTTP status. Breaking this pattern silently drops error details from MCP callers.
- **When changing hold duration**, update BOTH `application.properties` (`hold.duration.minutes`) AND the timeout in `e2e/test_holds.py` — they must stay in sync.
- **`routers/booking_detail.py` is the only endpoint with auth** — it uses `X-User-Email` header + SHA-256 hashed logging. All other endpoints use `user_id` in body/path with name validation. Do not add auth headers to other endpoints without updating this pattern consistently.
- **mypy baseline is intentionally dirty** — 17 known pre-existing errors are suppressed in `.bob/hooks/mypy-baseline.txt`. Only NEW errors after a write are reported. Do not try to fix baseline errors unless specifically asked; regenerate the baseline with `.bob/hooks/gen-mypy-baseline.sh` only after intentional type surface changes.
- **Ruff ignores `B008`** — `Depends()` in function signatures is correct FastAPI DI, not a default-argument bug.
- **`pytest.ini` silences `PydanticDeprecatedSince211`** — triggered by `fastapi-mcp` schema generation, not app code. Do not suppress additional warnings without understanding the source.
- **Hold IDs are generated as `H-{year}-{count:06d}`** — sequential, not UUID. Do not change the format without updating e2e tests that match on `H-` prefix.
- **`confirmHold` is idempotent** — already-CONFIRMED holds return the existing record without error. Test for this explicitly when writing hold-related tests.
