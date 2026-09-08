# Security Audit Findings — Galaxium Travels

**Audit standard:** OWASP ASVS Level 1
**Scope:** Python/FastAPI backend, Java Spring Boot hold service
**Control families audited:** V4 (Access Control), V5 (Input Validation), V13 (API Security), V14 (HTTP Headers/CORS)

---

## Overall Summary

| Control Group | Controls Checked | Pass | Fail | N/A |
|---|---|---|---|---|
| V4 — Access Control | 3 | 0 | 3 | 0 |
| V5 — Input Validation | 1 | 0 | 1 | 0 |
| V13 — API Security | 1 | 0 | 1 | 0 |
| V14 — HTTP Headers/CORS | 2 | 0 | 2 | 0 |
| **Total** | **7** | **0** | **7** | **0** |

**Overall posture:** The application has no authentication or authorisation layer on any endpoint, making every resource reachable by any unauthenticated caller with knowledge of a numeric ID. Combined with missing security headers, a wildcard CORS policy, and unvalidated string inputs, the attack surface is broad and the risk is rated **Critical** overall.

---

## Sub-Task 1 — Access Control (V4)

### Phase 1 — Discovery

`server.py` defines all REST routes without any authentication `Depends(...)` injection. There is no middleware, decorator, or HTTP bearer-token check anywhere in the file. The booking service functions operate purely on caller-supplied integer IDs with no verification that the caller is the resource owner. The Java `HoldController` carries no Spring Security annotations or servlet filter.

### Phase 2 — Audit Results

| Control | Result |
|---|---|
| V4.1.3 — Users can only access their own resources | **FAIL** |
| V4.1.5 — Access control denies by default | **FAIL** |
| V4.2.1 — IDOR protection on sensitive resources | **FAIL** |

### Phase 3 — Findings

---

**Finding 1:**
- **Rule:** ASVS V4.1.3
- **Severity:** Critical
- **File:** `booking_system_backend/server.py`
- **Line:** 169–172
- **Issue:** `GET /bookings/{user_id}` returns all bookings for any user ID supplied by the caller; there is no check that the authenticated principal owns the requested `user_id`.
- **Fix:** Require an authenticated session token and verify that the token's subject matches the requested `user_id` before querying the database.

---

**Finding 2:**
- **Rule:** ASVS V4.1.5
- **Severity:** Critical
- **File:** `booking_system_backend/server.py`
- **Line:** 44–337
- **Issue:** No authentication middleware or dependency exists anywhere in the FastAPI application; every endpoint is reachable by unauthenticated requests, which violates the deny-by-default principle.
- **Fix:** Add an authentication dependency (e.g. OAuth 2 / JWT bearer validation via `Depends(verify_token)`) and apply it globally via an `app.dependency_overrides` default or per-router dependency.

---

**Finding 3:**
- **Rule:** ASVS V4.2.1
- **Severity:** Critical
- **File:** `booking_system_backend/server.py`, `booking_system_backend/services/booking.py`
- **Line:** server.py 175–186; booking.py 93–123
- **Issue:** `POST /cancel/{booking_id}` accepts any integer `booking_id`; `cancel_booking()` fetches and cancels the booking without verifying that the caller is the booking's owner, enabling any user to cancel another user's booking by guessing or iterating IDs.
- **Fix:** After fetching the booking, compare `booking.user_id` against the authenticated caller's identity and return HTTP 403 if they do not match.

---

**Finding 4:**
- **Rule:** ASVS V4.2.1
- **Severity:** Critical
- **File:** `booking_system_backend/server.py`
- **Line:** 221–237
- **Issue:** `POST /internal/bookings/from-hold` is publicly reachable via the internet; it accepts raw traveler data and creates a real booking — an unauthenticated attacker can forge bookings by calling this endpoint directly.
- **Fix:** Restrict this endpoint to internal network traffic only (e.g. via a network policy or reverse-proxy ACL), or add a shared-secret header that only the Java service knows and validate it in the handler.

---

**Finding 5:**
- **Rule:** ASVS V4.2.1
- **Severity:** High
- **File:** `booking_system_inventory_hold_service/src/main/java/com/galaxium/holdservice/api/HoldController.java`
- **Line:** 19–70
- **Issue:** `POST /quotes/{quoteId}/holds`, `POST /holds/{holdId}/confirm`, and `POST /holds/{holdId}/release` carry no authentication annotation or Spring Security filter; any caller who guesses a UUID can confirm or release another user's hold.
- **Fix:** Integrate Spring Security, add `@PreAuthorize` on sensitive methods, and validate hold ownership against the authenticated caller's identity.

---

### Phase 4 — Summary

- **Controls checked:** 3 (V4.1.3, V4.1.5, V4.2.1)
- **Pass:** 0 | **Fail:** 3 | **N/A:** 0
- The backend has zero authentication or authorisation enforcement. Every booking, cancellation, and hold operation is vulnerable to IDOR and unauthorised access by any network-reachable caller.

---

## Sub-Task 2 — Input Validation (V5)

### Phase 1 — Discovery

Pydantic models are used for `POST /book` and `POST /register` endpoints. However, string fields carry no `max_length` constraints. Three proxy endpoints (`/quotes`, `/quotes/{id}/holds`, `/internal/bookings/from-hold`) accept raw `dict` bodies, bypassing Pydantic validation entirely. The Java `CreateQuoteRequest` DTO uses Bean Validation (`@NotBlank`, `@Min`) but `seatClass` has no `@Pattern` allowlist and `quantity` has no `@Max` upper-bound.

### Phase 2 — Audit Results

| Control | Result |
|---|---|
| V5.1.1 — All string inputs have defined maximum length constraints | **FAIL** |

### Phase 3 — Findings

---

**Finding 6:**
- **Rule:** ASVS V5.1.1
- **Severity:** Medium
- **File:** `booking_system_backend/schemas.py`
- **Line:** 52–53
- **Issue:** `BookingRequest.name` is declared as a plain `str` with no `max_length` constraint, allowing arbitrarily long strings that can cause excessive memory use or denial-of-service via oversized payloads.
- **Fix:** Add `name: str = Field(..., max_length=200)` and import `Field` from `pydantic`.

---

**Finding 7:**
- **Rule:** ASVS V5.1.1
- **Severity:** Medium
- **File:** `booking_system_backend/schemas.py`
- **Line:** 71–72
- **Issue:** `UserRegistration.name` and `UserRegistration.email` are plain `str` fields with no length upper bound, enabling oversized registration payloads.
- **Fix:** Apply `Field(..., max_length=200)` to `name` and `Field(..., max_length=254)` (the RFC 5321 limit) to `email`.

---

**Finding 8:**
- **Rule:** ASVS V5.1.1
- **Severity:** High
- **File:** `booking_system_backend/server.py`
- **Line:** 222, 243, 274
- **Issue:** Three endpoints (`/internal/bookings/from-hold`, `POST /quotes`, `POST /quotes/{id}/holds`) accept `dict` as their request body type, which means FastAPI performs no schema validation, length constraints, or type checking on the incoming JSON.
- **Fix:** Define typed Pydantic models (`HoldBookingRequest`, `CreateQuoteRequest`) for each endpoint and replace `dict` with the appropriate model.

---

**Finding 9:**
- **Rule:** ASVS V5.1.1
- **Severity:** Medium
- **File:** `booking_system_inventory_hold_service/src/main/java/com/galaxium/holdservice/api/dto/CreateQuoteRequest.java`
- **Line:** 21, 24
- **Issue:** `seatClass` has no `@Pattern` constraint to restrict it to valid values (economy/business/galaxium), and `quantity` has `@Min(1)` but no `@Max`, allowing arbitrarily large seat quantities.
- **Fix:** Add `@Pattern(regexp = "^(economy|business|galaxium)$")` to `seatClass` and `@Max(9)` (or a business-appropriate upper bound) to `quantity`.

---

### Phase 4 — Summary

- **Controls checked:** 1 (V5.1.1)
- **Pass:** 0 | **Fail:** 1 | **N/A:** 0
- All major input paths are missing length constraints, and three endpoints bypass Pydantic validation entirely by accepting raw `dict` bodies. The Java DTO is better annotated but still lacks an allowlist on the seat-class field and an upper bound on quantity.

---

## Sub-Task 3 — API Security (V13)

### Phase 1 — Discovery

`GET /user` (server.py line 203) declares `name: str` and `email: str` as plain function parameters with no `Query(...)` wrapper — FastAPI maps these directly from URL query parameters, placing PII and pseudo-credentials in the request URL (and therefore in web server logs, browser history, and Referer headers). `GET /flights` parameters are purely operational (dates, prices, seat class) with no PII. The `FastApiMCP` mount at line 336 automatically exposes every registered FastAPI route as an MCP tool with no auth boundary.

### Phase 2 — Audit Results

| Control | Result |
|---|---|
| V13.1.3 — API endpoints do not accept credentials or PII in URL query parameters | **FAIL** |

### Phase 3 — Findings

---

**Finding 10:**
- **Rule:** ASVS V13.1.3
- **Severity:** High
- **File:** `booking_system_backend/server.py`
- **Line:** 202–213
- **Issue:** `GET /user?name=Alice&email=alice@example.com` accepts the user's name and email address as URL query parameters; these values are logged by web servers, stored in browser history, and may leak via `Referer` headers to third-party resources.
- **Fix:** Change the endpoint to `POST /user` with a Pydantic request body, or pass `name` and `email` in HTTP headers; never accept PII or credentials in query strings.

---

**Finding 11:**
- **Rule:** ASVS V13.1.3
- **Severity:** High
- **File:** `booking_system_backend/server.py`
- **Line:** 336–337
- **Issue:** `FastApiMCP(app)` mounts MCP tool bindings for every FastAPI route — including all unauthenticated booking, cancellation, and user-lookup routes — with no authentication or authorisation boundary, expanding the unauthenticated attack surface to AI-agent callers.
- **Fix:** Pass an `auth_middleware` or restrict MCP tool exposure to non-sensitive routes; at minimum, ensure the MCP mount is placed behind the same authentication layer as the REST API once auth is added.

---

### Phase 4 — Summary

- **Controls checked:** 1 (V13.1.3)
- **Pass:** 0 | **Fail:** 1 | **N/A:** 0
- PII (name and email) is accepted as URL query parameters on the user-lookup endpoint, which violates ASVS V13.1.3 and contradicts the project's own security guidelines. The MCP surface compounds this by exposing all routes to agent callers without any authentication requirement.

---

## Sub-Task 4 — HTTP Headers and CORS (V14)

### Phase 1 — Discovery

`CORS_ORIGINS` defaults to `"*"` when the environment variable is unset (server.py line 53). `CORSMiddleware` is added with `allow_credentials=True` (line 58) and `allow_origins=["*"]` (line 57). Per the CORS specification, a browser will refuse a credentialed cross-origin request when the server responds with `Access-Control-Allow-Origin: *` — but the permissive wildcard is still returned for non-credentialed requests, and the intent is clearly to allow all origins. No security-header middleware (e.g. `SecurityHeadersMiddleware`, `Starlette`-level header injection, or equivalent) is present anywhere in the file; there are no `Content-Security-Policy`, `X-Frame-Options`, or `X-Content-Type-Options` headers set.

### Phase 2 — Audit Results

| Control | Result |
|---|---|
| V14.4.1 — HTTP responses include appropriate security headers (CSP, X-Frame-Options, X-Content-Type-Options) | **FAIL** |
| V14.5.3 — CORS origin validated against explicit allowlist; wildcard not permitted | **FAIL** |

### Phase 3 — Findings

---

**Finding 12:**
- **Rule:** ASVS V14.4.1
- **Severity:** Medium
- **File:** `booking_system_backend/server.py`
- **Line:** 44–61
- **Issue:** No `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, or `Strict-Transport-Security` headers are set on any HTTP response; the application is vulnerable to clickjacking, MIME-type sniffing attacks, and cross-site scripting amplification.
- **Fix:** Add a custom Starlette middleware (or use `secure` / `starlette-security-headers`) that injects `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Content-Security-Policy: default-src 'self'`, and `Strict-Transport-Security: max-age=31536000; includeSubDomains` on every response.

---

**Finding 13:**
- **Rule:** ASVS V14.5.3
- **Severity:** High
- **File:** `booking_system_backend/server.py`
- **Line:** 53, 55–61
- **Issue:** `CORS_ORIGINS` defaults to `"*"` when not set, and `CORSMiddleware` is configured with `allow_origins=["*"]` and `allow_credentials=True`; this combination sends a wildcard `Access-Control-Allow-Origin` header to all requestors and signals intent to allow credentialed requests from any origin.
- **Fix:** Set `CORS_ORIGINS` to an explicit comma-separated allowlist of known frontend origins (e.g. `https://galaxium.example.com`) and remove the `"*"` default; keep `allow_credentials=True` only if the frontend genuinely requires it.

---

### Phase 4 — Summary

- **Controls checked:** 2 (V14.4.1, V14.5.3)
- **Pass:** 0 | **Fail:** 2 | **N/A:** 0
- No security response headers of any kind are present, and the CORS configuration defaults to accepting all origins — both findings represent standard hardening gaps that are straightforward to remediate with a middleware addition and an environment-variable change.

---

*Audit performed against OWASP ASVS Level 1. All findings reference the source file at the time of audit.*
