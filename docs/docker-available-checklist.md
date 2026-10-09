# Docker-Available Checklist

**Last reviewed:** 2026-10-09  
**Current state:** Docker CLI is installed, but `docker info` reports that Docker Desktop cannot start. No PostgreSQL-backed migration or test has been completed. M2 session auth, security events, and rate limiting are implemented and tested on SQLite; PostgreSQL migration and concurrency verification remain pending.

Use this checklist when Docker Desktop is available again. Complete the M0/M1 database gates and verify the existing M2 authentication behavior against PostgreSQL. Do not mark an item complete until its command succeeds.

## M0: Start and Verify PostgreSQL

- [ ] Start Docker Desktop and wait until its engine is ready.
- [ ] From the repository root, verify the Docker engine:

  ```powershell
  docker info
  ```

- [ ] Confirm `backend/.env` exists and its PostgreSQL settings match the local Compose service. Do not print or commit secret values. For the current host-run Django setup, use `127.0.0.1` and port `5432`; the database name and user must match `docker-compose.yml`.
- [ ] Start the database service:

  ```powershell
  docker compose up -d db
  ```

- [ ] Confirm it is running and inspect logs if it is not:

  ```powershell
  docker compose ps
  docker compose logs --tail 50 db
  ```

## M0/M1: Apply and Verify the Database

Run these from the repository root, in order:

- [ ] Check Django configuration:

  ```powershell
  .\venv\Scripts\python.exe backend\manage.py check
  ```

- [ ] Apply Django and AEGIS migrations:

  ```powershell
  .\venv\Scripts\python.exe backend\manage.py migrate
  ```

- [ ] Confirm migrations are applied:

  ```powershell
  .\venv\Scripts\python.exe backend\manage.py showmigrations
  ```

- [ ] Verify model/migration consistency:

  ```powershell
  .\venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run
  ```

- [ ] Run identity tests against PostgreSQL:

  ```powershell
  .\venv\Scripts\python.exe backend\manage.py test identity
  ```

- [ ] Run the full Django test suite:

  ```powershell
  .\venv\Scripts\python.exe backend\manage.py test
  ```

These tests must confirm UUID identifiers, password hashing, inactive-user behavior, configured custom user model, tenant-scoped email uniqueness, and organization-based user queries on PostgreSQL.

## M2: Verify Session Authentication on PostgreSQL

- [ ] Run the complete identity/authentication suite against the configured PostgreSQL database:

  ```powershell
  .\venv\Scripts\python.exe backend\manage.py test identity
  ```

- [ ] Run the accountability model tests against PostgreSQL:

  ```powershell
  .\venv\Scripts\python.exe backend\manage.py test accountability
  ```

- [ ] Confirm session and CSRF migrations are applied by the `migrate` command above.
- [ ] Verify the HTTP session flow manually using a test organization and user:
  - [ ] `GET /api/v1/auth/csrf/` returns a CSRF token and sets the CSRF cookie.
  - [ ] `POST /api/v1/auth/login/` with organization slug, email, password, cookie, and `X-CSRFToken` returns user context and sets the HttpOnly session cookie.
  - [ ] `GET /api/v1/auth/me/` returns the authenticated user and that user's organization.
  - [ ] `POST /api/v1/auth/logout/` with the session and CSRF token ends the session; a subsequent `/me/` returns 401.
  - [ ] Login and logout without a valid CSRF token are rejected; wrong credentials and unknown organizations have the same generic authentication response.
- [ ] Confirm production cookie settings with HTTPS enabled: session cookie is HttpOnly and Secure, and the session timeout is the configured 14 days.
- [ ] Verify successful login, failed login, logout, and rate-limit triggers produce their expected Security Event rows and severities.
- [ ] Verify an unknown organization slug creates a platform-scoped event with null `organization_id`, without assigning it to a default tenant or storing the raw password/session token.
- [ ] Verify resolved-organization authentication events store that organization; keep user null if identity was not resolved.
- [ ] Verify the authentication response remains identical for an invalid password and an unknown organization even though their stored event scope differs.
- [ ] Verify platform-level events are not exposed to organization-level users when the security-event monitoring API is implemented.
- [ ] Confirm `security_events.organization_id` permits null only for platform-scoped events, while `activity_events.organization_id` remains required.
- [ ] Verify five account failures in a rolling 15-minute window trigger a 15-minute account block, and a successful login clears only the account counter.
- [ ] Verify twenty failures from one source IP in a rolling 15-minute window trigger a 15-minute IP block across account identifiers.
- [ ] Verify blocked responses remain generic and arbitrary `X-Forwarded-For` values do not change the source-IP key.
- [ ] Run `python manage.py cleanup_auth_rate_limits` and confirm expired counters are removed while active blocks remain.
- [ ] Verify concurrent requests across separate Django workers cannot exceed the account/IP policy because counter rows are locked transactionally.
- [ ] Configure deployment scheduling for `cleanup_auth_rate_limits` once a scheduler is selected; do not add a process-local counter backend.

## If a Check Fails

- Check that Docker Desktop is running and `docker compose ps` reports the `db` service as healthy/running.
- Compare `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT` in `backend/.env` with the local Compose configuration. Keep secrets private.
- For Django running directly on Windows, the database host is the forwarded host address (`127.0.0.1`), not the Compose service name `db`.
- Inspect `docker compose logs --tail 100 db` and resolve the connection or migration error before proceeding.
- Do not use `docker compose down -v` as routine cleanup; `-v` deletes the persistent development database volume.

## Add Future Docker Checks Incrementally

As each later milestone introduces database-backed behavior, append its specific migration, integration-test, and manual-verification steps here. Keep future items unchecked until that feature exists and its PostgreSQL check is run. After M2 is closed, the next checklist addition should cover M3 RBAC roles, permissions, and authorization tests.
