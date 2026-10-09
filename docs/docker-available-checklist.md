# Docker-Available Checklist

**Last reviewed:** 2026-10-09  
**Current state:** Docker Desktop is unavailable. No PostgreSQL-backed migration or test has been completed.

Use this checklist when Docker Desktop is available again. Complete the existing M0/M1 database gates before implementing the next milestone. Do not mark an item complete until its command succeeds.

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

## If a Check Fails

- Check that Docker Desktop is running and `docker compose ps` reports the `db` service as healthy/running.
- Compare `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT` in `backend/.env` with the local Compose configuration. Keep secrets private.
- For Django running directly on Windows, the database host is the forwarded host address (`127.0.0.1`), not the Compose service name `db`.
- Inspect `docker compose logs --tail 100 db` and resolve the connection or migration error before proceeding.
- Do not use `docker compose down -v` as routine cleanup; `-v` deletes the persistent development database volume.

## Add Future Docker Checks Incrementally

As each later milestone introduces database-backed behavior, append its specific migration, integration-test, and manual-verification steps here. Keep future items unchecked until that feature exists and its PostgreSQL check is run. The next expected addition is the M2 session-authentication integration tests; do not treat those as implemented yet.
