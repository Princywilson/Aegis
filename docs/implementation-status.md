# AEGIS Implementation Status

**Last reviewed:** 2026-10-19
**Source of truth:** [Implementation Guide](implementation-guide.md.md)

This file records implementation progress and how to test the work that exists. A check passing on SQLite is not evidence that PostgreSQL integration has passed.

## Milestone 0: Development Foundation

### Verified

- Inspected the Django project structure, settings, API routing, requirements, environment template, migrations, and Docker Compose configuration.
- Python 3.12.10 and the pinned backend requirements are available in `venv`.
- Docker Engine 29.8.2 and PostgreSQL 16 are available. The PostgreSQL integration validations on 2026-10-10 used the configured `aegis` database; Docker/PostgreSQL was responsive during M7 verification.
- The local PostgreSQL role credentials were aligned to the current Compose configuration to restore host authentication; no application data was changed.
- Django's system check passes.
- A custom-format backup of the existing `aegis` database, `aegis-before-migration-repair-20261009.dump`, was created locally, its archive listing verified, and restored into a disposable database before repair.
- The existing `aegis` database was repaired from the verified backup: the current identity migration is recorded, the login column and missing permission/group join tables match the current model, and the tenant-email constraint uses its current name.
- M3-M10 migrations, including the current RBAC, Program, Access Grant, Content Access, and Activity schema, apply on `aegis`; `showmigrations` reports them applied and `makemigrations --check --dry-run` reports no changes. M11-M14 add no backend migrations.
- Temporary validation and repair-clone databases were removed after successful verification.
- Node.js 24.20.0 and npm 11.19.0 were installed for the React frontend. The frontend package manifest and lockfile are present.

### Not yet complete

- `backend/.env` is absent. PostgreSQL validation used process-local environment variables; no credentials were added to source or documentation.
- The legacy recorder entry `identity.0001_initial_organization_and_user` is retained as historical metadata; the current `identity.0001_initial` entry is also recorded, so Django's current migration graph is consistent.
- The frontend development server proxies `/api` to `http://127.0.0.1:8000`, so the Django API must be started separately for authenticated browser testing.
- The guide's clean-worktree criterion is not met. The pre-existing untracked `Notes.md` was left untouched; implementation changes are also currently uncommitted.

## Milestone 1: Organization + Custom Identity

### Implemented

- `Organization` has a UUID primary key, name, unique slug, lifecycle status, and timestamps.
- `User` is the configured Django custom user model with a UUID primary key, organization relationship, email, password hash, active/inactive status, names, and timestamps.
- User email uniqueness is scoped to `(organization, email)`, matching the tenant model.
- `AUTH_USER_MODEL` points to `identity.User`.
- A user's tenant context is available through `user.organization`; no tenant is selected from an arbitrary request parameter.
- The initial identity migration is present at `backend/identity/migrations/0001_initial.py`.

### Verification

- Identity behavior and migrations pass against the configured PostgreSQL database.
- The repaired database's `users.last_login_at`, tenant-scoped email constraint, and Django permission/group relations were exercised through the ORM.

## Milestone 2: Authentication + Session Management

### Implemented

- Organization-aware authentication using organization slug, email, and password.
- Generic authentication failures for wrong credentials, unknown organizations, and inactive users.
- `GET /api/v1/auth/csrf/`, `POST /api/v1/auth/login/`, `POST /api/v1/auth/logout/`, and `GET /api/v1/auth/me/`.
- Django session cookies, CSRF protection for unsafe requests, and credentialed development CORS.
- A consistent JSON error envelope for API and CSRF failures.
- At the end of M2, `/me` returned identity and organization details with empty role/permission arrays; the M3 implementation now populates those arrays from AEGIS role assignments.
- Shared account/IP rate-limit counters use PostgreSQL row locks and hashed keys. PostgreSQL-only concurrency tests cover both the five-failure account threshold and the twenty-failure source-IP threshold across independent database connections.
- The source-IP API test confirms the rate-limit key is derived from `REMOTE_ADDR`, not an arbitrary `X-Forwarded-For` header.

### Verification

- The complete Django suite passes against the configured PostgreSQL database: 35 tests, including the PostgreSQL-only concurrency tests.
- The SQLite suite passes 33 tests; its two PostgreSQL-only concurrency tests are skipped. SQLite results do not substitute for the PostgreSQL result above.
- Django's system check passes and `makemigrations --check --dry-run` reports no migration drift.
- Separate Python worker processes concurrently submitted 8 attempts for one account and 25 attempts across accounts for one source IP on the repaired clone. The persisted counters capped at 5 and 20 respectively, with 25 expected failure events.
- Production session/CSRF cookie settings were checked with `DEBUG=False`: HttpOnly, Secure, CSRF Secure, and the configured 14-day session age.
- The threshold-trigger event assertion is order-independent, avoiding reliance on tied event timestamps.

### Operational follow-ups

- Production scheduling for `cleanup_auth_rate_limits` is environment-specific and is not configured in this repository.
- Organization security-event reads are tenant-scoped and exclude platform-level rows through the M10 API; platform-level monitoring remains outside the organization API.
- M10 `ActivityEvent` requires organization ownership and validates linked user/resource/access tenant and context consistency.

## How to Test Now

### SQLite development checks

Run from the repository root. Test-only environment values let Django load settings when `backend/.env` is absent; the command then replaces the database with in-memory SQLite. It checks configuration and migration consistency, then runs the identity, accountability, and knowledge tests, including M6 program/assignment coverage. PostgreSQL-only tests are skipped by their explicit database requirements.

```powershell
.\venv\Scripts\python.exe -c "import os,sys; os.environ.update({'DJANGO_SECRET_KEY':'sqlite-test-only-secret','DJANGO_DEBUG':'true','POSTGRES_DB':'unused','POSTGRES_USER':'unused','POSTGRES_PASSWORD':'unused','POSTGRES_HOST':'127.0.0.1','POSTGRES_PORT':'5432'}); sys.path.insert(0,'backend'); os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); from django.conf import settings; settings.DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':':memory:'}}; import django; django.setup(); from django.core.management import call_command; call_command('check'); call_command('makemigrations','--check','--dry-run'); call_command('test','identity','accountability','knowledge',verbosity=1)"
```

SQLite test results are development evidence only. They do not verify PostgreSQL integration or PostgreSQL-specific locking, constraints, and concurrency behavior.

### PostgreSQL integration checks

The RBAC and M4-M8 migrations are applied to the configured `aegis` PostgreSQL database. On 2026-10-10, migrations `knowledge.0004`, `accountability.0007`, `knowledge.0005`, and `knowledge.0006` applied successfully; Django's system check passed; `makemigrations --check --dry-run` reported no changes; and `.\venv\Scripts\python.exe backend\manage.py test identity accountability knowledge` passed all 114 tests with no skips against PostgreSQL. This is PostgreSQL integration evidence for M3-M8. The earlier SQLite M3 and M6 runs are separate development evidence. Running bare `manage.py test` from the repository root discovers zero tests in this layout.

## Scope Expansion Status (updated 2026-10-19)

### Overall assessment

The scope expansion is **implemented within the approved v1 boundaries; final manual acceptance remains pending**. Capability A is advisory rule-based risk detection, not contextual authorization enforcement. Capability B has its audited API and React workflow. Capability C has secured metadata-only retrieval and a React search page, not generative RAG.

- The current Capability A implementation is advisory risk detection, not contextual access-policy enforcement.
- Capability B is an organization-scoped investigation workflow, with evidence and audit behavior described below; its automated tests pass, but authenticated manual acceptance has not been recorded.
- Capability C is permission-filtered metadata retrieval, not semantic retrieval over document contents and not a generative RAG assistant.

No new AI provider, vector database, persistent chunk/index store, or dependency has been added. Risk detection and retrieval make no model calls. React pages now exist for risk signals, investigations, and metadata search. Do not describe these features as AI-powered or as completed contextual policy enforcement / generative RAG.

### Scope-expansion guide phase tracking

| Guide phase | Status | Evidence / remaining work |
|---|---|---|
| Phase 1 — repository and documentation review | Done for the prior design/implementation gate; refreshed feature-focused source and documentation review on 2026-10-19 | Reviewed scope-relevant sections of the applicable `Agent/` rule, scope-expansion guide, requirements/architecture/API/data/business-rule docs, current feature source, tests, React routes, and migration state. |
| Phase 2 — scope and gap analysis | Done as a planning activity | Reuse of RBAC, grants, assignments, content lifecycle, delivery, activity, audit, and security-event systems was identified. This status update records the gaps found in the current code. |
| Phase 3 — design and approval gate | Approved for the constrained v1 direction | Existing approvals allow advisory rule-based signals, an evidence-based investigation workflow, and retrieval-only permission-filtered metadata search. They do not approve changing authorization based on risk, adding infrastructure/providers, or claiming a generative assistant. |
| Phase 4 — incremental implementation | In progress | Capability A is implemented as advisory detection. Capability B's API, evidence controls, audit integration, and React workflow are implemented. Capability C's metadata retrieval hardening and React search interface are implemented. |
| Phase 5 — verification and completion | In progress / not complete | Focused and broad PostgreSQL/backend tests (168), frontend tests (19), production build, Django check, migration-drift check, and `git diff --check` pass. Authenticated manual end-to-end verification remains outstanding. |

### Capability A — Context-Aware Content Access Policies

**Status: Implemented as advisory risk signals; formal policy approval and broad acceptance remain incomplete.**

Implemented:

- `backend/knowledge/risk_signals.py` derives a rolling 24-hour `ACCESS_BURST` from at least four granted `ContentAccess` rows across at least three distinct Content IDs, and `REPEATED_DENIALS` from at least three normal `SecurityEvent(ACCESS_DENIED, resource_type="content")` rows for a non-null user.
- Organization-scoped list and summary endpoints require `SECURITY_EVENT_VIEW_ORGANIZATION`. The list validates filter values, timezone-aware inclusive `from`/`to` ranges, positive pagination and the 100-row maximum; it defaults to page 1 and 20 rows. The summary accepts the same detection filters without pagination.
- `frontend/src/App.jsx` adds the permission-gated Risk signals navigation and review page, including date filters, severity/count/window/explanation display, pagination, and explicit advisory-only language.
- Signals remain request-time derived; no RiskSignal table or new event logger was added, and no authorization or grant changes are made.
- Focused tests cover exact/just-below thresholds, same-versus-distinct Content IDs, the 24-hour window, actual denial event path, date boundaries and summary filters, invalid filters/pagination, permissions, competing tenant evidence, and access/grant invariance.

Pending / gaps:

- Thresholds and severities describe existing rule behavior and have not been separately approved as product policy or validated using labeled activity; no real-world detection precision/recall evaluation is claimed.
- This is advisory detection and review, not contextual access-policy enforcement or an access-decision explanation. Risk indicators never grant, deny, suspend, or revoke access.
- The React experience has automated component-level coverage, but no authenticated browser/API manual acceptance run has been recorded yet.

#### Capability A milestone verification — 2026-10-19

Changed files: `backend/knowledge/risk_signals.py`, `backend/accountability/views.py`, `backend/knowledge/tests_risk_and_assistant.py`, `frontend/src/App.jsx`, `frontend/src/App.test.jsx`, and the scope-expansion documentation listed below. No model, migration, dependency, authorization-policy, or new event-logging change was introduced.

- `manage.py test knowledge.tests_risk_and_assistant --verbosity 2` — **8 tests passed** in 19.597 seconds against PostgreSQL's disposable Django test database (`test_aegis`); Django destroyed the test database afterward.
- `npm test -- --run` — **13 tests passed** in 2 test files.
- `npm run build` — passed.
- Django `check` — passed with one silenced check; `makemigrations --check --dry-run` — `No changes detected`.
- Tests verify source selection, thresholds, distinct content, 24-hour boundaries, inclusive date filtering, pagination/filter rejection, permission denial, competing organization evidence, and no access/grant mutation. These are focused tests, not full regression or manual browser acceptance.

### Capability B — Content Exposure Risk Investigation

**Status: Implemented; focused automated verification passed. Authenticated manual acceptance remains pending.**

Implemented:

- Reuses the existing `RiskInvestigation` model and migrations `0010`–`0012`; no new schema or migration was introduced for the investigation hardening/UI changes.
- Organization-scoped list, create, detail, and patch endpoints require `SECURITY_EVENT_VIEW_ORGANIZATION`; list status/severity filters and pagination are validated and bounded (maximum 100 per page).
- Lifecycle transitions are server-validated: `OPEN` → `IN_REVIEW` or `DISMISSED`; `IN_REVIEW` → `RESOLVED` or `DISMISSED`; terminal states have no outgoing transitions.
- Terminal investigations (`RESOLVED` or `DISMISSED`) are now read-only at both the API and UI. All PATCH requests are rejected for terminal cases, including repeated-status and content-only requests. Authorized detail reads remain available.
- Creation and meaningful edits (status, title, summary, severity, notes, and evidence) are atomic with existing `AuditRecord` entries. Audit metadata includes changed-field names and evidence counts, not raw administrative text.
- The bounded evidence contract supports organization-scoped Content denial Security Events and relevant Audit Records. It validates type/UUID, persisted source, tenant, source permission, duplicate references, and maximum size. Detail serialization rechecks current permissions and omits evidence no longer visible; the source remains immutable.
- The React page provides a paginated, filterable list; create/detail/edit forms; authorized denied-event selection; lifecycle transition controls; and loading, empty, success, and API error states. Frontend controls do not replace backend enforcement.
- The UI evidence picker lists up to 100 currently visible Content `ACCESS_DENIED` Security Events; the API supports up to 25 evidence references and also supports relevant Audit Record references for callers with the corresponding permission.

#### Capability B milestone verification — 2026-10-19

Files and modules: `backend/accountability/models.py`, `serializers.py`, `urls.py`, `views.py`, new `evidence.py`, migrations `0010`–`0012` (the existing approved schema/migration work), `backend/knowledge/tests_risk_and_assistant.py`, `frontend/src/App.jsx`, `frontend/src/App.test.jsx`, and the API, data, functional, setup, user-manual, scope-guide, scope-task, and status documents. No dependency or additional schema change was introduced in this milestone.

- `..\venv\Scripts\python.exe manage.py test knowledge.tests_risk_and_assistant` — **17 tests passed** against PostgreSQL's disposable Django test database; Django destroyed the test database. Coverage includes all state combinations, permission failures, audit atomicity/safe metadata, evidence validation and read-time visibility, tenant isolation, list filters/pagination, and retrieval baseline checks.
- `npm test -- --run` — **17 frontend tests passed** in 2 test files, including investigation list filtering/pagination, creation with authorized evidence, detail/edit, status transition, and API validation-error feedback.
- `npm run build` — passed.
- Django's test-runner system check found no issues (one check silenced).
- Authenticated manual/browser acceptance was not run in this milestone. The later full `identity accountability knowledge` regression passed; see final verification below.

Known limitations: evidence detail is a read-time filtered list rather than a chronological joined timeline; the UI selector only presents the first 100 authorized denial events, and direct Audit Record attachment remains API-only. The implementation does not claim a product-approved risk scoring policy or a generative AI investigation summary.

### Capability C — Permission-Aware Enterprise Knowledge Assistant

**Status: Implemented as permission-aware metadata retrieval; not generative RAG. Focused automated verification passed; manual acceptance remains pending.**

Implemented:

- `POST /api/v1/assistant/query/` performs live case-insensitive substring matching on Content `title` and `description`, validates a single string question of 1–200 non-whitespace characters, and returns at most five results. No index, chunk table, vector database, or model call is introduced.
- Requires existing `CONTENT_SEARCH` and `CONTENT_VIEW` permissions. Shared access helpers in `backend/knowledge/access.py` keep consumer Program/assignment/grant eligibility consistent with existing content and Program query behavior.
- Results are restricted to the caller's organization, published Content, and a published current version belonging to that same Content and organization. Content Consumers additionally require an active Program, assignment, and active unexpired grant for the caller. Other roles retain their existing organization-level content visibility.
- `program_names` are derived only from Programs visible through the caller's current Program query scope and assignments for the matched Content; no Program names are emitted without `PROGRAM_VIEW`.
- The response uses fixed retrieval-status wording, returns no citations for insufficient authorized matches, and does not change access, grants, assignments, publication, or version state.
- The React **Knowledge search** page validates query length, submits through the existing session/CSRF-aware API client, displays authorized metadata citations and empty/loading/error states, and explicitly describes the metadata-only/no-generation boundary.

#### Capability C milestone verification — 2026-10-19

Changed files/modules: new `backend/knowledge/access.py`; `backend/knowledge/retrieval.py`; `backend/knowledge/views.py`; `backend/knowledge/tests_risk_and_assistant.py`; `frontend/src/App.jsx`; `frontend/src/App.test.jsx`; and the API, data, functional, setup, user-manual, scope-guide, scope-task, and status documents. No schema migration, dependency, external provider, or infrastructure change was introduced.

- `..\venv\Scripts\python.exe manage.py test knowledge.tests_risk_and_assistant` — **23 tests passed** against PostgreSQL's disposable Django test database; Django destroyed the test database. Coverage includes active/expired/revoked grants, inactive Programs, missing assignments, tenant isolation, unpublished Content, stale/mismatched current versions, missing permissions, Program-name citation filtering, unauthorized same-organization source exclusion, invalid/oversized question bodies, safe empty results, result bounds, and no state mutation.
- `npm test -- --run` — **19 frontend tests passed** in 2 test files, including metadata search citations, fixed retrieval-only wording, blank-query validation, and surfaced API errors.
- `npm run build` — passed.
- Django's test-runner system check found no issues (one check silenced).
- Authenticated manual browser/API acceptance remains pending. The later full `identity accountability knowledge` regression passed; see final verification below.

Known limitations: retrieval is substring matching over metadata only, not semantic document retrieval; no source passage/page citation or generative answer is provided, so model evaluation and AI grounding metrics are not applicable. Metadata relevance has not been evaluated on a labeled query set. Authenticated manual tests remain necessary before final acceptance.

### Scope-expansion regression verification — 2026-10-19

- `..\venv\Scripts\python.exe manage.py test identity accountability knowledge` — **168 tests passed** in 325.977 seconds against PostgreSQL's disposable Django test database; the runner destroyed it afterward. Django's system check found no issues (one check silenced).
- `..\venv\Scripts\python.exe manage.py test knowledge.tests_risk_and_assistant` — **23 focused tests passed** against the PostgreSQL disposable test database.
- `npm test -- --run` — **19 frontend tests passed** in 2 files.
- `npm run build` — passed.
- `..\venv\Scripts\python.exe manage.py check` — passed with one silenced check.
- `..\venv\Scripts\python.exe manage.py makemigrations --check --dry-run` — `No changes detected`.
- `..\venv\Scripts\python.exe manage.py showmigrations accountability` — migrations `0001`–`0012`, including `0010`–`0012`, are applied on the configured persistent database. This inspection was read-only.
- `git diff --check` — passed.
- No persistent database schema/data was changed during the capability B/C continuation. No feature migration or dependency was added.
- Authenticated browser/manual acceptance remains unperformed; the automated suites do not substitute for it.

### Files and modules reviewed for this status

This is a scope-expansion audit, not a claim that every byte of every repository file was line-reviewed. The repository inventory was checked, and scope-relevant sources were traced:

- Rules/design: `Agent/Rules/rules/aegis-development.mdc`; `docs/scope-expansion-implementation-guide.md`; `docs/implementation-guide.md.md`; `docs/prd.md`; `docs/srs.md`; `docs/business-rule.md`; `docs/domain-model.md`; `docs/ard.md`; `docs/system-architecture.md`; `docs/functional-architecture.md`; `docs/data-architecture.md`; `docs/api-specification.md`; `docs/adr/0001-security-event-scope.md`; `docs/adr/0002-authentication-events-and-rate-limits.md`.
- Authorization and evidence: `backend/identity/models.py`, `rbac.py`, `permissions.py`, `views.py`, `knowledge/models.py`, `services.py`, `delivery.py`, and `accountability/models.py` / `services.py`.
- New implementation and tests: accountability models, serializers, views, URLs, evidence resolver and migrations `0010`–`0012`; knowledge `access.py`, `risk_signals.py`, `retrieval.py`, views, URLs, and `tests_risk_and_assistant.py`.
- UI and setup: `frontend/src/App.jsx`, `App.test.jsx`, and `docs/implementation-setup.md`.

The React app now includes `/risk-signals`, `/risk-investigations`, and `/assistant` (Knowledge search).

### Database and migration status

- The configured engine is PostgreSQL; the configured and connected database name is `aegis` at local host `127.0.0.1:5432`, running PostgreSQL 16.15. The Compose service uses the named persistent volume `aegis_aegis_postgres_data`; this is not established as a disposable test database.
- Before reconciliation, read-only inspection confirmed the database had accountability migrations only through `0009`; `0010_riskinvestigation` and `0011_auditrecord_risk_investigation_actions` were unapplied. The `audit_records` table had the pre-enhancement `audit_action_valid` check constraint, and `risk_investigations` did not exist. The migration graph is linear: `0010` depends on `0009`; `0011` depends on `0010`.
- Root cause of `0012_alter_auditrecord_action`: migration `0011` expands the database check constraint to include investigation actions but does not update the migration-state `AuditRecord.action.choices`. The current model includes those four choices; the migration project state after `0011` does not. Django therefore proposes an `AlterField` migration to synchronize choices.
- Expected impact: applying `0010` creates the `risk_investigations` table, its indexes, and status/severity constraints. Applying `0011` replaces the `audit_action_valid` check constraint with the expanded allowed-action list. Neither operation is intended to rewrite existing business rows; the constraint change must still be validated against existing `audit_records` values before applying. A generated `0012` for choices alone should update Django's migration state; `choices` are application metadata and `max_length=100` is unchanged, so no physical column/data change is expected.
- Read-only inspection found 39 audit rows; all observed action values are included in the current model choices. No existing rows use the four new investigation actions. The old database constraint continues to allow the existing values.
- Generated `backend/accountability/migrations/0012_alter_auditrecord_action.py` after reviewing the autodetected operation. It depends on `0011` and only alters the state field choices. `sqlmigrate` for `0012` reports `(no-op)`; it makes no physical schema or data change. Historical migrations were not edited or deleted.
- Created a new custom-format backup at `C:\Users\Princy\.copilot\session-state\8b8c828d-bed8-4d95-9e32-d39aa8ce0552\files\aegis-before-scope-migrations-20261019.dump`. The dump completed successfully (108,032 bytes); `pg_restore --list` parsed it and returned 229 archive entries. SHA-256: `081FD3A5B4826D1C60557E1D47526891AAC9F933BD96CAB49052A191B023F7B4`. It was restored successfully to the separately named disposable database `aegis_restore_rehearsal_20261019`: 39 `audit_records` rows were present, the migration ledger matched the expected state through `0009`, and `risk_investigations` was absent before migration. Keep this data-containing archive protected.
- The prior reported backup `aegis-before-migration-repair-20261009.dump` was not found at the checked repository-root or nearby Desktop locations.
- The database owner confirmed `aegis` as the intended development database and required preserving all existing data. The backup restore rehearsal passed. Migrations `0010`–`0012` were first applied successfully to the disposable restore clone; the audit-row count remained 39, and the investigation table, expanded audit constraint, and migration records were verified. The clone was removed after verification. Following explicit approval, the same three migrations were applied to persistent `aegis`; post-migration checks confirmed 39 audit rows remain, the investigation table and audit constraint exist, and all three migration records are applied.
- `python manage.py check` passed after generating `0012`: no system-check issues (one silenced).
- After applying migrations to `aegis`, `python manage.py showmigrations accountability` reports `0010`, `0011`, and `0012` applied.
- `python manage.py makemigrations accountability` created `0012_alter_auditrecord_action.py`; the operation was reviewed and its SQL is a no-op.
- `python manage.py sqlmigrate accountability 0010` showed only creation of the investigation table, indexes, FKs, and status/severity checks.
- `python manage.py sqlmigrate accountability 0011` showed replacement of the `audit_action_valid` check with the extended allowed-action set.
- `python manage.py sqlmigrate accountability 0012` showed `(no-op)`.
- After generating `0012`, `python manage.py makemigrations --check --dry-run` passed with `No changes detected`; this confirms model/migration-state consistency, not migration application to the database.
- `git diff --check` passed after the migration/status edits.
- Restore rehearsal: `pg_restore --exit-on-error --no-owner --no-privileges` completed successfully against the empty isolated database. Inspection confirmed 39 restored audit records and an accountability migration ledger through `0009`. On that clone, `manage.py migrate accountability --verbosity 2` applied `0010`, `0011`, and `0012` successfully. Post-migration verification confirmed all three migration records, the new table, the expanded check constraint, and the unchanged 39 audit records. The explicitly named clone and its temporary container copy of the dump were removed; no other database was dropped.
- PostgreSQL-focused test: `manage.py test knowledge.tests_risk_and_assistant --verbosity 1` ran 3 tests in 4.725 seconds; all passed. Django created and destroyed its separate PostgreSQL test database. This is focused test evidence, not full-suite acceptance coverage.
- Persistent application: after confirming Django's live connection returned database name `aegis` and receiving explicit user approval, `manage.py migrate accountability --verbosity 2` applied `0010`, `0011`, and `0012` successfully. Post-migration read-only checks confirmed 39 `audit_records`, `risk_investigations` exists, `audit_action_valid` exists, and all three migration rows are recorded.
- Final checks against configured `aegis`: `manage.py check` passed (one silenced check); `manage.py makemigrations --check --dry-run` passed with `No changes detected`; `manage.py showmigrations accountability` reports every migration through `0012` applied; and `git diff --check` passed.
- Migration/recovery gate is resolved. The persistent database change was limited to the reviewed accountability migrations; no reset, flush, recreation, fake migration, or historical migration edit occurred.

### Test and evaluation status

Current focused test file: `backend/knowledge/tests_risk_and_assistant.py` contains **8 tests**.

Executed during the Step 2 reconciliation:

```powershell
cd "C:\Users\Princy\OneDrive\Desktop\Aegis\backend"; & "C:\Users\Princy\OneDrive\Desktop\Aegis\venv\Scripts\python.exe" manage.py check
```

Result: passed; no system-check issues (one silenced).

```powershell
cd "C:\Users\Princy\OneDrive\Desktop\Aegis\backend"; & "C:\Users\Princy\OneDrive\Desktop\Aegis\venv\Scripts\python.exe" manage.py makemigrations --check --dry-run
```

Before generating `0012`, this failed with pending `accountability.0012_alter_auditrecord_action`. After generation, it passed with `No changes detected`; this check does not establish that database migrations are applied.

```powershell
cd "C:\Users\Princy\OneDrive\Desktop\Aegis\backend"; & "C:\Users\Princy\OneDrive\Desktop\Aegis\venv\Scripts\python.exe" manage.py test knowledge.tests_risk_and_assistant --verbosity 1
```

During the migration reconciliation, the focused test ran against PostgreSQL's disposable Django test database: 3 tests ran in 4.725s; OK. During Capability A implementation, the expanded test file ran against PostgreSQL's disposable Django test database: 8 tests ran in 19.597s; OK. Both test databases were destroyed by Django. The focused tests are not full acceptance coverage.

A prior PostgreSQL full-suite run recorded in the preceding session reported 148 tests passing. It was not rerun during this milestone; the focused tests do not establish that the full backend suite or all scope-expansion acceptance criteria pass.

No labeled anomaly dataset or AI model evaluation has been run. There is no generative model in the approved v1, so generative answer metrics are not applicable.

### Documentation status

Updated for accurate current-state descriptions:

- `docs/implementation-status.md` — this status and handoff.
- `docs/implementation-setup.md` — Risk signals, Investigations, and Knowledge search UI/API manual checks and limitations.
- `docs/user-manual.md` — current workflows and boundaries for all three scope-expansion capabilities.
- `docs/api-specification.md` — signal filters, investigation contract, retrieval validation, permissions, and citations.
- `docs/data-architecture.md` — reuse of existing risk/audit records and live permission-filtered retrieval, with no signal, chunk, or index table.
- `docs/functional-architecture.md` — advisory detection, investigation workflow, and metadata retrieval integration.
- `docs/scope-expansion-implementation-guide.md` and `docs/scope-expansion-implementation-task.md` — approved v1 boundaries and verified A/B/C implementation state.

The original PRD/SRS and architecture documents were reviewed as context. Do not update them to claim broader capabilities until the design/scope is finalized and implementation acceptance criteria are met. If requirements are to change, preserve traceability and follow the ADR process.

### Remaining work — recommended order

1. **Complete Capability C as the approved retrieval-only v1.** Filter cited program names to the same currently authorized assignment/grant scope; correct the fixed response wording; add tests for revoked/expired grants, removed assignments, inactive programs, unpublished content, stale current versions, permission failures, invalid input, insufficient sources, and citation/metadata exclusion; deliver and test the metadata-search UI.
3. **Complete manual acceptance.** Run the manual UI/API scenarios in `implementation-setup.md` against approved development data, record exact results, and do not mark blocked or unrun checks as passed. Automated backend/frontend regression and migration checks are recorded above.
4. **Only then decide on out-of-v1 work.** Actual contextual access policies that alter authorization, semantic document retrieval, and generative RAG need a separate design/approval before any policy enforcement, indexing, model, or provider changes. Current approvals do not authorize an AI/risk signal to grant, deny, or revoke access.

### Current handoff

**Next action:** perform authenticated manual UI/API acceptance for A, B, and C using synthetic data in an approved development environment, then record outcomes here. Do not upgrade Capability A to authorization enforcement or Capability C to semantic/generative RAG without separate design approval. The database migration/recovery gate is resolved, migrations `0010`–`0012` are applied to `aegis`, and focused plus broad automated verification passes.

M0/M1 database gates and M2 PostgreSQL integration checks now pass. The approved domain-neutral role name is `Content Consumer`, defined as a user authorized to access and consume organizational content according to assigned permissions and access grants. This is a role of the existing `User`, not a separate user type/entity/table. The agreed high-level access boundary is assigned/authorized content and permitted current versions, searching only that authorized content, secure content delivery without source-file download/sharing, no content mutation/publishing/archiving/version creation/assignment changes absent a separate explicit permission, and tracking significant content interactions. Limited analytics/report access is restricted to the user's own activity and reports for content/programs assigned to them; organization-wide analytics and audit/security-event access are excluded.

M3 baseline decision approved on 2026-10-09: the four system roles and their atomic capability assignments are recorded in the Implementation Guide. This is a new RBAC baseline; there was no runtime Trainer mapping in M2 to preserve. Implemented locally: organization-scoped Role, Permission, UserRole, and RolePermission models; idempotent role seeding and trusted user-role assignment commands; explicit role-management/grant services; deny-by-default DRF permission class; and `/me` effective role/permission output. PostgreSQL verification passed: the RBAC migration applied to `aegis`, Django's system check passed, migration drift check reported no changes, and all 45 identity/accountability tests passed with no PostgreSQL-only skips. The SQLite run (45 tests, 2 PostgreSQL-only tests skipped) remains development evidence only. Content Consumer receives only assigned-resource reporting/analytics capabilities; Management audit access is not assigned until its record scope is defined; no role implies platform-wide administration. Assignment/report query enforcement remains a dependency of the resource-owning milestones. M4 adds the minimal `CONTENT_ARCHIVED` AuditRecord required for content archival; role/permission management APIs remain deferred until M10 records their assignment and permission changes. Legacy `/analytics/trainers` identifiers/examples remain outside the Content Consumer grant until replaced with a properly scoped implementation. The user approved domain-neutral `Program` terminology for M6 and **Program Access Grant** for M7.

## Milestone 4: Content Repository (Implemented; Browser Smoke Pending)

Implemented the tenant-owned `Content` schema and PostgreSQL migration, including organization, title, description, lifecycle status, creator, timestamps, indexes, and a current-version relationship added in M5. Added session-authenticated, permission-checked APIs for create, list, retrieve, metadata update, and archive. List supports pagination, status, and permission-checked text search; organization is taken from the authenticated user, and content is tenant-filtered. M7 now scopes Content Consumer list/detail results using active Program Access Grants and assignments; unknown fields such as client-supplied organization IDs and file payloads are rejected.

Added the minimal `AuditRecord` model to the existing accountability app, matching the established schema and initially allowing only `CONTENT_ARCHIVED`. The archive service locks and tenant-filters the content row, changes its state, and writes the actor-attributed record within one atomic transaction. It rejects repeat archives with `409 INVALID_STATE`; cross-tenant content appears not found. Audit-record failure rolls back the content state change.

Added an injectable `StorageService` with a private local filesystem adapter, internal organization/content/version UUID key generation, streamed SHA-256/size metadata, protected file opening and deletion, collision protection, and no public URL method. Uploads are staged with an 8 MiB memory threshold before private storage, avoiding buffering large approved files entirely in memory. The default root is `backend/private_storage` (ignored by git) and can be configured using `AEGIS_PRIVATE_STORAGE_ROOT`.

PostgreSQL verification: `accountability.0004_auditrecord` applied to `aegis`; Django check and migration-drift check passed; `identity accountability knowledge` passed all 61 tests without skips. The storage-service test module also passed all 6 tests. Tests cover organization scoping, Content Consumer scope/denial, CRUD metadata, search/filter validation, archive authorization and tenant isolation, audit contents, repeat-archive conflict, rollback on audit-insert failure, storage key/metadata, no public URL, traversal rejection, and duplicate-write protection.

M4 implementation is in place. The broader audit history/query features and additional audit actions remain in M10. Authenticated API session/CSRF behavior for content create/update/archive is covered by PostgreSQL integration tests. On 2026-10-11 the frontend browser flow created content and uploaded/published a PDF against a disposable PostgreSQL database.

## Milestone 5: Content Versioning (Implementation Complete; Operational Checks Pending)

Added the tenant-owned `ContentVersion` schema and replaced the temporary nullable `current_version_id` UUID with a nullable relationship to the current version. Versions have per-content numbering, draft/published/archived lifecycle states, creator and publication timestamps, private storage metadata fields, and organization/content identity validation. Published or archived file identity cannot be modified.

Added tenant- and permission-checked version upload/list/detail/publish/archive endpoints. Uploads enforce the approved per-file format/MIME/size allowlist, verify file-content signatures (and the PPTX package structure), calculate the checksum while streaming, and create a private draft with server-generated tenant/content/version storage identity. Failed version-row persistence removes the stored file. Publishing locks the content and version, requires a draft and non-archived content, archives the previous current version, updates the current-version relationship, and records `CONTENT_VERSION_PUBLISHED` atomically. Version archival locks content and version, rejects the current or already archived version with 409, preserves the private file and historical row, and records `CONTENT_VERSION_ARCHIVED` atomically. The new `VERSION_ARCHIVE` capability is granted to Administrator and Content Manager, including organizations already seeded in PostgreSQL.

PostgreSQL verification: all M5 migrations are applied; the combined `identity accountability knowledge knowledge.tests_uploads` suite passed all 93 tests with no skips. Django check, migration-drift check, and `git diff --check` passed. Tests cover the approved per-file limits, MIME/signature checks, session/CSRF behavior, upload permissions and tenant isolation, private storage metadata, storage cleanup after database failure, publication, non-current archiving, current-version conflict, audit rollback, and historical immutability.

The user approved the initial policy: PDF 50 MiB, PPTX 50 MiB, JPG/JPEG/PNG/WEBP 10 MiB, and MP4 250 MiB per file. Template uploads and external-link content remain deferred without removing them from broader product scope. No public file URL or download endpoint was added. API session/CSRF behavior for file upload is covered by PostgreSQL integration tests, and a PDF upload/publish was manually verified in the browser on 2026-10-11 using disposable PostgreSQL/private storage. Deployment-specific request-body and timeout limits must support the approved 250 MiB maximum before production rollout. Those environment-dependent checks remain open and are not represented as passed.

M0 still needs a local `backend/.env` and the clean-worktree/baseline checkpoint criteria.

## Milestone 6: Programs + Content Assignment (Implemented; PostgreSQL Verified)

Added organization-scoped `Program` and `ContentAssignment` models and migration, tenant and duplicate-pair validation, permission-checked program CRUD and activate/deactivate APIs, assignment create/list/remove APIs, and `program_id` content filtering. Deactivation retains existing assignments and rejects new ones; reactivation permits assignments again. Assignment relationships do not grant user access. The approved inactive-Program rule is recorded in the Implementation Guide and API specification.

**SQLite development verification (2026-10-10):** Django system check passed; `makemigrations --check --dry-run` found no model drift; the full `identity accountability knowledge` suite passed 101 tests with 2 PostgreSQL-only tests skipped, including all 8 `knowledge.tests_programs` tests. This is development evidence only, separate from PostgreSQL integration.

**PostgreSQL integration verification (2026-10-10):** Migration `knowledge.0004` applied successfully to `aegis`; Django check and migration-drift check passed; `identity accountability knowledge` passed 101 tests with no skips; and `git diff --check` passed. M6's PostgreSQL gate is complete.

## Milestone 7: Program Access Grants (Implemented; PostgreSQL Verified)

Added tenant-scoped Program Access Grants with active, revoked, and expired states; optional expiry; grant/revoke actor and timestamp history; and a PostgreSQL conditional unique constraint allowing at most one active grant per organization/user/program while retaining multiple historical grants. The approved regrant behavior creates a new row after revocation or expiry. Grant/revoke APIs require their explicit permissions and write audit records transactionally. Access is limited to active Content Consumer users and active Programs; protected content, assignment, and version queries require an unexpired active grant, an assignment, published Content, and the current published version. Program deactivation preserves the grant while denying access; reactivation restores eligibility when all other checks remain valid.

**PostgreSQL integration verification (2026-10-10):** Applied `accountability.0007` and `knowledge.0005` to the configured `aegis` database. The focused `knowledge.tests_access_grants` run passed all 6 tests. After adapting the M6 consumer-view test to provide the now-required grant, `identity accountability knowledge` passed all 107 tests with no skips. Django check and migration-drift check passed. These results are PostgreSQL integration evidence, not SQLite-only checks.

## Milestone 8: Secure Content Delivery (Implemented; Browser Smoke Verified; Operational Checks Pending)

Implemented session-authenticated access creation and rendered delivery. Starting access creates a tenant/user/program/content/version-bound Content Access record only when the user has `SECURE_DELIVERY`, an active unexpired Program Access Grant, an active Program, an assignment, and published Content with its current published version. Each delivery request re-checks the authenticated session, the user-bound access record, grant expiry/revocation, Program state, assignment, and current version; a different user, tenant, revoked grant, inactive Program, removed assignment, or stale version receives not-found.

PDF is rendered one requested page at a time to PNG. JPG/JPEG/PNG/WEBP are normalized to PNG, with metadata excluded from the representation. Raster output is capped at 2400 pixels on the longest edge and image source dimensions are bounded. Original files remain in private storage; responses are inline PNG with `private, no-store` and `nosniff` headers. PPTX and MP4 delivery are deferred and return 415. No short-lived token system, public file URL, or raw source delivery was added. M9 adds the approved dynamic watermark to rendered responses; rendering does not prevent screenshots or saving the rendered representation.

**PostgreSQL integration verification (2026-10-10):** Applied `knowledge.0006`. The focused `knowledge.tests_delivery` suite passed 7 tests, including watermark content and rendered pixel output. The full `identity accountability knowledge` suite passed all 114 tests with no skips; Django system check and migration-drift check passed. Tests exercise rendered PDF pages/images, session/CSRF, access/grant/tenant/program/assignment/version checks, revocation and stale-version denial, page validation, private no-store headers, and deferred formats. At that time, browser smoke was pending; the subsequent 2026-10-11 browser verification is recorded below.

**Browser verification (2026-10-11):** Using a disposable PostgreSQL database and private upload directory, a Content Consumer logged in through the React app, opened a published one-page PDF, and received a rendered 960×640 PNG. The Django server returned 404 for a direct `/media/...` raw-file request. Render and watermark CPU/memory/time limits remain deployment-specific and unverified.

## Milestone 9: Dynamic Watermarking (Implemented; Browser Presence Verified; Legibility Review Pending)

Applied a low-opacity repeated diagonal watermark to every rendered PNG page/image response at delivery time. The original approved fields were masked email, organization name, UTC access timestamp, and content UUID prefix/version number. The 2026-10-15 product decision replaces masked email with the user's display name; if no name exists, delivery displays `Unknown user` rather than email. The watermark is composed on the rendered representation only; private originals are unchanged and there is no permanent watermark table. Unauthorized requests cannot invoke rendering or watermark generation.

M9 adds no schema changes. PostgreSQL delivery tests verify the watermark fields and that output pixels differ from the unwatermarked page; the complete 114-test suite passed on PostgreSQL. Browser legibility and placement remain pending manual viewer smoke testing.

The 2026-10-11 browser screenshot showed the repeated diagonal watermark on the rendered PDF. At the tested viewport it appeared low-contrast; confirm acceptable legibility/placement with product stakeholders before closing this visual review.

## Milestone 10: Activity + Security + Audit (Implemented; PostgreSQL Verified)

Added organization-owned, allowlisted `ActivityEvent` records for successful viewer opens and rendered pages. Delivery writes those events server-side with the user, Content, Content Version, Program, and Content Access context; client event injection is not available. Added read-only, paginated activity, audit, and security-event APIs. Content Consumers are restricted to their own activity, organization activity requires its separate permission, and all list APIs derive tenant scope from the authenticated user. Organization security-event queries exclude platform-level and other-organization rows. Audit records reject instance updates/deletes and have no mutation API.

Expanded audit actions for Program, assignment, Program Access Grant, user-role, and permission changes. RBAC role/permission mutation services now persist their `USER_ROLE_CHANGED` and `PERMISSION_CHANGED` records in the same transaction as the mutation. Existing content, version, Program, assignment, and grant actions remain transactional. Management does not receive audit or security-event permissions by default; no policy broadening was made.

**PostgreSQL integration verification (2026-10-10):** Applied `accountability.0008` to the configured `aegis` database. Focused M10/RBAC/delivery tests passed **25 tests**. Django system check passed, `makemigrations --check --dry-run` found no drift, and `identity accountability knowledge` passed **122 tests with no skips** against PostgreSQL. `git diff --check` passed. These are PostgreSQL results; SQLite results are not substituted. The 2026-10-11 browser verification covered viewer/activity behavior; watermark legibility and deployment resource/time-limit checks remain open from M8/M9, as do M5 upload ingress/timeout checks.

## Milestone 11: Basic Analytics + Reports (Implemented; PostgreSQL Verified)

Added organization-scoped content analytics at `/api/v1/analytics/content/` and a paginated Content Access report at `/api/v1/reports/access/`. Organization-level permissions are tenant-filtered; Content Consumers are limited to their own successful Content Access history for currently assigned resources backed by an active grant, active Program, assignment, published Content, and published current version. Unauthorized access attempts and denied access records do not count as views.

The approved view definition is one successful Content Access record per viewer open. Page-render Activity Events remain usage detail and never increment view counts. Analytics report total views, distinct users with successful access during the selected period, most-viewed Content, daily access frequency, version usage, and recent activity. Session count is represented by the same Content Access records. Average session duration is omitted because no reliable session-end signal exists. Existing M10 Activity, Audit, and Content Version list APIs serve the corresponding User Activity, Audit, and Version History reports.

**PostgreSQL integration verification (2026-10-10):** Focused `knowledge.tests_analytics` passed **7 tests**. No schema changes were required. Django system check passed, `makemigrations --check --dry-run` found no drift, and the full `identity accountability knowledge` suite passed **134 tests with no skips** against PostgreSQL after adding M13/M14 coverage. `git diff --check` passed. This is PostgreSQL evidence, not a SQLite substitute.

**Browser verification (2026-10-11):** On disposable PostgreSQL data, the Content Consumer dashboard and analytics showed one view and one active user, the access report displayed the successful open, and Activity listed the trusted `VIEWER_OPENED` and `VIEWER_PAGE_RENDERED` events.

## Milestone 12: React Frontend (Implemented; Browser/API Smoke Verified)

Added a React/Vite application consuming the existing `/api/v1/` session-authenticated APIs. The API client includes browser credentials, obtains and sends Django CSRF tokens on unsafe requests, refreshes the token after login, preserves pagination metadata, and surfaces API errors. Frontend permission checks only tailor navigation and controls; authorization and tenant isolation remain server-enforced.

Implemented organization login, workspace overview, supported content and version workflows (create, upload draft, publish/archive), Programs and assignments, Program Access Grant create/revoke and lookup, page-by-page protected viewer delivery, read-only Activity/Audit/Security Event lists, analytics, and access reports. Tenant-scoped user list/create/update and read-only role/permission catalogue APIs are available. Role-permission mutation and organization configuration management remain unavailable in the UI; no frontend-only or simulated behavior is added.

Node.js **24.20.0** and npm **11.19.0** are available; dependencies are recorded in `frontend/package-lock.json`. Frontend verification: `npm test` passed **5 tests**; `npm run build` passed; `npm audit` reported **0 vulnerabilities** after upgrading the Vitest test runner to patched version 5.0.3. On 2026-10-11 Vite and Django both returned HTTP 200. Against a freshly migrated disposable PostgreSQL database, the browser verified CSRF-protected login/logout, content creation, PDF draft upload/publication, Program creation/assignment, grant creation, Content Consumer access and rendered delivery, read-only Activity/Audit, analytics, and access report. Browser probes confirmed Content Consumer content creation returns 403, Management content creation and audit reads return 403 while analytics returns 200, and the Django raw-file path returns 404. The existing PostgreSQL end-to-end test separately covers Organization B isolation. Frontend checks and browser smoke do not replace the PostgreSQL integration suite.

## Pending Milestones

- **M5/M8/M9 operational checks:** browser smoke now covers PDF upload/publish and rendered/watermarked delivery. Production 250 MiB ingress/timeouts, viewer resource limits, and acceptable watermark legibility remain unverified.
- **M12 remaining scope:** frontend implementation, automated tests/build/audit, and authenticated disposable-PostgreSQL browser flow are verified. Organization configuration and interactive role-permission management remain unavailable.
- **M13 Security Hardening:** complete the remaining deployment/session configuration review, product-approved audit visibility boundary, and any further role-matrix tests. Automated PostgreSQL tests plus browser probes verified selected cross-tenant, permission, audit, CSRF, and raw-file controls; this is not a production security sign-off.
- **M14 Integration Testing:** backend PostgreSQL end-to-end test covers Organization B isolation, and the equivalent supported workflow was manually exercised through the React browser against disposable PostgreSQL data. Production/manual multi-organization acceptance remains environment-specific.

Content Consumer list/detail, Program, assignment, and version scope now enforces Program Access Grants. Keep Management audit access disabled until its precise record boundary is approved. M5 browser and production ingress/body-size/timeout checks remain environment-dependent.

## Post-M12 UI and Reporting Enhancements (2026-10-15)

The `/access` page now lists all organization-scoped Program Access Grants to authorized access managers, with user and Program names; Content Consumers continue to see only their own grants. Administration now uses Organization users and Roles & Permissions tabs, displays each role's assigned permissions, explains the permission catalogue as a reference list, and opens user creation in a dialog with a multi-select role dropdown. Content creation, Program creation, and Program Access Grant forms also open in dialogs. The protected viewer can expand to a full-window page with Back, Previous, and Next controls. PPTX/MP4 delivery remains deferred and now reports unsupported formats clearly.

Activity, Audit, Security Event, Analytics, and Access Report views show user, Content, and Program display names instead of raw identifiers where available. The dynamic watermark now uses the user's display name instead of email; if no name is configured, it displays `Unknown user`.

**Approved scope decisions:** direct user-to-Content assignment and unarchiving Content are deferred to future development. The MVP retains Program-to-Content assignments, separate Program Access Grants, and its existing one-way Content archive lifecycle.

Verification on 2026-10-15: `npm test` passed 12 frontend tests, `npm run build` passed, and the focused Django identity/accountability/access/analytics/delivery suites passed 37 tests with no skips. Django's system check and `git diff --check` passed.

## Follow-up UI and Policy Review (2026-10-19)

### Completed in this follow-up

- Risk-signal and investigation filter toolbars align their controls at the bottom; both Apply buttons use the primary blue style.
- Investigation creation now opens in the existing modal pattern. The `/risk-investigation` path is also accepted as a frontend alias for the existing `/risk-investigations` page.
- Knowledge search uses a single search-and-results panel, with authorized metadata results displayed in a table. Its retrieval-only behavior and lack of semantic/document search remain unchanged.
- Organization user search and Create User are aligned beside the section heading/description, with responsive wrapping.
- The desktop sidebar keeps the profile and sign-out section pinned at the bottom; only the navigation list scrolls, with its scrollbar visually hidden. Mobile navigation remains horizontal.
- Knowledge search displays its metadata-only limitation directly below the page header as a light-yellow notice with dark text and an exclamation icon. The search input and primary action remain side by side on desktop.
- Login HTTP 429 errors now display generic wait-and-retry guidance. No exact wait duration is shown because the login response does not provide a retry interval.

### Files changed

- `frontend/src/App.jsx`
- `frontend/src/styles.css`
- `frontend/src/App.test.jsx`
- `docs/implementation-setup.md`
- `docs/user-manual.md`
- `docs/implementation-status.md`

### Verification and manual acceptance

- `npm test -- --run` — 23 frontend tests passed across 2 files, including
  assertions for the notice placement, input label association, and sidebar
  navigation/profile ordering.
- `npm run build` — production build passed.
- `git diff --check` — passed.
- Opened the local frontend at `http://127.0.0.1:5173`; it redirected to
  `/login` because no authenticated browser session was available. G13
  privileged-preview acceptance and G14 sidebar scrolling therefore remain
  unverified in the browser. No application content or database rows were
  changed during this attempt.

No backend, schema, migration, permission, or dependency changes were made for these UI updates. No architecture or authorization behavior was changed.

### Verification

- Latest frontend tests and build results are recorded above. The local
  frontend is reachable, but authenticated browser verification remains
  outstanding because no authorized browser session is available.

### Current decisions and outstanding items

- Closed investigations are immutable; later findings require a separate case.
- The privileged-preview design has since been approved and implemented below.
  It remains distinct from consumer grants and assignments.

### Next step

Complete G13 privileged-preview and G14 sidebar acceptance using an
authenticated Administrator or Content Manager session and synthetic content.
The migrations and RBAC seed are already applied on local `aegis`; do not
reapply them. Record the manual outcomes before claiming browser acceptance.

## Investigation Closure Integrity (2026-10-19)

### Decision and implementation

The user selected immutable terminal investigations. The API now rejects all PATCH operations after `RESOLVED` or `DISMISSED`, including title/summary/notes/severity/evidence changes and repeated status values. The React detail view remains readable but disables all fields and removes the save action. New findings can be recorded in a new investigation; a formal link to its predecessor is not currently supported. No migration or dependency was required.

### Files updated for this decision

- `backend/accountability/views.py`
- `backend/knowledge/tests_risk_and_assistant.py`
- `frontend/src/App.jsx`
- `frontend/src/App.test.jsx`
- `docs/business-rule.md` (BR-039)
- `docs/api-specification.md`
- `docs/data-architecture.md`
- `docs/functional-architecture.md`
- `docs/implementation-setup.md`
- `docs/user-manual.md`
- `docs/implementation-status.md`

### Verification

- `..\venv\Scripts\python.exe manage.py test knowledge.tests_risk_and_assistant --verbosity 2` from `backend\`: **24 tests passed** against PostgreSQL disposable test database `test_aegis`, which Django created and destroyed. Coverage includes both terminal states, rejection of status and business-field edits, no mutation/audit side effects, and authorized reads.
- `npm test -- --run` from `frontend\`: **21 tests passed** across 2 files.
- `npm run build` from `frontend\`: passed.
- The frontend system was not authenticated against a running backend for manual browser acceptance.
- No persistent database was modified; no migration, dependency, or preview-authorization change was introduced.

## Privileged Content Preview — Approved Implementation (2026-10-19)

The user approved a separate, audited preview path for Administrator and
Content Manager. It does not reuse `SECURE_DELIVERY` or consumer grant and
assignment authorization. It requires `CONTENT_PREVIEW`, `CONTENT_VIEW`,
`VERSION_VIEW`, an active user, and organization-scoped Content and
ContentVersion in DRAFT or PUBLISHED state; archived resources are rejected.
Each page rechecks the preview-session owner, tenant, permissions, active
account, Content lifecycle, and version relationship. The existing renderer
returns only watermarked PNG pages with a visible `PREVIEW` label.

The implementation reuses `ContentAccess`, `ActivityEvent`, and `AuditRecord`.
`access_context` distinguishes consumer and preview activity; consumer
analytics, reports, and access-burst detection filter out preview records.
Preview does not create or mutate grants or assignments and exposes no source
file or storage URL. The Preview action is shown only with the explicit
permissions. Generative AI and additional infrastructure are not involved.

The accepted decision is recorded in `docs/adr/0011-privileged-content-preview.md`
and indexed in `docs/ard.md`. After the user's explicit authorization, the
backup/restore rehearsal succeeded, all four migrations were applied to
persistent `aegis`, and `seed_rbac` completed for both organizations.
Authenticated browser acceptance remains outstanding.

### Milestone record

**Completed functionality:** Content Manager and Administrator can start a
separate preview for a specific non-archived DRAFT or PUBLISHED version. The
API rechecks organization, session owner, active user, preview/content/version
permissions, Content lifecycle, version lifecycle, and version-to-Content
relationship on each page. The reused renderer returns watermarked PNG pages
only. Preview starts generate audit records; viewer events are marked
`PREVIEW`. The React Content library offers Preview only when the explicit
permissions are present and reuses the protected viewer. Consumer grant and
assignment behavior is unchanged.

**Files/modules changed for this milestone:**

- Backend: `identity/models.py`, `identity/rbac.py`, `identity/tests_rbac.py`;
  `knowledge/models.py`, `serializers.py`, `delivery.py`, `views.py`, `urls.py`,
  `analytics_views.py`, `risk_signals.py`, `tests_delivery.py`,
  `tests_analytics.py`, and `tests_risk_and_assistant.py`; `accountability/models.py`.
- Migrations: `identity/migrations/0004_alter_permission_code.py`,
  `knowledge/migrations/0007_contentaccess_access_context_and_more.py`, and
  `knowledge/migrations/0008_contentaccess_content_preview_without_program.py`,
  `accountability/migrations/0013_remove_auditrecord_audit_action_valid_and_more.py`.
- Frontend: `frontend/src/App.jsx`, `frontend/src/App.test.jsx`.
- Documentation: `docs/prd.md`, `docs/srs.md`, `docs/business-rule.md`,
  `docs/api-specification.md`, `docs/data-architecture.md`,
  `docs/functional-architecture.md`, `docs/ard.md`,
  `docs/adr/0011-privileged-content-preview.md`,
  `docs/implementation-setup.md`, `docs/user-manual.md`, and this status file.
- No dependency, provider, service, vector database, storage infrastructure, or
  other runtime framework was added.

**Migrations and expected impact:** `identity.0004` updates permission choices
in migration state only (`sqlmigrate` reports no SQL). `knowledge.0007` adds
`ContentAccess.access_context`, defaults existing rows to `CONSUMER`, then
removes the database default and adds an allowed-value check. `accountability.0013`
replaces the audit action check to include `CONTENT_PREVIEW_STARTED`; the
column itself is unchanged. `knowledge.0008` adds a check that preview records
cannot reference a Program. No migration deletes or rewrites existing records;
the context column assigns existing access records the `CONSUMER` default.
`seed_rbac` adds the new permission and its standard-role grants for the
existing organizations. Persistent data counts remain unchanged: 2
organizations, 6 users, 44 audit records, 1 risk investigation, 10 Content
Access records, 3 assignments, and 1 Program Access Grant.

**Backup and recovery verification:** A fresh custom-format backup was created
before applying migrations at
`C:\Users\Princy\.copilot\session-state\8b8c828d-bed8-4d95-9e32-d39aa8ce0552\files\aegis-before-privileged-preview-20261019.dump`.
It is 117,476 bytes, `pg_restore --list` parsed 240 archive entries, and its
SHA-256 is
`532ffe4d20966b69a2bce1271c227ab29f5c631749e01ee4adeb1d153585f986`.
The archive was restored successfully to the separately named
`aegis_preview_restore_20261019_8b8c82` database. Before migration, the clone
matched the recorded counts and had migration history through
`accountability.0012`. All four migrations and `seed_rbac` then succeeded on
the clone. Post-seed checks confirmed the same business-data counts, all old
ContentAccess rows defaulted to `CONSUMER`, and the three new constraints
existed. The clone was removed after successful verification; the backup was
retained. Neither backup nor rehearsal modified persistent `aegis`.

**Verification completed:**

- `..\venv\Scripts\python.exe manage.py test knowledge.tests_delivery --verbosity 2`
  — 11 tests passed against disposable PostgreSQL `test_aegis`; Django applied
  the full migration graph and destroyed the test database afterward. Coverage
  includes published/draft previews, archived rejection, organization and
  session binding, active-user checks, missing/revoked permissions,
  `VERSION_VIEW`, CSRF on both consumer and preview starts, audit and activity
  context, watermarking, PNG-only delivery, and unchanged grants/assignments.
- `..\venv\Scripts\python.exe manage.py test identity accountability knowledge --verbosity 1`
  — 174 tests passed in 486.065 seconds against disposable PostgreSQL
  `test_aegis`; Django destroyed the test database afterward.
- `..\venv\Scripts\python.exe manage.py test knowledge.tests_delivery knowledge.tests_analytics knowledge.tests_risk_and_assistant --verbosity 1`
  — 43 tests passed in 174.839 seconds against disposable PostgreSQL after the
  persistent migration/seed operation; Django destroyed the test database.
- `npm test -- --run` — 23 frontend tests passed across two files, including
  permission-gated preview navigation and the protected preview API path.
- `npm run build` — passed.
- `manage.py check` — passed with one silenced check.
- `manage.py makemigrations --check --dry-run` — passed with `No changes
  detected`.
- `manage.py showmigrations identity knowledge accountability` — read-only
  inspection confirms `identity.0004`, `knowledge.0007`–`0008`, and
  `accountability.0013` are applied to persistent `aegis`.
- Post-migration read-only verification confirmed the permission exists,
  `CONTENT_PREVIEW` is granted to Administrator and Content Manager in both
  organizations and not to Content Consumer or Management, Content Manager
  still lacks `SECURE_DELIVERY`, and Content Consumer retains `SECURE_DELIVERY`.
  All 10 existing ContentAccess records are `CONSUMER`; grants, assignments,
  audit rows, and investigation rows retain their pre-migration counts.
- `sqlmigrate` review confirmed that the permission choices operation is a
  no-op; the Knowledge migration adds the access-context column/constraint; and
  `knowledge.0008` enforces that preview records have no Program; the
  Accountability migration replaces its check constraint with the
  preview-enabled allowlist.
- `git diff --check` — passed.

**Security/regression outcome:** consumer delivery still uses its original
grant/assignment/active-program/published-current-version checks. Preview page
requests use a distinct URL and reauthorize their own context. Preview records
are filtered from consumer analytics, reports, and access-burst detection.
Cross-organization content/version access and another user's preview session
are rejected. No source URL or source-file response is returned by the preview
endpoint.

**Limitations and next step:** Authenticated browser/manual acceptance has not
been completed. The migrations and role seed are now applied on persistent
`aegis`; sign in with an authorized Administrator or Content Manager and
synthetic PDF/image content, then perform G13 and G14 in
`implementation-setup.md` and record the browser/API outcome. Do not claim
manual acceptance or production readiness until those checks are complete.
