# AEGIS Implementation Status

**Last reviewed:** 2026-10-11
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

## Current Progress and Next Step

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

Applied a low-opacity repeated diagonal watermark to every rendered PNG page/image response at delivery time. The approved fields are masked email (first local-part character plus `***`, with domain retained), organization name, UTC access timestamp, and content UUID prefix/version number. The watermark is composed on the rendered representation only; private originals are unchanged and there is no permanent watermark table. Unauthorized requests cannot invoke rendering or watermark generation.

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

Implemented organization login, workspace overview, supported content and version workflows (create, upload draft, publish/archive), Programs and assignments, Program Access Grant create/revoke and lookup by user UUID, page-by-page protected viewer delivery, read-only Activity/Audit/Security Event lists, analytics, and access reports. The Administration page explicitly reports that user/role/organization-management APIs are not currently available; no frontend-only or simulated management behavior was added.

Node.js **24.20.0** and npm **11.19.0** are available; dependencies are recorded in `frontend/package-lock.json`. Frontend verification: `npm test` passed **5 tests**; `npm run build` passed; `npm audit` reported **0 vulnerabilities** after upgrading the Vitest test runner to patched version 5.0.3. On 2026-10-11 Vite and Django both returned HTTP 200. Against a freshly migrated disposable PostgreSQL database, the browser verified CSRF-protected login/logout, content creation, PDF draft upload/publication, Program creation/assignment, grant creation, Content Consumer access and rendered delivery, read-only Activity/Audit, analytics, and access report. Browser probes confirmed Content Consumer content creation returns 403, Management content creation and audit reads return 403 while analytics returns 200, and the Django raw-file path returns 404. The existing PostgreSQL end-to-end test separately covers Organization B isolation. Frontend checks and browser smoke do not replace the PostgreSQL integration suite.

## Pending Milestones

- **M5/M8/M9 operational checks:** browser smoke now covers PDF upload/publish and rendered/watermarked delivery. Production 250 MiB ingress/timeouts, viewer resource limits, and acceptable watermark legibility remain unverified.
- **M12 remaining scope:** frontend implementation, automated tests/build/audit, and authenticated disposable-PostgreSQL browser flow are verified. User, role, and organization configuration management still awaits the corresponding backend APIs.
- **M13 Security Hardening:** complete the remaining deployment/session configuration review, product-approved audit visibility boundary, and any further role-matrix tests. Automated PostgreSQL tests plus browser probes verified selected cross-tenant, permission, audit, CSRF, and raw-file controls; this is not a production security sign-off.
- **M14 Integration Testing:** backend PostgreSQL end-to-end test covers Organization B isolation, and the equivalent supported workflow was manually exercised through the React browser against disposable PostgreSQL data. Production/manual multi-organization acceptance remains environment-specific.

Content Consumer list/detail, Program, assignment, and version scope now enforces Program Access Grants. Keep Management audit access disabled until its precise record boundary is approved. M5 browser and production ingress/body-size/timeout checks remain environment-dependent.
