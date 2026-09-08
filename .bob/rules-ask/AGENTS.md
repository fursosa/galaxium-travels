# AGENTS.md — Ask (question-answering) mode

This file provides guidance to agents when working with code in this repository.

## Non-obvious context for answering questions

- **`server.py` is NOT a typical FastAPI file** — it contains REST endpoints, MCP tools (auto-generated), AND proxy pass-through endpoints to the Java service, all in one file. When asked about an endpoint, check whether it's a direct handler or a proxy.
- **HTTP status codes are unreliable for hold/quote endpoints** — the Python proxy catches all `httpx.HTTPError` and returns `{"error":"..."}` with HTTP 200. The only reliable signal is the presence of an `error` key in the response body.
- **`GET /bookings/{booking_id}` and `GET /bookings/{user_id}` are different endpoints** — the former is in `routers/booking_detail.py` (requires `X-User-Email`, returns a single booking, enforces ownership). The latter is in `server.py` (no auth, returns all bookings for a user). They share a path pattern but differ in every other way.
- **The frontend never calls the Java service directly** — all Java calls route through Python proxy endpoints. The Java service's only outbound call is to Python `POST /internal/bookings/from-hold`.
- **`booking.db` and `holds.db` in the repo root are real SQLite files**, not fixtures — they are committed and seeded by the app on startup (only if empty).
- **The mypy baseline file** at `.bob/hooks/mypy-baseline.txt` lists 17 known SQLAlchemy/Pydantic type errors that are pre-existing and suppressed. The repo is intentionally not mypy-clean.
- **`inject-pending.sh` is currently disabled** (all lines commented out) — the PostToolUse type-error injection loop is scaffolded but inactive.
- **Frontend API base URL:** in dev, Vite proxies `/api` → `http://localhost:8001` and strips the prefix. In production, `VITE_API_URL` sets the base directly. The `root_path="/api"` on the FastAPI app aligns with ALB routing, not Vite's proxy.
