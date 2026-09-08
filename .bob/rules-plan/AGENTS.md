# AGENTS.md — Plan mode

This file provides guidance to agents when working with code in this repository.

## Non-obvious architectural constraints for planning

- **`FastMCP` must be instantiated before `FastAPI`** — this is a hard lifespan composition constraint, not just convention. Any plan that restructures `server.py` startup must preserve this order.
- **Service layer is the only safe extension point** — `services/` functions have no I/O other than the DB session argument. Adding external HTTP calls, file I/O, or environment reads to a service function breaks the test isolation pattern (in-memory SQLite + monkeypatched `SessionLocal`).
- **Tests patch two module-level names** — `db.SessionLocal` and `server.SessionLocal`. Any plan that adds a third module importing `SessionLocal` must include a corresponding patch in `conftest.py`, or MCP tool tests will silently hit the real DB.
- **The Java service has one outbound dependency: Python `/internal/bookings/from-hold`** — the Java service is otherwise self-contained. Plans that change the Python booking API must also update `PythonBackendClient.java` and the matching e2e tests.
- **Hold duration is configured in two places** — `application.properties` (`hold.duration.minutes`) and the e2e runner which overrides it to 1 minute for fast testing. Plans touching hold expiry must account for both.
- **The `gate-commit.sh` hook blocks commits when the 72-test backend suite is red** — any plan that touches Python files must include a "run pytest" verification step before the commit step.
- **`routers/` is the only place with IDOR protection and auth headers** — the rest of the API trusts `user_id` values from the request body. Plans adding new endpoints that return per-user data must decide which pattern to follow and document it explicitly.
- **`SQLite` in ECS is intentional ephemeral storage** — `DATABASE_URL` is unset in production ECS tasks by design. Plans assuming durable cloud storage must provision the `DATABASE_URL` env var and account for the SQLite → PostgreSQL schema difference (`check_same_thread` connect arg).
- **`FastApiMCP` mounts at `app` level** — MCP tool availability is coupled to FastAPI startup. Plans that split the app into multiple FastAPI instances (e.g., for versioning) would break the single-MCP-mount assumption.
