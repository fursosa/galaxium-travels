# Contributing to Galaxium Travels

Welcome! This guide will get you from zero to a working development environment and walk you through the contribution workflow.

## Table of contents

1. [Prerequisites](#prerequisites)
2. [Development setup](#development-setup)
3. [Project structure at a glance](#project-structure-at-a-glance)
4. [Running the tests](#running-the-tests)
5. [Making a change](#making-a-change)
6. [Submitting a pull request](#submitting-a-pull-request)
7. [Code style guidelines](#code-style-guidelines)
8. [Common pitfalls](#common-pitfalls)

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.8+ | Backend service |
| Node.js | 18+ | Frontend |
| Docker + Buildx | Latest stable | Full stack / e2e tests |
| Java | **17 or 21 only** | Hold service (Lombok breaks on 22+) |
| Maven | 3.8+ | Hold service build |

> **macOS users:** Use [Colima](https://github.com/abiosoft/colima) as your Docker runtime — see [Docker on macOS](#docker-on-macos) below.

---

## Development setup

### 1. Clone the repository

```bash
git clone https://github.com/your-org/galaxium-travels.git
cd galaxium-travels
```

### 2. Set up the Python backend

```bash
cd booking_system_backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Verify it works:

```bash
python server.py
# Open http://localhost:8001/docs in your browser
```

The database (`booking.db`) is created and seeded automatically on first run. To suppress re-seeding, set `SEED_DEMO_DATA=false`.

### 3. Set up the frontend

```bash
cd booking_system_frontend
npm install
npm run dev
# Open http://localhost:5173 in your browser
```

### 4. Set up the Java hold service (optional)

The hold service powers the quote → hold → confirm workflow. If you don't need it, the rest of the app runs fine without it.

```bash
# Confirm you have Java 17 or 21 — NOT 22+
java -version

cd booking_system_inventory_hold_service
mvn spring-boot:run
# Listens on :8080
```

If you manage multiple JDKs with [sdkman](https://sdkman.io/):

```bash
sdk use java 21.0.x-tem   # pick any 17 or 21 candidate
```

### 5. Start everything at once

```bash
./start.sh
```

Starts backend (`:8001`), frontend (`:5173`), and the Java hold service (`:8080`) if Maven and Java 17/21 are available.

### Docker on macOS

```bash
brew install colima docker docker-compose docker-buildx
colima start
```

Add to `~/.docker/config.json`:

```jsonc
{ "cliPluginsExtraDirs": ["/opt/homebrew/lib/docker/cli-plugins"] }
```

Verify before running compose commands:

```bash
docker ps            # should print an empty table, not an error
docker buildx version
```

---

## Project structure at a glance

```
booking_system_backend/
  server.py          ← entry point; REST + MCP tools + Java proxy
  services/          ← pure business logic; no HTTP, no FastAPI
  models.py          ← SQLAlchemy ORM (User, Flight, Booking)
  schemas.py         ← Pydantic request/response shapes
  db.py              ← engine, SessionLocal, get_db()
  seed.py            ← demo data (skipped when DB is non-empty)
  tests/             ← pytest, in-memory SQLite

booking_system_inventory_hold_service/
  src/main/java/com/galaxium/holdservice/
    api/             ← REST controllers
    service/         ← business logic (@Transactional)
    domain/          ← JPA entities
    scheduler/       ← hold expiry job (every 60 s)
    client/          ← calls Python /internal/bookings/from-hold

booking_system_frontend/
  src/
    pages/           ← route-level components
    components/      ← reusable UI pieces
    services/api.ts  ← all HTTP calls; check `error` key, not status
    hooks/           ← useUser (context + localStorage)
    types/index.ts   ← shared TypeScript interfaces
```

---

## Running the tests

### Backend unit tests (fast, no Docker)

```bash
cd booking_system_backend
source .venv/bin/activate
pytest                           # run all tests
pytest -v                        # verbose output
pytest tests/test_services.py    # service layer only
pytest tests/test_rest.py        # REST endpoints only
pytest --cov=. --cov-report=term-missing   # with coverage
```

Tests run against an **in-memory SQLite database**. The fixture in [`conftest.py`](booking_system_backend/tests/conftest.py) patches `SessionLocal` in both the `db` module and the `server` module. If you add a new MCP tool that opens its own session, you must patch its import too — otherwise it will hit the real `booking.db`.

### Frontend type checking and lint

```bash
cd booking_system_frontend
npm run build    # TypeScript compile + Vite build (catches type errors)
npm run lint     # ESLint
```

### Java hold service tests

```bash
cd booking_system_inventory_hold_service
mvn test
```

### End-to-end tests

**Native runner** (recommended — no Docker required for the stack itself):

```bash
cd e2e
./run-native.sh                           # smoke + holds tests
E2E_RUN_SLOW=1 ./run-native.sh            # include auto-expiry test (~90 s)
E2E_BASE_URL=http://localhost:8001 ./run-native.sh  # against a running stack
```

Prerequisites: the backend venv must exist and the Java jar must be pre-built:

```bash
# Build the jar once
cd booking_system_inventory_hold_service
mvn package -DskipTests
```

**Docker runner** (uses `e2e/docker-compose.e2e.yml`):

```bash
./test.sh
```

---

## Making a change

### Workflow overview

```
main  ──────────────────────────────────►
        │                   ▲
        └── feature/xyz ────┘
              (PR)
```

1. Create a branch from `main` with a descriptive prefix:
   - `feature/add-flight-filter`
   - `fix/hold-expiry-race-condition`
   - `docs/update-contributing`

2. Make your changes (see the service-specific notes below).

3. Run the relevant tests before pushing (see [Running the tests](#running-the-tests)).

4. Open a pull request against `main`.

### Adding a backend endpoint

Every new capability needs **both** a REST handler and (because the app is also MCP-accessible) an entry in `server.py`. The pattern:

```python
# 1. Add the service function in services/booking.py (or flight.py / user.py)
def do_thing(db: Session, arg: str) -> ThingOut | ErrorResponse:
    """One-line summary of what this does.

    Args:
        db: SQLAlchemy session.
        arg: Description of the argument.

    Returns:
        ThingOut on success, ErrorResponse on failure.
    """
    ...

# 2. Add the REST endpoint in server.py
@app.post("/thing", response_model=ThingOut, tags=["Things"])
def do_thing_endpoint(request: ThingRequest, db: Session = Depends(get_db)):
    """Human-readable description shown in Swagger UI."""
    result = booking.do_thing(db, request.arg)
    if isinstance(result, ErrorResponse):
        raise HTTPException(status_code=..., detail=result.model_dump())
    return result
```

Because `FastApiMCP` auto-generates MCP tools from all FastAPI routes, the REST endpoint registration is sufficient — no separate MCP registration is needed.

### Adding a frontend API call

Add the function to [`api.ts`](booking_system_frontend/src/services/api.ts) following the existing JSDoc pattern:

```typescript
/**
 * Brief description of what this call does.
 * @param arg - What the argument represents.
 * @returns The response data on success; throws ErrorResponse on failure.
 */
export const doThing = async (arg: string): Promise<ThingResponse> => {
  const response = await api.post('/thing', { arg });
  return response.data;
};
```

> ⚠️ **Always check for proxy errors on hold/quote endpoints.** The Python proxy returns `{"error": "..."}` with HTTP 200 when the Java service is down. Call `assertNotProxyError(response.data)` before returning from any quote/hold API function.

### Modifying hold durations

If you change `hold.duration.minutes` in `application.properties`, update the matching timeout in [`e2e/test_holds.py`](e2e/test_holds.py) so the auto-expiry test stays accurate.

---

## Submitting a pull request

1. **Run the tests** for every service you touched.
2. **Write a clear PR title**: `feat: add seat upgrade endpoint`, `fix: restore seat count on cancel`, `docs: clarify proxy error pattern`.
3. **Describe what changed and why** in the PR body — architectural decisions, trade-offs, links to related issues.
4. **Keep PRs focused** — one logical change per PR makes review faster.
5. **Do not delete `booking.db` or `holds.db`** — a lifecycle hook will block the commit if you do.
6. **Do not commit while the backend test suite is red** — the hook checks `pytest` before allowing a push.

---

## Code style guidelines

### Python (backend)

- **Naming:** `snake_case` for functions and variables; `PascalCase` for classes and Pydantic models.
- **Linting:** Ruff is configured in [`ruff.toml`](booking_system_backend/ruff.toml). Run `ruff check .` before committing.
- **Error handling:** Service functions return `SomeModel | ErrorResponse` — they do **not** raise exceptions. Callers use `isinstance(result, ErrorResponse)` to branch.
- **Database sessions:** REST endpoints get a session via `Depends(get_db)`. MCP tools (and `seed.py`) open `SessionLocal()` directly and close it in a `finally` block.
- **Docstrings:** All public service functions need a docstring with `Args:` and `Returns:` sections (Google style).

```python
def register_user(db: Session, name: str, email: str) -> UserOut | ErrorResponse:
    """Register a new user with a unique email address.

    Args:
        db: SQLAlchemy database session.
        name: Display name for the new user.
        email: Email address — normalised to lowercase; must be unique.

    Returns:
        UserOut with the newly assigned user_id on success.
        ErrorResponse with error_code INVALID_EMAIL or EMAIL_EXISTS on failure.
    """
```

### TypeScript (frontend)

- **Naming:** `camelCase` for variables and functions; `PascalCase` for components and types.
- **Error detection:** Never rely on HTTP status alone. Check `response.data.error` (proxy errors) or use `isErrorResponse()` (backend errors).
- **JSDoc:** All exported functions and components should have a brief JSDoc comment.
- **Tailwind:** Use the custom space-themed tokens only — `space-dark`, `space-blue`, `cosmic-purple`, `nebula-pink`, `alien-green`, `solar-orange`, `star-white`. Do not assume standard Tailwind colour names work.

### Java (hold service)

- **Style:** Lombok `@Data`, `@Builder`, `@RequiredArgsConstructor` — no manual getters/setters.
- **Transactions:** Service methods are `@Transactional`; controllers are not.
- **Never edit** files inside `target/` (Maven output directory).

---

## Common pitfalls

These are known gotchas that have tripped up contributors before:

| Situation | What goes wrong | Fix |
|---|---|---|
| Swapping `FastMCP` and `FastAPI` instantiation order in `server.py` | Lifespan composition breaks; app won't start | `FastMCP` must be created **before** `FastAPI` |
| Patching only `db.SessionLocal` in tests | MCP tools still hit the real `booking.db` | Patch both `db.SessionLocal` **and** `server.SessionLocal` in `conftest.py` |
| Using Java 22+ for the hold service | Lombok annotation processing fails at compile time | Use Java 17 or 21 only |
| Checking HTTP status on proxy responses | Java 404s come back as HTTP 200 with `{"error": "..."}` in the body | Check the body for an `error` key |
| Running `docker compose up` without `--profile hold-service` | Java service doesn't start | Add `--profile hold-service` or use `e2e/docker-compose.e2e.yml` |
| Deleting `booking.db` or `holds.db` | A lifecycle hook blocks the commit | Restore the files; they are committed artefacts that seed local dev |

If a tool call or hook is blocked, check `.bob/hooks/state/.last-block` for the full explanation.
