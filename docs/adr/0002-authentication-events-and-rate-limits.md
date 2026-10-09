# ADR-0002: Authentication Events and Rate Limits

**Status:** Accepted  
**Date:** 2026-10-09

## Context

AEGIS uses organization-scoped identities, so authentication failures may occur before an organization or user can be resolved. Authentication monitoring must preserve tenant isolation while recording these failures. Repeated attempts must be bounded across application instances without introducing a separate cache service or process-local counters.

## Decision

### Security Event Severity

Allowed severity values are `INFO`, `LOW`, `MEDIUM`, and `HIGH`, enforced by model choices and a database check constraint.

| Event | Severity |
| --- | --- |
| `LOGIN_SUCCESS` | `INFO` |
| `LOGIN_FAILURE`, including a rate-limit trigger | `MEDIUM` |
| `LOGOUT` | `INFO` |

Other event types require an explicit severity mapping before implementation.

### Login Rate Limits

- Use a rolling 15-minute window.
- Block an organization-scoped normalized account identifier for 15 minutes after five failures.
- Independently block a source IP for 15 minutes after twenty failures.
- A successful login clears the account failure counter but not the source-IP counter.
- Return generic failure/rate-limit messages that do not reveal whether an organization or account exists.
- Record authentication failures and rate-limit triggers as `LOGIN_FAILURE` Security Events; rate-limit metadata contains only whether a limit triggered and its scope.
- Store counter keys as HMAC-SHA-256 digests derived using Django's secret key. Do not persist raw account identifiers, IP addresses, passwords, or session tokens in the counter table.
- Store counters in the shared PostgreSQL database and lock rows transactionally while updating them. Process-local counters are not acceptable.
- Use the direct request source address. Never trust arbitrary forwarded-IP headers; a deployment must explicitly configure trusted proxies before forwarding headers can be used.
- A periodic `cleanup_auth_rate_limits` management command removes stale counter rows while retaining active blocks. Deployment-specific scheduling remains configuration work.

## Consequences

This decision adds the `authentication_rate_limit_counters` table and its migration. Concurrent behavior must be verified on PostgreSQL because SQLite does not implement PostgreSQL row-lock semantics. Independent account and IP limits, generic responses, and security monitoring mitigate account-lockout abuse. Progressive delays and additional controls are not part of this decision.
