# Getting Started with Galaxium Travels

This tutorial walks you through the key workflows as a developer: searching for flights, booking a seat, and using the quote-and-hold workflow. It assumes you have the app running locally — see [CONTRIBUTING.md](../CONTRIBUTING.md#development-setup) if you haven't set it up yet.

## What you'll learn

- How the backend API is structured and how to call it
- The difference between a direct booking and a quote → hold → confirm booking
- How error responses work (they're different from what you might expect)
- How the frontend talks to the backend
- How to run a booking end-to-end from the command line

---

## 1. Exploring the API with Swagger UI

With the backend running, open **http://localhost:8001/docs**. This is the live Swagger UI — every endpoint is documented and executable from the browser.

The endpoints are grouped by tag:

| Tag | What it covers |
|---|---|
| **Health** | `GET /` — service liveness check |
| **Flights** | `GET /flights` — list and filter available flights |
| **Bookings** | `POST /book`, `GET /bookings/{user_id}`, `POST /cancel/{id}` |
| **Users** | `POST /register`, `GET /user` |
| **Quotes** | `POST /quotes`, `GET /quotes/{id}` — proxied to Java hold service |
| **Holds** | `POST /quotes/{id}/holds`, `GET /holds/{id}`, confirm, release |
| **Internal** | `POST /internal/bookings/from-hold` — called by Java, not by clients |

---

## 2. A direct booking (the simple path)

### Step 1 — Find a flight

```bash
curl -s http://localhost:8001/flights | python3 -m json.tool | head -60
```

Pick any `flight_id` from the response. Each flight shows three prices and three seat-availability counters:

```json
{
  "flight_id": 1,
  "origin": "Earth",
  "destination": "Mars",
  "departure_time": "2099-01-01 09:00",
  "arrival_time": "2099-01-01 17:00",
  "base_price": 1000000,
  "economy_seats_available": 6,
  "business_seats_available": 3,
  "galaxium_seats_available": 1,
  "economy_price": 1000000,
  "business_price": 2500000,
  "galaxium_price": 5000000
}
```

### Step 2 — Get your user ID

The demo data includes 10 pre-seeded users. Look up Alice:

```bash
curl -s "http://localhost:8001/user?name=Alice&email=alice@example.com"
```

```json
{ "user_id": 1, "name": "Alice", "email": "alice@example.com" }
```

### Step 3 — Book the flight

```bash
curl -s -X POST http://localhost:8001/book \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "name": "Alice",
    "flight_id": 1,
    "seat_class": "economy"
  }' | python3 -m json.tool
```

```json
{
  "booking_id": 21,
  "user_id": 1,
  "flight_id": 1,
  "status": "booked",
  "booking_time": "2099-...",
  "seat_class": "economy",
  "price_paid": 1000000
}
```

> **Why does `book_flight()` check both `user_id` and `name`?**
> This is an intentional non-standard security pattern. If the `name` doesn't match what's in the database for that `user_id`, the booking is rejected with a `NAME_MISMATCH` error. This protects against accidental bookings with a wrong user ID.

### Step 4 — Cancel the booking

```bash
curl -s -X POST http://localhost:8001/cancel/21
```

Cancelling restores the seat counter for the correct class.

---

## 3. Understanding error responses

Service functions in this project **never throw exceptions**. Instead they return a `BookingOut | ErrorResponse` union type. The REST layer converts `ErrorResponse` into the appropriate HTTP status code.

```python
# From services/booking.py
result = booking.book_flight(db, user_id=99, name="Nobody", flight_id=1)
if isinstance(result, ErrorResponse):
    print(result.error_code)   # "USER_NOT_FOUND"
    print(result.details)      # human-readable explanation
```

From the client side, a failed booking returns HTTP 404 or 409 with this body:

```json
{
  "success": false,
  "error": "User not found",
  "error_code": "USER_NOT_FOUND",
  "details": "User with ID 99 is not registered..."
}
```

**In the frontend**, the Axios interceptor in [`api.ts`](../booking_system_frontend/src/services/api.ts) re-throws these as rejected promises. Use the `isErrorResponse()` helper or check `result.success === false`.

---

## 4. The quote → hold → confirm workflow

This is the more complex path powered by the Java hold service. It's useful when a user wants to reserve a seat for a few minutes before committing to payment.

> **Prerequisite:** The Java hold service must be running on `:8080`.

### Step 1 — Create a quote

```bash
curl -s -X POST http://localhost:8001/quotes \
  -H "Content-Type: application/json" \
  -d '{
    "flightId": 1,
    "seatClass": "business",
    "quantity": 1,
    "travelerId": 1,
    "travelerName": "Alice"
  }' | python3 -m json.tool
```

```json
{
  "quoteId": "q-abc123",
  "flightId": 1,
  "seatClass": "business",
  "pricePerSeat": 2500000,
  "totalPrice": 2500000,
  "expiresAt": "2099-01-01T09:05:00Z",
  "status": "CREATED"
}
```

### Step 2 — Create a hold

```bash
curl -s -X POST http://localhost:8001/quotes/q-abc123/holds | python3 -m json.tool
```

```json
{
  "holdId": "h-xyz789",
  "quoteId": "q-abc123",
  "status": "HELD",
  "reservedUntil": "2099-01-01T09:20:00Z"
}
```

The hold lasts **15 minutes** by default. After that, the Java scheduler expires it automatically.

### Step 3 — Confirm the hold

```bash
curl -s -X POST http://localhost:8001/holds/h-xyz789/confirm
```

On success, the Java service calls the Python backend's internal endpoint (`POST /internal/bookings/from-hold`), which creates the real booking in the SQLite/PostgreSQL database. The hold status changes to `CONFIRMED` and `externalBookingReference` contains the new `booking_id`.

### Step 4 — Or release the hold

```bash
curl -s -X POST http://localhost:8001/holds/h-xyz789/release
```

This frees the reserved slot without creating a booking.

---

## 5. Filtering flights

The `/flights` endpoint supports rich filtering:

```bash
# Flights from Earth to Mars with economy seats available
curl "http://localhost:8001/flights?origin=Earth&destination=Mars&has_economy=true"

# Flights sorted by price descending, under 2,000,000 credits
curl "http://localhost:8001/flights?max_price=2000000&sort=price&order=desc"

# Outer-planet routes departing in the morning
curl "http://localhost:8001/flights?route_category=outer_planets&departure_time_period=morning"
```

Filter parameters are documented in detail at `/docs`.

---

## 6. Registering a new user

```bash
curl -s -X POST http://localhost:8001/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Zara", "email": "zara@neptune.com"}' | python3 -m json.tool
```

Email addresses are normalised to lowercase and must be unique. The returned `user_id` is what you'll pass to `book_flight`.

---

## 7. Frontend walkthrough

With both the backend and frontend running:

1. Open **http://localhost:5173**
2. Click **Sign in** and enter any demo user credentials — e.g. `Alice` / `alice@example.com`
3. Browse the **Flights** page; use the filters to narrow results
4. Click **Book** on a flight, select a seat class, confirm
5. Visit **My Bookings** to see all your bookings and any active holds

The frontend stores the signed-in user in `localStorage` under the key `galaxium_user`. Clearing storage or clicking Sign Out logs you out.

---

## 8. Next steps

- **Read [CONTRIBUTING.md](../CONTRIBUTING.md)** to understand the test strategy and code style rules before making changes.
- **Read [docs/architecture.md](architecture.md)** for a deep-dive into why certain decisions were made (MCP tool generation, dual-session pattern, proxy error handling).
- **Browse the Swagger UI** at `/docs` — every endpoint is interactive and shows request/response schemas.
- **Look at the tests** in [`booking_system_backend/tests/`](../booking_system_backend/tests/) for concrete examples of how each service function behaves.
