# ADR-011: Permission-Aware Privileged Content Preview

**Status:** Accepted  
**Date:** 2026-10-19

## Context

Content Administrators and Content Managers need to inspect protected content
they manage without receiving consumer grants or assignments. Reusing the
consumer delivery path by granting `SECURE_DELIVERY` would change the
consumer authorization model and mix operator previews with consumer access
metrics.

## Decision

- Add the explicit `CONTENT_PREVIEW` permission for Administrator and Content
  Manager through the existing role-seeding baseline.
- Require `CONTENT_PREVIEW`, `CONTENT_VIEW`, `VERSION_VIEW`, and an active
  organization user to start a preview.
- Permit non-archived Content and DRAFT or PUBLISHED ContentVersions in the
  user's organization. Reject archived records and tenant/content mismatches.
- Bind preview access records to the initiating user, organization, Content,
  and selected version. Recheck permissions and resource state on every
  rendered-page request.
- Reuse the protected renderer and apply the existing contextual watermark
  with a visible `PREVIEW` label. Never return a source file or storage URL.
- Record preview starts in the existing AuditRecord system and viewer events
  in ActivityEvent. Use `ContentAccess.access_context` to distinguish preview
  from consumer access, prohibit Program association for preview records, and
  exclude preview records from consumer analytics, reports, and access-burst
  signals.
- Do not create grants or assignments, call AI services, add external
  infrastructure, or create a separate preview session/logging system.

## Consequences

The implementation adds an explicit permission, an access-context field and
database constraint, an audit action constraint update, two API operations,
and a preview route in the existing React protected viewer. Migrations must be
applied through the approved deployment/recovery procedure before the feature
is enabled on a persistent environment. Preview is not a consumer access
path, and watermarked rendered pages remain capturable by an authorized user.
