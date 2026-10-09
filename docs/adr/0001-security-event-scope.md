# ADR-0001: Explicit Scope for Security Events

**Status:** Accepted  
**Date:** 2026-10-09

## Context

The Security Event data model requires an organization reference, but authentication attempts can fail before an organization is resolved. Assigning such an event to a default tenant would violate tenant isolation. Creating a separate platform-event table would add a second event model before a requirement justifies it.

## Decision

Use one Security Event model with explicit tenant or platform scope:

- A non-null `organization_id` means the event belongs to that tenant.
- A null `organization_id` means the event is platform-scoped because no organization was resolved.
- Never infer a tenant from an unknown organization slug or assign the event to a default tenant.
- `user_id` may be null when no user was resolved.
- `activity_events.organization_id` remains required; this decision changes only `security_events`.
- Organization-level monitoring may access only events for the authenticated user's organization. Platform-scoped events are restricted to authorized platform-level monitoring.
- Authentication responses remain generic and must not reveal whether the organization, account, or password was valid.
- Event metadata must be minimal and sanitized. Passwords, session tokens, and other secrets must never be recorded.

## Consequences

The `security_events.organization_id` column is nullable, and monitoring/authorization logic must distinguish null platform scope from tenant scope. This does not authorize organization-level users to read platform-scoped events.

## Follow-up Decisions

- Add event-visibility tests when the security-event read/monitoring API is implemented.
