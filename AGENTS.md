# AGENTS.md

This file provides guidance to agents when working with code in this repository.

A demo interplanetary flight-booking app. Its purpose is to **showcase challenges agents face in a multi-service codebase** — not to run in production.

- When asked to create a plan, gather data first, then explicitly switch to plan mode.
- Planning documents go at the root level in ALL CAPS.
- Before building anything, look for tests and the `verify` skill.
- For exploration tasks, use subagents.

## Commands

```bash
# Backend tests (fast, ~0.5s, 72 tests) — run from booking_system_backend/
cd booking_system_backend && .venv/bin/pytest                   # all
cd booking_system_backend && .venv/bin/pytest tests/test_services.py  # single file
cd booking_system_backend && .venv/bin/pytest -k "test_book_flight_success"  # single test

# Lint (Python)
cd booking_system_backend && .venv/bin/ruff check .

# Type-check (Python) — repo is NOT mypy-clean; only NEW errors matter
cd booking_system_backend && .venv/bin/mypy . --ignore-missing-imports

# Frontend
cd booking_system_frontend && npm run build   # TypeScript compile + Vite
cd booking_system_frontend && npm run lint

# Java hold service
cd booking_system_inventory_hold_service && mvn test
cd booking_system_inventory_hold_service && mvn spring-boot:run   # Java 17 or 21 ONLY

# E2E (requires built Java jar + backend venv)
cd e2e && ./run-native.sh
E2E_RUN_SLOW=1 cd e2e && ./run-native.sh    # includes ~90s hold auto-expiry test
```

## Critical footguns

- **`FastMCP` must be instantiated BEFORE `FastAPI`** — [`server.py`](booking_system_backend/server.py) does this; swapping breaks lifespan composition.
- **`FastApiMCP` auto-generates MCP tools from all FastAPI routes** — no manual MCP tool registration; adding a REST route is sufficient.
- **Service functions return `Model | ErrorResponse`, never raise** — callers use `isinstance(result, ErrorResponse)`. REST layer maps `error_code` → HTTP status.
- **`book_flight()` validates both `user_id` AND `name`** — name mismatch → `NAME_MISMATCH` error, not 404.
- **MCP tools bypass FastAPI DI** — use `SessionLocal()` / `db.close()` directly; `Depends(get_db)` is only for REST endpoints.
- **Tests patch `SessionLocal` in TWO places** — both `db.SessionLocal` and `server.SessionLocal` in [`conftest.py`](booking_system_backend/tests/conftest.py). Patching one leaves MCP tools hitting the real DB.
- **Java proxy returns `{"error":"..."}` with HTTP 200** — `httpx.HTTPError` is caught and swallowed. Never check status alone; call `assertNotProxyError()` (see [`api.ts`](booking_system_frontend/src/services/api.ts)).
- **Java 17 or 21 only** — Lombok breaks on 22+. Preflight warns if wrong version.
- **`booking.db` and `holds.db` are committed artefacts** — do not delete; a lifecycle hook blocks the commit if you do.
- **Committing with a red backend suite is blocked** — `gate-commit.sh` runs `pytest` on every `git commit`. Check `.bob/hooks/state/.last-block` when a tool call is blocked.
- **mypy-check hook runs on every Python file write** — it only reports errors NEW since the baseline in `.bob/hooks/mypy-baseline.txt`. Regenerate baseline with `.bob/hooks/gen-mypy-baseline.sh` after intentional type surface changes.
- **`SEED_DEMO_DATA=true`** re-seeds on every start (only if DB empty). Set `false` to preserve data across restarts.
- **Docker Compose Java service is opt-in** — needs `--profile hold-service`; `e2e/docker-compose.e2e.yml` enables it unconditionally.
- **`GET /bookings/{booking_id}`** (in [`routers/booking_detail.py`](booking_system_backend/routers/booking_detail.py)) requires `X-User-Email` header and enforces ownership — unlike all other booking endpoints which use `user_id` in the path/body.

## Architecture

```
booking_system_backend/          Python/FastAPI + FastMCP — port 8001
  server.py                        Entry point; REST + MCP (auto-generated) + Java proxy
  routers/booking_detail.py        GET /bookings/{id} — IDOR-protected, X-User-Email header
  services/{booking,flight,user}.py  Business logic; return Union types, no exceptions
  models.py / schemas.py / db.py   ORM, Pydantic, engine+SessionLocal+get_db()
  tests/                           pytest; in-memory SQLite StaticPool; 72 tests

booking_system_inventory_hold_service/   Java 17/Spring Boot 3 — port 8080
  hold.duration.minutes=15 (application.properties)
  HoldExpirationScheduler runs every 60s
  On confirmHold: calls Python POST /internal/bookings/from-hold

booking_system_frontend/         React 19/TypeScript/Vite — port 5173
  services/api.ts                  All HTTP; check body.error, not HTTP status
  hooks/useUser.tsx                UserProvider; persists to localStorage key "galaxium_user"
  utils/holdStorage.ts             Holds persisted to "galaxium_holds_{userId}"
```

**Hold flow:** Frontend → `POST /quotes` (Python proxy) → Java → `POST /quotes/{id}/holds` → Python proxy → on confirm: Java → Python `/internal/bookings/from-hold` → real Booking row.

## Code conventions

**Python:** `snake_case` functions/variables; `PascalCase` classes/Pydantic models. Ruff ignores `B008` (FastAPI `Depends()` in signatures is intentional). New endpoints need both a REST route and matching MCP exposure (auto via `FastApiMCP`). Logging in `booking_detail.py` uses SHA-256 hashed email — never log raw PII.

**TypeScript/React:** `camelCase` functions/variables; `PascalCase` components/types. Custom Tailwind tokens only: `space-dark`, `space-blue`, `cosmic-purple`, `nebula-pink`, `alien-green`, `solar-orange`, `star-white`. Vite dev server proxies `/api` → `http://localhost:8001` (strips the `/api` prefix). `VITE_API_URL` env var overrides the base URL.

**Java:** Lombok `@Data`/`@Builder`/`@RequiredArgsConstructor` throughout — no manual getters/setters. All service methods `@Transactional`. `PYTHON_BACKEND_URL` env var overrides Python backend address (default `http://localhost:8001`).

**Never edit:** `booking_system_inventory_hold_service/target/`, `booking_system_frontend/dist/`, `scripts/terraform/.terraform/`.
