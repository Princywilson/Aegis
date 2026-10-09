# Docker-Available Checklist

**Last reviewed:** 2026-10-09  
**Current state:** Docker Desktop and the PostgreSQL 16 Compose service are running. The existing `aegis` database was repaired from a locally stored, restore-tested backup (`aegis-before-migration-repair-20261009.dump`); all current migrations are applied, migration drift is clear, and all 35 PostgreSQL tests pass. Separate worker processes also verified the account/IP rate limits. `backend/.env` is absent; validation used process-local configuration. See [Implementation Status](implementation-status.md) for exact results and the SQLite command.

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

## If a Check Fails

- Check that Docker Desktop is running and `docker compose ps` reports the `db` service as healthy/running.
- Compare `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT` in `backend/.env` with the local Compose configuration. Keep secrets private.
- For Django running directly on Windows, the database host is the forwarded host address (`127.0.0.1`), not the Compose service name `db`.
- Inspect `docker compose logs --tail 100 db` and resolve the connection or migration error before proceeding.
- Before repairing the existing database, inspect and preserve the verified backup. Do not fake or reorder migration records alone; the current schema also differs from the migration state.
- Do not use `docker compose down -v` as routine cleanup; `-v` deletes the persistent development database volume.

## Add Future Docker Checks Incrementally

As each later milestone introduces database-backed behavior, append its specific migration, integration-test, and manual-verification steps here. Keep future items unchecked until that feature exists and its PostgreSQL check is run. After M2 is closed, the next checklist addition should cover M3 RBAC roles, permissions, and authorization tests.
