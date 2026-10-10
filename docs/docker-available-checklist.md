# Docker-Available Checklist

**Last reviewed:** 2026-10-11
**Current state:** Docker Engine 29.8.2 and PostgreSQL 16 are available. M3-M10 migrations, including `knowledge.0006` and `accountability.0008`, are applied to the configured `aegis` database. On 2026-10-11, Django check and migration-drift checks passed and `identity accountability knowledge` passed all **134 tests with no skips** against PostgreSQL. A separate disposable PostgreSQL database was migrated from scratch for the React browser flow; it verified session/CSRF login, content upload/publication, Program assignment/grant, protected PDF delivery, accountability, analytics, reporting, and selected authorization failures. React tests/build pass and `npm audit` reports 0 vulnerabilities. PostgreSQL results are distinct from frontend tests; SQLite is development evidence only. The existing `aegis` database repair and restore-tested backup (`aegis-before-migration-repair-20261009.dump`) remain documented. Node.js 24.20.0/npm 11.19.0 are installed. `backend/.env` is absent; credentials must remain private.

Use this checklist to complete remaining database and manual verification. Do not treat SQLite validation as proof that PostgreSQL integration has passed.

## M0: Start and Verify PostgreSQL

- [x] Start Docker Desktop and wait until its engine is ready.
- [x] From the repository root, verify the Docker engine:

  ```powershell
  docker info
  ```

- [ ] Create `backend/.env` from the example and confirm its PostgreSQL settings match the local Compose service. Do not print or commit secret values. For the current host-run Django setup, use `127.0.0.1` and port `5432`; the database name and user must match `docker-compose.yml`.
- [x] Confirm the database service is running:

  ```powershell
  docker compose up -d db
  ```

- [x] Confirm it is running and inspect logs if it is not:

  ```powershell
  docker compose ps
  docker compose logs --tail 50 db
  ```

## M0/M1: Apply and Verify the Database

Run these from the repository root, in order:

- [x] Check Django configuration:

  ```powershell
  .\venv\Scripts\python.exe backend\manage.py check
  ```

- [x] Apply Django and AEGIS migrations to the configured `aegis` database:

  ```powershell
  .\venv\Scripts\python.exe backend\manage.py migrate
  ```

- [x] Confirm migrations are applied on the configured `aegis` database:

  ```powershell
  .\venv\Scripts\python.exe backend\manage.py showmigrations
  ```

- [x] Verify model/migration consistency on the configured PostgreSQL database:

  ```powershell
  .\venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run
  ```

- [x] Run identity tests against the configured PostgreSQL database:

  ```powershell
  .\venv\Scripts\python.exe backend\manage.py test identity
  ```

- [x] Run the full Django test suite against PostgreSQL. From the repository root, specify the app labels so discovery is not limited to the root directory:

  ```powershell
  .\venv\Scripts\python.exe backend\manage.py test identity accountability
  ```

The PostgreSQL run discovered 35 tests and passed against the configured `aegis` database, including the PostgreSQL-only concurrency tests. The historical identity migration record remains in `django_migrations`; the current identity migration is also recorded and the current migration graph is consistent.

## M2: Verify Session Authentication on PostgreSQL

- [x] Run the complete identity/authentication suite against the configured PostgreSQL database:

  ```powershell
  .\venv\Scripts\python.exe backend\manage.py test identity
  ```

- [x] Run the accountability model tests against the configured PostgreSQL database as part of the complete suite:

  ```powershell
  .\venv\Scripts\python.exe backend\manage.py test accountability
  ```

- [x] Confirm session and CSRF migrations are applied by the `migrate` command above.
- [x] Verify the HTTP session flow with PostgreSQL API integration tests:
  - [x] `GET /api/v1/auth/csrf/` returns a CSRF token and sets the CSRF cookie.
  - [x] `POST /api/v1/auth/login/` with organization slug, email, password, cookie, and `X-CSRFToken` returns user context and sets the HttpOnly session cookie.
  - [x] `GET /api/v1/auth/me/` returns the authenticated user and that user's organization.
  - [x] `POST /api/v1/auth/logout/` with the session and CSRF token ends the session; a subsequent `/me/` returns 401.
  - [x] Login and logout without a valid CSRF token are rejected; wrong credentials and unknown organizations have the same generic authentication response.
- [x] Confirm production cookie settings with HTTPS enabled: session cookie is HttpOnly and Secure, and the session timeout is the configured 14 days.
- [x] Verify successful login, failed login, logout, and rate-limit triggers produce their expected Security Event rows and severities.
- [x] Verify an unknown organization slug creates a platform-scoped event with null `organization_id`, without assigning it to a default tenant or storing the raw password/session token.
- [x] Verify resolved-organization authentication events store that organization; keep user null if identity was not resolved.
- [x] Verify the authentication response remains identical for an invalid password and an unknown organization even though their stored event scope differs.
- [x] Verify platform-level events are not exposed to organization-level users through the M10 security-event API; its queryset is restricted to the authenticated organization.
- [x] Confirm `security_events.organization_id` permits null for platform-scoped events while `activity_events.organization_id` remains required.
- [x] Verify five account failures in a rolling 15-minute window trigger a 15-minute account block, and a successful login clears only the account counter.
- [x] Verify twenty failures from one source IP in a rolling 15-minute window trigger a 15-minute IP block across account identifiers.
- [x] Verify blocked responses remain generic and arbitrary `X-Forwarded-For` values do not change the source-IP key.
- [x] Run `python manage.py cleanup_auth_rate_limits` and confirm expired counters are removed while active blocks remain.
- [x] Verify concurrent account and source-IP failures cannot exceed their thresholds using PostgreSQL transactions on independent database connections and separate worker processes.
- [ ] Configure deployment scheduling for `cleanup_auth_rate_limits` once a scheduler is selected; do not add a process-local counter backend.

## M3: RBAC (PostgreSQL Verification Passed)

The M3 role boundary was approved and recorded in the Implementation Guide on 2026-10-09. RBAC models, services, commands, `/me` output, and automated tests are implemented. The migration and full relevant suite passed on PostgreSQL. Management audit access remains unassigned pending a more precise audit-record scope. M7 now enforces Content Consumer resource-level filtering through active Program Access Grants, assignments, and published current versions.

- [x] Approve the initial role capability boundaries for Administrator, Content Manager, Content Consumer, and Management; do not use Django Groups as the AEGIS role model.
- [x] Define the atomic permission catalogue and seeded role-permission mapping; identity tests exercise the mapping on SQLite.
- [x] Implement tenant-scoped role assignment and role-permission services, including cross-organization rejection tests on SQLite and PostgreSQL.
- [x] Ensure Content Consumer content/version/program reads require assigned/authorized scope; do not grant content mutation, publishing, archiving, version creation, assignment, or access-grant management.
- [x] Scope Content Consumer activity to the user's own records; reports/analytics still require M11 assigned-resource scope. Do not grant audit or security-event access.
- [x] Implement reusable server-side permission checks and a deny-by-default DRF permission class, wired to the implemented content/program operations.
- [x] Re-run the full authorization suite against PostgreSQL, including allow/deny behavior, inactive users, and tenant isolation: 45 tests passed, no skips.
- [x] Verify role mappings, allow/deny behavior, inactive-user handling, tenant-scoped assignment, and Management audit/security-event denials on SQLite (45 total suite tests; 2 PostgreSQL-only tests skipped). This is development evidence only, not PostgreSQL verification.
- [x] Apply RBAC migrations on PostgreSQL, run migration-drift checks, and execute the complete relevant PostgreSQL test suite (45 tests passed; no skips; no migration drift).
- [x] Verify `/api/v1/auth/me/` returns the assigned role and effective permissions without cross-tenant roles on SQLite and PostgreSQL.
- [x] Keep Management audit access denied until its audit-record scope is explicitly approved; security events remain a separate capability.
- [x] Record role assignment/removal and permission grant/revocation in transactional audit writes before exposing role-management endpoints; those management endpoints remain unimplemented.

## M4: Content Repository (Implemented; Browser Smoke Pending)

- [x] Add the organization-owned Content model and apply its migration to PostgreSQL.
- [x] Add create, list, retrieve, and metadata-update APIs with server-side AEGIS permission checks.
- [x] Enforce organization filtering; cross-tenant content is not listed or retrievable.
- [x] Enforce Content Consumer-only list/detail results through M7's active-grant, assignment, and published-current-version filter.
- [x] Validate pagination, status/search filters, and search permission; reject unsupported `program_id` until M6.
- [x] Reject unknown fields, including client-supplied tenant IDs and file data, instead of silently accepting them.
- [x] Add the minimal organization-scoped AuditRecord prerequisite and CONTENT_ARCHIVED event for archive, with actor/resource/timestamp and old/new status values.
- [x] Verify the archive state change and AuditRecord commit atomically, including rollback on audit persistence failure; repeated archive returns 409 INVALID_STATE.
- [x] Expose archive only with CONTENT_ARCHIVE and verify cross-organization 404 and permission-denied behavior.
- [x] Run `identity accountability knowledge` against PostgreSQL: 61 tests passed, no skips; Django check and migration-drift check passed.
- [x] Verify authenticated API session/CSRF behavior for content create/update/archive in PostgreSQL integration tests.
- [x] In the React browser on 2026-10-11, create content and upload/publish a small PDF against disposable PostgreSQL/private storage.
- [ ] Verify production ingress/body-size and request timeout settings support the 250 MiB per-file policy.
- [x] Implement an injectable private storage abstraction with tenant/content/version UUID keys, streamed size/checksum metadata, protected open/delete methods, duplicate-write protection, and no public URL. The configured local private root is not exposed by static/media routes.
- [x] Integrate private file upload and stored metadata with Content Version in M5; no public file URL or unprotected download endpoint is allowed.
- [x] Replace the temporary nullable `current_version_id` UUID reference with the proper Content Version relationship in M5.
- [x] Add assignment- and grant-backed Content Consumer list/detail filtering; test tenant isolation, inactive Programs, revoked/expired grants, and current published versions in M7.

## M5: Content Versioning (Implementation Complete; Operational Checks Pending)

- [x] Add ContentVersion with tenant/content ownership, version numbering, lifecycle state, creator, and private storage metadata fields.
- [x] Apply the Content Version migration to PostgreSQL and preserve the existing current-version database column while replacing its UUID field with a foreign key.
- [x] Add tenant- and permission-checked version list/detail and publish APIs; publish the selected draft atomically, archive the prior current version, and record `CONTENT_VERSION_PUBLISHED`.
- [x] Add the documented Content Version archive endpoint; reject current/already archived versions with 409, audit atomically, and preserve historical metadata/files.
- [x] Apply the version notes, archive-audit, and `VERSION_ARCHIVE` permission migrations to PostgreSQL; grant archive permission to existing Administrator and Content Manager roles.
- [x] Enforce the approved per-file allowlist: PDF 50 MiB, PPTX 50 MiB, JPG/JPEG/PNG/WEBP 10 MiB, and MP4 250 MiB. Verify declared MIME and content signature; templates and external links are deferred.
- [x] Integrate multipart upload with private storage, streamed size/checksum calculation, generated tenant/content/version keys, and cleanup if the version row cannot be saved.
- [x] Test version identity/numbering, authorization, tenant isolation, file validation/limits, private metadata, upload rollback cleanup, publication, archival, audit rollback, and lifecycle transitions.
- [x] Run `identity accountability knowledge knowledge.tests_uploads` against PostgreSQL: 93 tests passed, no skips; Django check, migration-drift check, and `git diff --check` passed.
- [ ] Verify production ingress/body-size and request timeout settings support the 250 MiB per-file policy.
- [x] Verify authenticated API session/CSRF behavior for content create/update/archive and version upload in PostgreSQL integration tests.
- [x] Perform a browser smoke test for content create, PDF version upload, and publication through React on disposable PostgreSQL (2026-10-11).

## M6: Programs + Content Assignment (Implemented; PostgreSQL Verified)

- [x] Add tenant-scoped Program and ContentAssignment models, uniqueness/tenant validation, and permission-checked CRUD, activate/deactivate, assignment, and content-filter APIs.
- [x] Preserve assignments when deactivating a Program; reject new assignments while inactive; reactivation restores assignment eligibility. Assignment does not grant user access.
- [x] Run SQLite development checks: `identity accountability knowledge` passed 101 tests with 2 PostgreSQL-only skips; Django system check and migration-drift check passed. This is not PostgreSQL integration evidence.
- [x] Start Docker/PostgreSQL and apply `knowledge.0004` to the configured PostgreSQL database.
- [x] Run Django system check and `makemigrations --check --dry-run`; run `identity accountability knowledge` against PostgreSQL: 101 tests passed, no skips.
- [x] Record PostgreSQL evidence separately from the SQLite development run in the implementation status.

## M7: Program Access Grants (Implemented; PostgreSQL Verified)

- [x] Add tenant-scoped grant lifecycle with active, revoked, and expired states; optional future expiry; and actor/timestamp history.
- [x] Preserve revoked/expired history and allow regrant by creating a new row; enforce at most one active grant per organization/user/program.
- [x] Require explicit `ACCESS_GRANT` / `ACCESS_REVOKE` permissions and append grant/revoke audit records in the same transaction.
- [x] Enforce Content Consumer access only for active grants on active Programs, assigned published Content, and its current published version; preserve grants during Program deactivation.
- [x] Apply `accountability.0007` and `knowledge.0005` to PostgreSQL `aegis`.
- [x] Run `knowledge.tests_access_grants` against PostgreSQL: 6 tests passed.
- [x] Run `identity accountability knowledge` against PostgreSQL: 107 tests passed, no skips; Django check and migration-drift check passed.
- [x] Use the approved render-based delivery policy: PDF pages and normalized JPG/JPEG/PNG/WEBP images render to private inline PNG; PPTX/MP4 are deferred.
- [x] Revalidate session, access record, grant, Program, assignment, and published current version on every page/image request; do not add a bearer token.
- [x] Apply `knowledge.0006` for version-specific Content Access records; keep original files private and set rendered responses to `private, no-store`.
- [x] Run `knowledge.tests_delivery` against PostgreSQL: 7 tests passed, including tenant/user scope, CSRF, revoked/inactive/stale access denial, page validation, rendering, and unsupported formats.
- [x] Run `identity accountability knowledge` against PostgreSQL: 114 tests passed, no skips; Django check and migration-drift check passed.
- [x] On 2026-10-11, use the React browser to open the assigned published PDF and verify rendered PNG delivery against disposable PostgreSQL.
- [ ] Confirm production render CPU/memory and request-timeout settings for page rendering.

## M9: Dynamic Watermarking (Browser Presence Verified; Legibility Review Pending)

- [x] Apply the approved masked email, organization name, UTC access timestamp, and content/version reference to each rendered page/image.
- [x] Compose a low-opacity repeated diagonal watermark on the response only; leave private originals unchanged and add no watermark table.
- [x] Verify rendered output contains the approved watermark content and differs from the unwatermarked output in PostgreSQL tests.
- [x] Verify the repeated diagonal watermark is present in the rendered browser preview.
- [ ] Obtain product confirmation of watermark legibility/placement; it appeared low-contrast at the tested viewport.

## M10: Activity + Security + Audit (Implemented; PostgreSQL Verified)

- [x] Add the organization-owned ActivityEvent table with tenant/context validation and allowlisted viewer-open/page-render event types.
- [x] Generate viewer activity and access-denial security events only from trusted backend workflows; do not expose a client activity-ingestion endpoint.
- [x] Add read-only, paginated activity, audit, and security-event list APIs with permission and tenant scoping.
- [x] Limit Content Consumer activity to the current user's events; verify organization activity permission and cross-tenant exclusion.
- [x] Exclude null-organization platform events from organization security-event results.
- [x] Make AuditRecord instance updates/deletes fail and provide no audit mutation API.
- [x] Audit user-role assignment/removal and role-permission grant/revocation transactionally; verify rollback when audit persistence fails.
- [x] Apply `accountability.0008` to PostgreSQL database `aegis`.
- [x] Run focused M10/RBAC/delivery tests on PostgreSQL: 25 tests passed.
- [x] Run Django system check and `makemigrations --check --dry-run`; run `identity accountability knowledge`: 122 tests passed, no skips.
- [x] Run `git diff --check`.
- [ ] Add an explicitly approved audit-record visibility boundary before granting Management the audit permission.
- [x] Verify viewer and trusted Activity events through the React browser on disposable PostgreSQL (2026-10-11); visual watermark review remains tracked under M9.

## M11: Basic Analytics + Reports (Implemented; PostgreSQL Verified)

- [x] Define one content view as one successful Content Access record; do not count page-render events as additional views.
- [x] Add organization-scoped content aggregates for total views, active users, most-viewed content, daily access frequency, version usage, and recent activity.
- [x] Add a paginated Content Access report without exposing email addresses or private storage details.
- [x] Limit Content Consumer analytics/report access to their own successful access history for currently assigned/authorized resources; verify organization and cross-tenant scope.
- [x] Exclude denied access records from view and report totals.
- [x] Omit average session duration because the system has no reliable session-end event.
- [x] Run `knowledge.tests_analytics` against PostgreSQL: 7 tests passed.
- [x] Run Django system check and `makemigrations --check --dry-run`; run `identity accountability knowledge`: 129 tests passed, no skips.
- [x] Run `git diff --check`.
- [x] On 2026-10-11, verify the Consumer dashboard/analytics show one successful view, the access report includes it, and Activity shows viewer-open/page-render events.

## M12: React Frontend (Implemented; Authenticated Browser Test Pending)

- [x] Install Node.js/npm and add the React/Vite package manifest and lockfile.
- [x] Implement the session/CSRF-aware API client and login/logout experience.
- [x] Implement supported Content, Program/Assignment, Program Access Grant, secure viewer, Activity/Audit/Security Event, analytics, and access-report screens.
- [x] Make navigation/controls permission-aware while keeping all authorization and tenant decisions on the backend.
- [x] Surface unavailable user/role/organization-management APIs rather than simulating those operations.
- [x] Run `npm test` (5 frontend tests) and `npm run build`.
- [x] Run `npm audit`; report 0 vulnerabilities after upgrading Vitest to 5.0.3.
- [x] Start Vite and verify its root responds with HTTP 200 and renders the login page.
- [x] Against a fresh disposable PostgreSQL database, verify browser login/logout, CSRF, content create, PDF upload/publish, Program create/assignment, grant, Consumer viewer delivery, Activity/Audit, analytics, and access report.
- [x] Verify Content Consumer content creation and audit reads return 403; Management content creation and audit reads return 403 while analytics reads return 200.
- [x] Verify the Django raw-file media URL returns 404; the Vite development server's SPA fallback is not treated as a file response.
- [x] Complete the supported M5/M8/M9 browser smoke steps; upload-size/production limits and watermark visual approval remain separate pending checks.
- [ ] Add User/Role/Organization configuration management after the corresponding backend APIs and authorization/audit workflows exist.

## M13: Security Hardening (Backend Checks Added; Full Pass Pending)

- [x] Reject arbitrary `organization_id` and unknown query filters on accountability APIs.
- [x] Reject naive date-time filters; dates must carry an explicit timezone.
- [x] Deny client-created activity and security events.
- [x] Reject AuditRecord instance and queryset update/delete attempts.
- [x] Verify Content Consumer cannot read audit records and organization security events cannot expose platform/other-tenant records.
- [x] Run focused PostgreSQL accountability hardening checks: 17 tests passed across `accountability.tests_hardening`, `accountability.tests_m10`, and `knowledge.tests_analytics`.
- [x] Run `npm audit` for the React frontend dependency tree: 0 vulnerabilities.
- [x] Rerun the full PostgreSQL suite after M12: 134 tests passed with no skips; Django check and migration-drift check passed.
- [x] Manually verify Consumer content-create/audit-read denial, Management content-create/audit-read denial and analytics access, and direct Django raw-file denial (404) in the browser flow.
- [x] Verify Organization B content/program/access/report isolation in the PostgreSQL end-to-end scenario.
- [ ] Complete production session/CSRF/CSP/ingress/timeout review and any additional manual role-matrix checks; this browser/development evidence is not production sign-off.

## M14: Integration Testing (Backend and Browser Flows Verified)

- [x] Run a PostgreSQL session/CSRF API scenario covering content creation, version upload/publication, Program creation/assignment, grant, viewer access/delivery, activity/audit, analytics, and report behavior.
- [x] Repeat cross-tenant resource/access attempts with Organization B and verify tenant isolation.
- [x] Integrate and manually verify the supported content-to-report workflow through React against a disposable PostgreSQL database, including real session/CSRF login and rendered protected viewer.

## If a Check Fails

- Check that Docker Desktop is running and `docker compose ps` reports the `db` service as healthy/running.
- Compare `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT` in `backend/.env` with the local Compose configuration. Keep secrets private.
- For Django running directly on Windows, the database host is the forwarded host address (`127.0.0.1`), not the Compose service name `db`.
- Inspect `docker compose logs --tail 100 db` and resolve the connection or migration error before proceeding.
- Before repairing the existing database, inspect and preserve the verified backup. Do not fake or reorder migration records alone; the current schema also differs from the migration state.
- Do not use `docker compose down -v` as routine cleanup; `-v` deletes the persistent development database volume.

## Add Future Docker Checks Incrementally

As each later milestone introduces database-backed behavior, append its specific migration, integration-test, and manual-verification steps here. Keep future items unchecked until that feature exists and its PostgreSQL check is run.
