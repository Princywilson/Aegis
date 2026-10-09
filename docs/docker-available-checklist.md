# Docker-Available Checklist

**Last reviewed:** 2026-10-09  
**Current state:** Docker Engine 29.8.2 and the PostgreSQL 16 Compose service are available. M3's RBAC migration and M4's Content and minimal AuditRecord migrations are applied to the configured `aegis` database. Django checks and migration-drift checks passed; the combined identity/accountability/knowledge suite passed all 61 tests with no skips. The existing `aegis` database repair and restore-tested backup (`aegis-before-migration-repair-20261009.dump`) remain documented. `backend/.env` is absent; this verification used process-local configuration, and credentials must remain private.

Use this checklist to complete the remaining database and manual verification. Do not treat validation on the isolated database as proof that the existing `aegis` database can be migrated.

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
- [ ] Verify platform-level events are not exposed to organization-level users when the security-event monitoring API is implemented.
- [ ] Confirm `security_events.organization_id` permits null only for platform-scoped events, while `activity_events.organization_id` remains required. Activity events are not implemented yet.
- [x] Verify five account failures in a rolling 15-minute window trigger a 15-minute account block, and a successful login clears only the account counter.
- [x] Verify twenty failures from one source IP in a rolling 15-minute window trigger a 15-minute IP block across account identifiers.
- [x] Verify blocked responses remain generic and arbitrary `X-Forwarded-For` values do not change the source-IP key.
- [x] Run `python manage.py cleanup_auth_rate_limits` and confirm expired counters are removed while active blocks remain.
- [x] Verify concurrent account and source-IP failures cannot exceed their thresholds using PostgreSQL transactions on independent database connections and separate worker processes.
- [ ] Configure deployment scheduling for `cleanup_auth_rate_limits` once a scheduler is selected; do not add a process-local counter backend.

## M3: RBAC (PostgreSQL Verification Passed)

The M3 role boundary was approved and recorded in the Implementation Guide on 2026-10-09. RBAC models, services, commands, `/me` output, and automated tests are implemented. The migration and full relevant suite passed on PostgreSQL. Management audit access remains unassigned pending a more precise audit-record scope. Content Consumer resource-level assignment filtering is still to be implemented with the assignment/access models.

- [x] Approve the initial role capability boundaries for Administrator, Content Manager, Content Consumer, and Management; do not use Django Groups as the AEGIS role model.
- [x] Define the atomic permission catalogue and seeded role-permission mapping; identity tests exercise the mapping on SQLite.
- [x] Implement tenant-scoped role assignment and role-permission services, including cross-organization rejection tests on SQLite and PostgreSQL.
- [ ] Ensure Content Consumer content/version/program reads require assigned/authorized scope; do not grant content mutation, publishing, archiving, version creation, assignment, or access-grant management.
- [ ] Scope Content Consumer activity to the user's own records and reports/analytics to content/programs assigned to that user; do not grant audit or security-event access.
- [x] Implement reusable server-side permission checks and a deny-by-default DRF permission class. No content/program operation endpoints exist yet to wire.
- [x] Re-run the full authorization suite against PostgreSQL, including allow/deny behavior, inactive users, and tenant isolation: 45 tests passed, no skips.
- [x] Verify role mappings, allow/deny behavior, inactive-user handling, tenant-scoped assignment, and Management audit/security-event denials on SQLite (45 total suite tests; 2 PostgreSQL-only tests skipped). This is development evidence only, not PostgreSQL verification.
- [x] Apply RBAC migrations on PostgreSQL, run migration-drift checks, and execute the complete relevant PostgreSQL test suite (45 tests passed; no skips; no migration drift).
- [x] Verify `/api/v1/auth/me/` returns the assigned role and effective permissions without cross-tenant roles on SQLite and PostgreSQL.
- [x] Keep Management audit access denied until its audit-record scope is explicitly approved; security events remain a separate capability.
- [x] Keep role/permission management APIs unavailable until M10 AuditRecord support can record assignments and permission changes.

## M4: Content Repository (In Progress)

- [x] Add the organization-owned Content model and apply its migration to PostgreSQL.
- [x] Add create, list, retrieve, and metadata-update APIs with server-side AEGIS permission checks.
- [x] Enforce organization filtering; cross-tenant content is not listed or retrievable.
- [x] Keep Content Consumer-only list/detail results empty until assignment/access records support an authorized-resource filter.
- [x] Validate pagination, status/search filters, and search permission; reject unsupported `program_id` until M6.
- [x] Reject unknown fields, including client-supplied tenant IDs and file data, instead of silently accepting them.
- [x] Add the minimal organization-scoped AuditRecord prerequisite and CONTENT_ARCHIVED event for archive, with actor/resource/timestamp and old/new status values.
- [x] Verify the archive state change and AuditRecord commit atomically, including rollback on audit persistence failure; repeated archive returns 409 INVALID_STATE.
- [x] Expose archive only with CONTENT_ARCHIVE and verify cross-organization 404 and permission-denied behavior.
- [x] Run `identity accountability knowledge` against PostgreSQL: 61 tests passed, no skips; Django check and migration-drift check passed.
- [ ] Manually verify content create/update/archive through an authenticated session and CSRF-protected requests against the running development API.
- [ ] Implement the guide's storage abstraction and private-file workflow with Content Versioning; no public file URL or unprotected download endpoint is allowed.
- [ ] Replace the temporary nullable `current_version_id` UUID reference with the proper Content Version relationship in M5.
- [ ] Add assignment-backed Content Consumer list/detail filtering when assignment/access models are implemented.

## If a Check Fails

- Check that Docker Desktop is running and `docker compose ps` reports the `db` service as healthy/running.
- Compare `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT` in `backend/.env` with the local Compose configuration. Keep secrets private.
- For Django running directly on Windows, the database host is the forwarded host address (`127.0.0.1`), not the Compose service name `db`.
- Inspect `docker compose logs --tail 100 db` and resolve the connection or migration error before proceeding.
- Before repairing the existing database, inspect and preserve the verified backup. Do not fake or reorder migration records alone; the current schema also differs from the migration state.
- Do not use `docker compose down -v` as routine cleanup; `-v` deletes the persistent development database volume.

## Add Future Docker Checks Incrementally

As each later milestone introduces database-backed behavior, append its specific migration, integration-test, and manual-verification steps here. Keep future items unchecked until that feature exists and its PostgreSQL check is run.
