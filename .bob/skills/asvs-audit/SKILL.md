---
name: asvs-audit
description: >-
  Audits a codebase against OWASP ASVS Level 1 access control, input validation,
  API security, and configuration requirements.
metadata:
  disable-model-invocation: true
---

---
name: asvs-audit
description: Audit a codebase against OWASP ASVS Level 1 access control, input validation, API security, and configuration requirements and produce structured findings ready for SARIF and OSCAL export.
user-invocable: true
---

Perform a structured security audit of this codebase. Work through the following phases in order. Do not skip phases or combine them.

## Phase 1: Discover

Read and understand the application before auditing. Focus on:
- Entry points: main files, route definitions, controllers
- Authentication and session handling code
- Input validation and sanitization code
- Database query code
- Any files flagged as high-risk in earlier analysis

Summarize what you find before proceeding to Phase 2.

## Phase 2: Audit

Check each control below. For each one record: PASS, FAIL, or N/A.
For every FAIL, record the file path and line number.

### V4.1 General Access Control
- V4.1.3 — Users can only access their own resources; other users' data is not accessible
- V4.1.5 — Access control denies by default — unauthenticated requests are rejected

### V4.2 Operation Level Access Control
- V4.2.1 — Sensitive resources cannot be accessed by manipulating a predictable object ID (IDOR protection)

### V5.1 Input Validation
- V5.1.1 — All string inputs have defined maximum length constraints

### V13.1 Generic Web Service Security
- V13.1.3 — API endpoints do not accept credentials or PII in URL query parameters

### V14.4 HTTP Security Headers
- V14.4.1 — HTTP responses include appropriate security headers such as Content-Security-Policy, X-Frame-Options, and X-Content-Type-Options

### V14.5 HTTP Request Header Validation
- V14.5.3 — CORS origin is validated against an explicit allowlist — wildcard origins are not permitted

## Phase 3: Generate Findings

For each FAIL, produce a finding in this format:

**Finding [N]:**
- Rule: ASVS [control number]
- Severity: Critical / High / Medium / Low
- File: [path]
- Line: [number or range, if identifiable]
- Issue: [one sentence describing what was found]
- Fix: [one sentence describing the recommended change]

## Phase 4: Summary

Produce a short summary:
- Total controls checked
- Pass / Fail / N/A counts
- Two-sentence overall security posture assessment

Save the findings to the location specified by the plan or prompt that invoked this skill. Do not generate SARIF, OSCAL, or other report files — report generation is a separate task. Report that the audit is complete and wait for the next instruction.
