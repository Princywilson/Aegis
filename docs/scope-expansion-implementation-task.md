# AEGIS — Capability A, B & C: Implementation, Security Hardening, Frontend Integration and Acceptance Testing

## 1. Role and Objective

Act as a senior full-stack engineer and security-focused software architect working on **AEGIS — Enterprise Knowledge Protection and Delivery Platform**.

The objective is to complete the approved v1 scope of the following three capabilities:

- **Capability A:** Context-Aware Content Access Policies — currently implemented as advisory, rule-based risk signals.
- **Capability B:** Content Exposure Risk Investigation — currently implemented as an organization-scoped backend model and API workflow.
- **Capability C:** Permission-Aware Enterprise Knowledge Assistant — currently implemented as permission-filtered, metadata-only content retrieval.

These capabilities are partially implemented. Do not rebuild them from scratch or assume the existing implementation is correct merely because a few tests pass.

Inspect the actual repository, understand the existing code and decisions, implement the remaining work, integrate the capabilities into the React application, execute appropriate tests, and update the implementation documentation with verified results.

The final outcome must be production-conscious, secure, maintainable, domain-neutral, multi-tenant, and consistent with the existing AEGIS architecture.

## 2. Mandatory Repository and Documentation Review

Before modifying code, inspect the current repository and its working state.

Read and follow the applicable project rules, including:

- `Agent/Rules/rules/aegis-development.mdc`
- `docs/scope-expansion-implementation-guide.md`
- `docs/implementation-guide.md.md`
- `docs/implementation-status.md`
- `docs/prd.md`
- `docs/srs.md`
- `docs/domain-model.md`
- `docs/business-rule.md`
- `docs/ard.md`
- `docs/system-architecture.md`
- `docs/functional-architecture.md`
- `docs/data-architecture.md`
- `docs/api-specification.md`
- `docs/implementation-setup.md`
- `docs/user-manual.md`
- Relevant existing ADRs and capability-specific documentation.

If a listed path differs in the repository, locate the actual file rather than assuming it exists.

Inspect the actual implementation and tests, particularly:

**Backend**
- `backend/knowledge/risk_signals.py`
- `backend/knowledge/retrieval.py`
- `backend/knowledge/views.py`
- `backend/knowledge/urls.py`
- `backend/knowledge/models.py`
- `backend/knowledge/services.py`
- `backend/knowledge/delivery.py`
- `backend/knowledge/tests_risk_and_assistant.py`
- `backend/accountability/models.py`
- `backend/accountability/services.py`
- `backend/accountability/serializers.py`
- `backend/accountability/views.py`
- `backend/accountability/urls.py`
- Existing accountability tests, audit services, security-event recording, RBAC, permission definitions, Program Access Grant enforcement, and migrations.

**Frontend**
- `frontend/src/App.jsx`
- Existing routing, navigation, API client, authentication/session handling, permission helpers, reusable components, and tests.
- `frontend/package.json` and the existing dependency lockfile.

These are starting points, not an exhaustive file list. Follow the actual call paths and relationships needed to understand each capability.

### Baseline and change discipline

1. Inspect `git status`, the current diff, and untracked files before editing.
2. Preserve unrelated changes, including pre-existing untracked files. Do not clean the repository merely to obtain a clean working tree.
3. Identify existing tests and verification results, distinguishing historical results from checks run during this task.
4. Confirm the currently configured database and environment before any database operation.
5. Reuse existing models, permission codes, audit services, security-event mechanisms, API conventions, frontend patterns, and terminology wherever appropriate.
6. Do not duplicate existing functionality or create competing implementations.
7. Do not make architectural changes, add dependencies, or introduce external providers without a justified and approved requirement.
8. If an essential business rule is genuinely ambiguous and cannot be resolved from the approved requirements, stop that specific decision and report the precise question. Continue independent work that does not depend on it.

Before implementation, provide a concise summary of the current state, identified gaps, intended changes, affected files/modules, test plan, and any genuine approval blockers. Then proceed with implementation without waiting for another prompt where the approved requirements are sufficient.

## 3. Non-Negotiable Product and Architecture Boundaries

The following are binding constraints.

### Technology stack

- Frontend: React.
- Backend: Python Django and the existing API framework.
- Primary database: PostgreSQL.
- Continue using the current application structure and established conventions.

### Security and tenancy

- All organizational data must remain tenant-scoped.
- Derive the organization from the authenticated user's trusted context, not a client-supplied organization ID.
- Enforce authorization on the backend, independently of frontend navigation and controls.
- Apply the existing RBAC permissions and resource-specific access rules.
- Prevent cross-organization access, identifier-based information leakage, and unauthorized metadata disclosure.
- Preserve session authentication, CSRF protection, secure error handling, and existing API response conventions.
- Validate inputs, bound pagination, handle expected errors, and use transactions where multiple persistent changes must succeed or fail together.
- Never log passwords, credentials, session tokens, raw sensitive notes, or unnecessary content in audit records.
- Keep audit history append-only using the existing audit architecture.
- Do not expose source files or create public file URLs as part of these capabilities.

### Explicit capability boundaries

**Capability A is advisory only.** A risk signal must never grant, deny, suspend, revoke, or otherwise modify access. Do not add a contextual authorization engine or change delivery decisions based on a signal.

**Capability B is an evidence-based investigation workflow.** Evidence must refer to actual, authorized, tenant-scoped records. Do not allow arbitrary JSON references to become trusted evidence.

**Capability C is retrieval-only v1.** It retrieves authorized content metadata using the existing title/description matching approach. Do not represent it as semantic search, generative RAG, an AI-powered assistant, or document-body retrieval.

Do not introduce an AI provider, model calls, vector database, embeddings, persistent indexing infrastructure, new external services, or other out-of-scope architecture.

Do not add industry-specific terminology. Reuse AEGIS's approved domain-neutral terminology.

## 4. Capability A — Complete Advisory Risk Signals

### Existing behavior

At task start, the implementation derived `ACCESS_BURST` from granted `ContentAccess` records (at least four accesses across at least three Content IDs in 24 hours), but derived `REPEATED_DENIALS` from denied `ContentAccess` records even though the normal denial path writes `ACCESS_DENIED` `SecurityEvent` records. Its date filters and pagination also needed hardening, and there was no React risk-review page.

**Capability A implementation update:** The denial detector now uses the normal `SecurityEvent` source; both rules identify qualifying rolling 24-hour windows. The endpoints apply validated timezone-aware inclusive time filters and bounded pagination, and the React application has a permission-gated risk-review page. Focused tests and frontend build/tests are recorded in `docs/implementation-status.md`. The rules remain advisory; their thresholds/severities have not been validated as product policy or through labeled data.

### Required implementation

#### A1. Verify and document the rules

Trace the actual data sources, query boundaries, event timestamps, severity assignments, and permission checks.

Treat the existing thresholds and 24-hour window as existing implementation behavior, not automatically approved business policy.

- Reuse the established values for compatibility while they remain within the approved scope.
- Check the implementation guide and recorded decisions for an explicit approval of these definitions.
- If approval is absent, do not silently invent or change business thresholds. Clearly document the current behavior and identify the precise product decision required before calling the rule set formally approved.
- Keep the rules deterministic, explainable, and testable.

#### A2. Correct the repeated-denial evidence source

Use the existing `SecurityEvent(event_type="ACCESS_DENIED")` evidence path for repeated denied-access signals.

- Inspect the event model and `record_access_denied()` implementation before changing queries.
- Derive repeated-denial counts from the authoritative event source using the correct organization, time-window, and event semantics.
- Reuse existing security-event logging rather than duplicating denial events.
- Do not change the normal access-denial response or create duplicate audit/security records merely to satisfy the detector.
- Ensure the event source distinguishes the relevant denied-content activity sufficiently for the approved rule. If the event schema lacks required context, document the limitation and make the smallest justified change, with explicit approval if a business or schema decision is needed.

#### A3. Implement correct date filtering

- Implement the advertised `from` and `to` query parameters using a consistent, documented timestamp convention.
- Validate the format and reject invalid ranges, including `from > to`.
- Apply filters to the actual event timestamps used by the signal rules.
- Handle boundary timestamps and timezone-aware comparisons correctly.
- Preserve any existing default lookback behavior where appropriate and document it.
- Do not return results that fall outside the requested interval.

#### A4. Validate and bound pagination

- Validate page and page-size inputs.
- Reject malformed, non-positive, or otherwise invalid values according to the established API conventions.
- Enforce a reasonable maximum page size.
- Handle empty results and out-of-range pages predictably.
- Validate supported filters rather than silently accepting misleading input.

#### A5. Preserve tenant isolation and advisory behavior

- Scope every signal query and summary to the authenticated user's organization.
- Apply the existing permission checks consistently to list and summary endpoints.
- Ensure one organization's events cannot influence another organization's signal counts.
- Prove that generating, viewing, or dismissing a signal, if dismissal is already supported, does not modify grants, assignments, Content Access records, user status, or delivery authorization.
- Do not invent persistent signal acknowledgement, dismissal, or remediation workflows if they are not already approved.

#### A6. Add a React risk-review experience

Integrate the existing endpoints into the React application using established navigation, API client, loading, error, empty-state, and permission-handling patterns.

The interface should allow authorized users to:

- View the available advisory signals.
- Understand the signal type, severity, detection window, and supporting counts or references.
- Filter by the supported time interval.
- Navigate paginated results.
- Distinguish advisory findings from enforced access decisions.

Do not expose unnecessary personal information or records outside the user's organization. Do not label the rules as statistically validated, machine-learning-based, or AI-driven.

#### A7. Capability A tests

Add or extend backend tests covering:

- Each rule's exact threshold and just-below-threshold behavior.
- Multiple accesses to the same Content versus accesses across distinct Content IDs.
- Events inside and outside the 24-hour window.
- Repeated denials sourced from the normal `ACCESS_DENIED` event path.
- Insufficient history and empty results.
- Date filters, inclusive/exclusive boundaries as specified, invalid dates, and reversed ranges.
- Pagination validation and maximum page size.
- Missing permissions and unauthorized access.
- Cross-organization isolation, including competing tenant evidence.
- Correct severity and supporting metadata.
- Proof that risk-signal evaluation never changes access or grant state.
- Regression behavior for existing security-event recording.

Use the existing testing conventions and PostgreSQL integration where database behavior matters.

## 5. Capability B — Complete Content Exposure Risk Investigation

### Existing behavior

The current backend contains:

- `RiskInvestigation` and its migrations.
- Organization-scoped list, create, detail, and update endpoints.
- Existing `SECURITY_EVENT_VIEW_ORGANIZATION` permission checks and organization-scoped queries.
- Server-side state-transition validation.
- Atomic audit records for creation and every meaningful update, without storing raw administrative text.
- Bounded, validated references to visible Content denial Security Events and relevant Audit Records; evidence is re-resolved with current organization and source permissions on reads.
- A React investigation list/detail/create/edit workflow with status and severity filters, pagination, evidence selection, and API error feedback.

Automated Capability B verification currently passes the focused backend and frontend tests and the production frontend build. Authenticated browser/API acceptance is still pending and must be recorded separately; the broader backend regression suite has not yet been rerun for this continuation.

Migrations `0010`–`0012` have already been applied to the persistent `aegis` database according to the latest verified implementation status. Do not rerun destructive recovery procedures or assume that this database is disposable.

### Required implementation

#### B1. Review the existing investigation domain

Inspect the actual model, serializers, endpoints, audit action choices, migrations, and service layer.

Preserve existing field names and lifecycle behavior unless an explicitly approved requirement requires a change.

The current transition rules are:

- `OPEN` → `IN_REVIEW` or `DISMISSED`.
- `IN_REVIEW` → `RESOLVED` or `DISMISSED`.
- Terminal states have no outgoing transitions.

Retain these rules and make sure all state changes are validated on the backend.

#### B2. Make mutations and audit writes atomic

Ensure each investigation creation or update and its corresponding `AuditRecord` are committed together in one database transaction.

If an audit write fails, the investigation mutation must roll back.

Audit the meaningful business changes, including:

- Investigation creation.
- Status transitions.
- Title changes.
- Summary changes.
- Severity changes.
- Notes changes.

Use the existing audit action conventions or add a narrowly scoped migration if a new action is genuinely required.

Audit records should contain the actor, organization, investigation reference, action, timestamp, and minimal change metadata necessary for accountability.

**Do not store the full raw notes or summary merely to prove that a change occurred.** Record an appropriate change indicator or safe metadata, following existing audit conventions.

Preserve audit immutability.

#### B3. Validate and authorize evidence references

The current `evidence` JSON must not accept arbitrary unverified entries.

Implement a clear, bounded evidence-reference contract based on the existing supported records, such as relevant Security Events, Audit Records, or other approved source types.

For every evidence reference:

- Validate the supported reference type and identifier format.
- Resolve the reference against an actual persisted record.
- Verify the source record belongs to the same organization.
- Apply the required permission and visibility checks.
- Reject malformed, nonexistent, unsupported, cross-tenant, or unauthorized references without revealing sensitive information.
- Prevent duplicate references and unreasonable evidence-list sizes where appropriate.
- Preserve source-record immutability; an investigation must not rewrite or delete source evidence.

Keep evidence metadata minimal. Do not copy sensitive source-record payloads into the investigation when a reference is sufficient.

Provide a joined, read-only evidence detail or timeline API if needed to support the workflow. It must reapply tenant and authorization checks when evidence is read, not merely trust validation performed when it was attached.

#### B4. Harden filtering and pagination

- Validate status and severity filters against the existing choices.
- Reject invalid values and unsupported parameters according to the established API convention.
- Implement bounded pagination.
- Ensure list and detail queries are organization-scoped.
- Avoid returning raw internal data that the caller is not authorized to view.

#### B5. Complete the React investigation workflow

Add the authorized user-facing investigation experience to the existing application.

Include:

- A paginated investigation list.
- Supported status and severity filters.
- Investigation detail.
- Investigation creation with appropriate fields.
- Evidence selection or attachment using valid references.
- Evidence details or timeline where supported.
- Status transitions that reflect the approved lifecycle.
- Editing of supported title, summary, severity, and notes fields.
- Clear validation, loading, error, success, and empty states.

The frontend may hide unavailable actions for usability, but the backend must remain authoritative.

Ensure edits and status transitions cannot bypass validation through direct API requests.

#### B6. Capability B tests

Cover:

- Creation and creation audit.
- Every valid and invalid state transition.
- Terminal-state enforcement.
- Every audited editable field.
- Audit-write failure and transaction rollback for creation and updates.
- Permission failures for list, detail, create, edit, transition, and evidence access.
- Cross-organization list, detail, mutation, and evidence-reference isolation.
- Malformed, nonexistent, unsupported, duplicate, and unauthorized evidence references.
- Evidence source immutability.
- Valid evidence retrieval and visibility filtering.
- Invalid status/severity filters and pagination boundaries.
- Safe audit metadata without unnecessary sensitive text.
- Concurrent or repeated updates where relevant to prevent inconsistent transitions.

Test the actual API and persistence behavior, not only serializer helper methods.

## 6. Capability C — Harden Permission-Aware Metadata Retrieval

### Existing behavior

`POST /api/v1/assistant/query/` searches the title and description of Content records using case-insensitive substring matching. The React application includes the metadata-only **Knowledge search** page.

It requires the existing search and view permissions and scopes results to the user's organization, published Content, and its published current version.

Content Consumers additionally require the applicable active Program, assignment, active unexpired Program Access Grant, and user/resource authorization context. The query verifies that the published current version belongs to the same Content and organization. Other roles follow their existing organization-wide Content permissions. Program names are included only if the caller has `PROGRAM_VIEW`, and are filtered through the same caller-visible Program queryset as the cited Content assignment.

The previous citation Program-name leakage and inaccurate active-grant wording have been corrected. The request requires exactly one string `question` field of 1–200 non-whitespace characters and returns at most five authorized metadata citations. Empty results contain no citations and do not reveal unauthorized Content metadata. Response status text is fixed, not generated.

Focused backend verification passes 23 tests and the broader `identity accountability knowledge` regression passes 168 tests against PostgreSQL. Frontend verification passes 19 tests and the production build. Coverage includes current permission and tenant checks, grant/assignment/program/version revocation or ineligibility, citation Program-name scope, same-organization unauthorized-source exclusion, invalid queries, empty results, result bounds, and no retrieval side effects. Authenticated browser/API acceptance remains pending. This implementation is not semantic document retrieval or generative RAG.

### Required implementation

#### C1. Centralize and verify the authorization boundary

Trace the existing content query, role determination, RBAC permissions, Program Access Grant checks, assignment relationships, Program status, and current-version lifecycle.

Reuse the existing authorization services where possible.

Every candidate result must be authorized according to the caller's actual role and the existing product rules.

For Content Consumers, verify all required conditions:

- Correct organization.
- Required search and view permissions.
- Published Content and published current version.
- Active Program.
- Valid assignment to the relevant Content through the Program.
- Active, unexpired Program Access Grant for the correct user and Program.

For other roles, apply the actual established permission rules rather than incorrectly forcing Content Consumer-specific grant requirements onto every caller.

Authorization must be checked server-side for each request. Do not rely on frontend filtering or prior successful requests.

#### C2. Fix citation metadata leakage

Ensure `program_names` and any equivalent metadata are derived only from Programs and assignments that are authorized for the current caller and the matched Content.

Do not return names of unrelated Programs merely because they share a Content assignment in the same organization.

Review all returned fields, including Content title, description, version details, identifiers, Program names, and source references, for unauthorized disclosure.

Return only metadata necessary for the supported retrieval use case.

#### C3. Correct response wording and behavior

- Do not claim all results are in active-grant scope when the caller's authorization model does not impose that exact rule.
- Return accurate, role-appropriate status messages.
- Handle blank or malformed queries with consistent validation errors.
- Bound query length and result count.
- Handle insufficient authorized sources without leaking the existence or metadata of unauthorized Content.
- Preserve the established API error envelope and response conventions.

The result must be explainable: a returned item should have a valid authorized source and appropriate citation metadata.

#### C4. Preserve the retrieval-only boundary

Do not introduce generation, model calls, semantic embeddings, document-body extraction, chunking, vector search, or a persistent index.

Do not describe metadata matches as a generated answer.

Keep the implementation modular so that future retrieval enhancements can be separately designed and approved.

#### C5. Add a React knowledge-assistant interface

Add a usable metadata-search interface in the React application.

Include:

- A query input.
- Input validation.
- Loading, error, and empty-result states.
- A list of authorized matching Content items.
- Appropriate citation/source metadata.
- Clear navigation to the corresponding Content detail or existing authorized workflow, where available.
- An explicit explanation that the current feature searches Content metadata rather than generating answers from document contents.

Do not add a chat transcript, AI-generated response, or fabricated citations.

#### C6. Capability C tests

Cover:

- Authorized matching results.
- Missing search or view permissions.
- Cross-organization isolation.
- Revoked and expired grants.
- Inactive Programs.
- Removed assignments.
- Missing or mismatched user grants.
- Unpublished Content and unpublished, stale, or invalid current versions.
- Role-specific authorization differences.
- Blank, malformed, oversized, and valid queries.
- No authorized results and insufficient-source behavior.
- Citation metadata restricted to the actual authorized Program/assignment scope.
- No unauthorized Content metadata or existence disclosure.
- Accurate response wording for each applicable role.
- Result limits and pagination if supported.
- Regression tests ensuring retrieval never changes access, grants, assignments, or Content state.

Use realistic fixtures with competing tenant and authorization contexts. A test that merely checks for one matching result and one cross-organization empty result is insufficient.

## 7. Frontend and API Integration Standards

All three capabilities must follow the existing React and Django conventions.

### Frontend

- Reuse the existing API client, session credentials, CSRF handling, routing, navigation, permission helpers, and UI components.
- Use real backend endpoints. Do not add mock or simulated production workflows.
- Handle API validation errors consistently.
- Support loading, empty, success, and failure states.
- Prevent duplicate submissions and accidental repeated mutations where appropriate.
- Provide usable pagination and filters where required.
- Keep components modular and consistent with the current application.
- Add automated component or integration tests using the existing test stack.
- Do not add a new frontend dependency unless justified and approved.

### Backend

- Use established serializers, services, views, permissions, URL conventions, and error envelopes.
- Keep business logic out of presentation-only code.
- Validate request bodies, query parameters, and identifiers.
- Enforce tenant isolation and permissions at every applicable boundary.
- Use database transactions for logically atomic business operations.
- Ensure list endpoints are bounded and do not create unbounded queries.
- Add appropriate indexes only when supported by query patterns and justified by the current schema.
- Avoid schema migrations unless genuinely required.
- If migrations are needed, inspect and explain the intended schema impact before applying them.

## 8. Database Safety and Migration Discipline

The configured persistent PostgreSQL database is named `aegis`. Existing application data must be preserved.

The latest implementation status reports migrations `accountability.0010`, `0011`, and `0012` applied successfully. Reconfirm the actual current repository and database state before relying on that report.

Mandatory rules:

1. Never reset, flush, drop, recreate, or fake migrations for the persistent `aegis` database.
2. Never overwrite or remove existing application data to make tests pass.
3. Never restore a backup over the persistent database as a convenience.
4. Never apply migrations to a production or persistent database without the required explicit approval.
5. Use Django's normal test database or an explicitly identified disposable PostgreSQL database for integration testing.
6. Verify the target database before any operation that creates, modifies, or deletes persistent database objects.
7. Preserve historical migrations.
8. Review generated migrations and their SQL before applying them.
9. Verify model/migration consistency with `makemigrations --check --dry-run`.
10. If no schema changes are required, do not create unnecessary migrations.

If a database operation is risky or its target cannot be confirmed, stop that operation and report the blocker.

## 9. Testing and Acceptance Verification

Testing is a mandatory deliverable, not an optional follow-up.

### Phase 1: Focused backend tests

Run the relevant Capability A, B, and C tests against PostgreSQL where applicable.

Add missing tests before treating a capability as complete.

### Phase 2: Existing backend regression suite

Run the relevant existing tests, including:

- Identity and authentication.
- Accountability, audit, and security events.
- Knowledge and content lifecycle.
- RBAC and permission enforcement.
- Program assignments and Program Access Grants.
- Secure content delivery.
- Activity, analytics, and reports.
- Existing integration and tenant-isolation tests.

Prefer the established full backend test command and run it against PostgreSQL. Follow the repository's actual test-discovery conventions.

Do not rely solely on SQLite results for PostgreSQL behavior, locking, constraints, or transaction semantics.

### Phase 3: Django and migration checks

Run:

- Django system check.
- Migration-drift check.
- Relevant migration-state inspection.
- `git diff --check`.

Report any existing or newly introduced warnings separately.

### Phase 4: Frontend verification

Run:

- Frontend automated tests.
- Production build.
- Browser/API integration tests where the existing environment supports them.

If you change frontend behavior, verify the relevant authenticated workflows against the actual Django API rather than relying only on mocked API responses.

### Phase 5: End-to-end acceptance

Exercise the following workflows with appropriate authorized and unauthorized test users.

**Capability A**
- Produce a signal from valid evidence.
- Confirm filters and pagination work.
- Confirm insufficient evidence does not trigger an unsupported signal.
- Confirm denied-access evidence comes from the real event path.
- Confirm risk-signal evaluation does not alter access authorization.

**Capability B**
- Create an investigation from authorized evidence.
- Read and edit it through the React application.
- Perform allowed state transitions and reject invalid transitions.
- Verify the corresponding audit entries.
- Verify an audit-write failure rolls back the business mutation.
- Verify unauthorized and cross-organization evidence cannot be attached or read.

**Capability C**
- Search for Content with an authorized user.
- Confirm only authorized matches are returned.
- Confirm inactive Programs, revoked/expired grants, removed assignments, and unpublished or stale Content do not leak results where the applicable role requires those restrictions.
- Confirm citation metadata does not reveal unrelated Program names.
- Confirm unauthorized users cannot bypass restrictions through direct API calls.

Use disposable test data and databases. Never modify persistent business data merely to demonstrate acceptance.

### Honest verification

For every test command, report the exact command and actual result.

Distinguish between:

- Passed.
- Failed.
- Skipped.
- Blocked by environment.
- Not run.

Do not report a test as passing because it passed historically. Do not claim browser verification without actually performing it. Do not claim production security sign-off from automated tests.

## 10. Documentation Updates

After implementation and testing, update the relevant existing documents, including:

- `docs/implementation-status.md`
- `docs/implementation-setup.md`
- `docs/user-manual.md`
- `docs/api-specification.md`
- `docs/functional-architecture.md`
- `docs/data-architecture.md`
- `docs/scope-expansion-implementation-guide.md`

Update only the sections affected by the actual implementation.

Document:

- What changed.
- Which API endpoints and React workflows are supported.
- The exact risk-rule behavior and any unresolved approval decisions.
- Investigation lifecycle and evidence-reference rules.
- Audit and transaction guarantees.
- Retrieval authorization and citation behavior.
- Known limitations.
- Test commands and actual outcomes.
- Remaining environment-specific checks.

Keep the PRD, SRS, architecture, and ADRs consistent with approved requirements. Do not silently broaden the product scope or rewrite approved requirements to match an incomplete implementation.

Do not mark a capability complete while required security tests, acceptance scenarios, or essential UI workflows remain unimplemented or unverified.

## 11. Execution Order

Work in the following sequence:

1. **Repository inspection and baseline** — review the working tree, rules, implementation guide, source code, migrations, and existing tests.
2. **Capability A** — correct the denial evidence source, date filtering, pagination, permissions, tenant isolation, frontend workflow, and tests.
3. **Capability B** — implement evidence validation, atomic audit behavior, audited edits, list validation, frontend workflow, and tests.
4. **Capability C** — fix authorization and citation metadata leakage, correct response semantics, add comprehensive authorization tests, and implement the metadata-search UI.
5. **Regression and integration testing** — run the focused PostgreSQL suites, existing backend regression tests, frontend tests/build, and applicable end-to-end checks.
6. **Documentation and handoff** — update the status and user-facing documentation with verified results and outstanding items.

Do not start all three capabilities with a large, unreviewable refactor. Make small, logically grouped changes, test them, and continue.

If an unrelated existing test fails, determine whether it is a regression or a pre-existing failure. Do not conceal it or make unrelated changes merely to obtain a passing suite.

## 12. Definition of Done

The work is complete only when all applicable criteria below are satisfied:

- [x] Capability A uses the correct evidence source, validates filters and pagination, preserves the advisory-only boundary, and has comprehensive focused tests.
- [x] Capability B validates and authorizes evidence, atomically persists mutations and audit records, audits meaningful edits, and has lifecycle/security tests.
- [x] Capability C enforces role-specific authorization, prevents citation metadata leakage, and has retrieval tests.
- [x] React workflows for A, B, and C use the existing API client, session/CSRF handling, and real backend endpoints.
- [x] Cross-organization isolation and permission boundaries are covered by automated PostgreSQL tests.
- [x] Existing backend functionality passes the broad regression suite; the persistent database was not modified during the Capability B/C continuation.
- [x] Required focused and broad PostgreSQL tests pass.
- [x] Frontend tests and production build pass.
- [x] Django system and migration-drift checks pass.
- [x] No migration drift or unintended schema change was introduced in this continuation.
- [x] Relevant API, data, functional, setup, user, guide, task, and status documentation reflects the implementation.
- [x] `git diff --check` passes.
- [x] No secrets, credentials, or sensitive user content were exposed in source code, test output, or audit metadata.
- [x] No unapproved AI, infrastructure, authorization-policy, or other scope expansion was introduced.
- [ ] Authenticated manual UI/API acceptance for A, B, and C is recorded in `docs/implementation-status.md`.

## 13. Final Handoff Format

At completion, provide a concise but evidence-based report containing:

1. **Overall status:** completed, partially completed, or blocked.
2. **Capability A:** changes, endpoints/UI, tests, and remaining limitations.
3. **Capability B:** changes, evidence/audit guarantees, endpoints/UI, tests, and remaining limitations.
4. **Capability C:** authorization corrections, metadata protection, endpoints/UI, tests, and remaining limitations.
5. **Files changed:** group by backend, frontend, tests, migrations, and documentation.
6. **Verification results:** exact commands and actual pass/fail/skip counts.
7. **Database safety:** database target used for testing, migration status, and confirmation of whether any persistent database was modified.
8. **Known gaps:** anything incomplete, blocked, not tested, or awaiting a product decision.
9. **Next action:** the single highest-priority remaining task, if any.

Do not report success based solely on implementation, a Django system check, or a small focused test suite.

**Start by inspecting the repository and current working tree. Then implement the approved scope in the sequence above, preserving existing AEGIS behavior and data throughout.**