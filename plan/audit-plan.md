# Security Audit Plan — Galaxium Travels

## Overview

This plan drives a structured OWASP ASVS Level 1 audit of the Galaxium Travels codebase,
focused on the high-risk areas identified during the earlier security exploration.

The audit is guided by the `asvs-audit` skill and covers four ASVS control families:

- **V4** — Access Control (general and operation-level)
- **V5** — Input Validation
- **V13** — Generic Web Service Security
- **V14** — HTTP Security Headers and CORS

Each sub-task is self-contained and maps to one or more ASVS control groups.
The auditor executes the phases in the `asvs-audit` skill (Discover → Audit → Findings →
Summary) for the files listed in each sub-task.

**Output:** All findings are written to `security/audit-findings.md`.
Create `security/` if it does not already exist before writing.

---

## Sub-Task 1 — Access Control Audit (V4.1 + V4.2)

**Status:** `[ ] pending`

### Intent
Verify whether the Python backend enforces any form of access control on the booking and
cancellation endpoints. These endpoints were flagged as IDOR candidates during exploration
because they accept caller-supplied resource IDs with no ownership or authentication check.

### Expected Outcomes
- ASVS controls V4.1.3, V4.1.5, and V4.2.1 recorded as PASS or FAIL with file + line
  evidence for each.
- Any IDOR findings documented in `security/audit-findings.md` with severity, file, line,
  issue, and fix.

### Todo List
1. Activate the `asvs-audit` skill.
2. Run **Phase 1 (Discover)** on the files listed in Relevant Context — read each file and
   summarise the access control patterns (or lack of them) present.
3. Run **Phase 2 (Audit)** — evaluate V4.1.3, V4.1.5, and V4.2.1 against the discovered
   patterns.
4. Run **Phase 3 (Generate Findings)** — produce a finding entry for every FAIL.
5. Run **Phase 4 (Summary)** — record pass/fail/N/A counts for this control group.
6. Create `security/` if it does not exist; write all findings and the summary to
   `security/audit-findings.md` under the heading `## Sub-Task 1 — Access Control (V4)`.

### Relevant Context
| File | Key Lines | Reason |
|---|---|---|
| `booking_system_backend/server.py` | 169–172 | `GET /bookings/{user_id}` — no auth dependency |
| `booking_system_backend/server.py` | 175–186 | `POST /cancel/{booking_id}` — no auth dependency |
| `booking_system_backend/server.py` | 221–237 | `POST /internal/bookings/from-hold` — publicly reachable internal endpoint |
| `booking_system_backend/services/booking.py` | 93–123 | `cancel_booking()` — no ownership check |
| `booking_system_backend/services/booking.py` | 126–129 | `get_bookings()` — no ownership check |
| `booking_system_inventory_hold_service/.../HoldController.java` | full file | Hold confirm/release with no auth |

---

## Sub-Task 2 — Input Validation Audit (V5.1)

**Status:** `[ ] pending`

### Intent
Verify that all string inputs across the Python API and the Java quote/hold service have
defined maximum length constraints and use typed validation models rather than raw
dictionaries.

### Expected Outcomes
- ASVS control V5.1.1 recorded as PASS or FAIL with file + line evidence.
- Findings documented for every unvalidated or length-unconstrained input path.

### Todo List
1. Activate the `asvs-audit` skill.
2. Run **Phase 1 (Discover)** on the files in Relevant Context — identify every place
   external input enters the application, and note whether a Pydantic model or Bean
   Validation annotation bounds it.
3. Run **Phase 2 (Audit)** — evaluate V5.1.1 for each identified input path.
4. Run **Phase 3 (Generate Findings)** — produce a finding for every FAIL.
5. Run **Phase 4 (Summary)** — record counts for this control group.
6. Append findings and summary to `security/audit-findings.md` under the heading
   `## Sub-Task 2 — Input Validation (V5)`.

### Relevant Context
| File | Key Lines | Reason |
|---|---|---|
| `booking_system_backend/schemas.py` | 9–30 | `FlightQueryParams` — defined but not used in route |
| `booking_system_backend/schemas.py` | 51–56 | `BookingRequest` — name field unbounded |
| `booking_system_backend/schemas.py` | 70–73 | `UserRegistration` — name and email unbounded |
| `booking_system_backend/server.py` | 221–237 | Raw `dict` body on internal endpoint |
| `booking_system_backend/server.py` | 242–256 | Raw `dict` body on `/quotes` proxy |
| `booking_system_backend/server.py` | 273–286 | Raw `dict` body on `/quotes/{id}/holds` proxy |
| `booking_system_inventory_hold_service/.../CreateQuoteRequest.java` | 20–25 | `seatClass` no allowlist; `quantity` no upper bound |

---

## Sub-Task 3 — API Security Audit (V13.1)

**Status:** `[ ] pending`

### Intent
Verify that API endpoints do not accept credentials or PII in URL query parameters, and
that the MCP tool surface does not introduce additional unauthenticated access paths beyond
what the REST API already exposes.

### Expected Outcomes
- ASVS control V13.1.3 recorded as PASS or FAIL with file + line evidence.
- Finding documented if `name` or `email` appear as query parameters on any endpoint.
- MCP exposure noted as a finding if all routes are mounted without an auth boundary.

### Todo List
1. Activate the `asvs-audit` skill.
2. Run **Phase 1 (Discover)** — identify every route that accepts `name`, `email`, `user_id`,
   or similar identity fields as query parameters, and confirm the MCP mount configuration.
3. Run **Phase 2 (Audit)** — evaluate V13.1.3.
4. Run **Phase 3 (Generate Findings)** — produce findings for every FAIL.
5. Run **Phase 4 (Summary)** — record counts for this control group.
6. Append findings and summary to `security/audit-findings.md` under the heading
   `## Sub-Task 3 — API Security (V13)`.

### Relevant Context
| File | Key Lines | Reason |
|---|---|---|
| `booking_system_backend/server.py` | 202–213 | `GET /user` accepts `name` and `email` as query params |
| `booking_system_backend/server.py` | 70–149 | `GET /flights` — inspect query params for PII |
| `booking_system_backend/server.py` | 336–337 | `FastApiMCP` mount — no auth boundary |

---

## Sub-Task 4 — HTTP Security Headers and CORS Audit (V14.4 + V14.5)

**Status:** `[ ] pending`

### Intent
Verify that HTTP responses include required security headers (CSP, X-Frame-Options,
X-Content-Type-Options) and that the CORS policy uses an explicit origin allowlist rather
than a wildcard default.

### Expected Outcomes
- ASVS controls V14.4.1 and V14.5.3 recorded as PASS or FAIL.
- Finding documented for the wildcard CORS default.
- Finding documented for any missing security response headers.

### Todo List
1. Activate the `asvs-audit` skill.
2. Run **Phase 1 (Discover)** — read the CORS and middleware configuration in `server.py`
   and check for any security-header middleware.
3. Run **Phase 2 (Audit)** — evaluate V14.4.1 and V14.5.3.
4. Run **Phase 3 (Generate Findings)** — produce findings for every FAIL.
5. Run **Phase 4 (Summary)** — record counts for this control group.
6. Append findings and summary to `security/audit-findings.md` under the heading
   `## Sub-Task 4 — HTTP Headers and CORS (V14)`.

### Relevant Context
| File | Key Lines | Reason |
|---|---|---|
| `booking_system_backend/server.py` | 53 | `CORS_ORIGINS` defaults to `"*"` |
| `booking_system_backend/server.py` | 55–61 | `CORSMiddleware` added with `allow_credentials=True` |
| `booking_system_backend/server.py` | 44–61 | Full FastAPI app setup — check for security-header middleware |

---

## Sub-Task 5 — Consolidate and Finalise Findings

**Status:** `[ ] pending`

### Intent
Produce a clean, complete audit report in `security/audit-findings.md` that aggregates all
sub-task findings, adds an overall summary, and is ready for stakeholder review.

### Expected Outcomes
- `security/audit-findings.md` contains all findings from sub-tasks 1–4.
- A consolidated summary table listing total controls checked, pass/fail/N/A counts, and an
  overall security posture assessment is present at the top of the file.
- The file is well-structured with clear headings and finding IDs that are unique across the
  whole report.

### Todo List
1. Read the current contents of `security/audit-findings.md`.
2. Renumber findings sequentially across all sections so IDs are globally unique (Finding 1,
   Finding 2 … Finding N).
3. Add a `## Overall Summary` section at the top of the file with a consolidated table and
   two-sentence posture assessment.
4. Verify the file is readable and well-formed markdown.

### Relevant Context
- Output file: `security/audit-findings.md`
- All content comes from the findings produced in sub-tasks 1–4.
