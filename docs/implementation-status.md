# AEGIS Implementation Status

**Last reviewed:** 2026-10-09  
**Source of truth:** [Implementation Guide](implementation-guide.md.md)

This file records implementation progress and how to test the work that exists. A check passing on SQLite is not evidence that PostgreSQL integration has passed.

## Milestone 0: Development Foundation

### Completed

- Inspected the Django project structure, settings, API routing, requirements, environment template, and Docker Compose configuration.
- Django reads local configuration from `backend/.env`; the example file contains the required variable names without values.
- The Django system check passes in the current environment.

### Not yet verified

- The Docker CLI is installed, but `docker info` reports that Docker Desktop cannot start. The database connection and `migrate` command have not been verified against PostgreSQL.
- The baseline Git checkpoint criterion has not been recorded as complete.
- Node.js/npm and the remaining toolchain checks in the guide have not been recorded as complete.

## Milestone 1: Organization + Custom Identity

### Implemented

- `Organization` has a UUID primary key, name, unique slug, lifecycle status, and timestamps.
- `User` is the configured Django custom user model with a UUID primary key, organization relationship, email, password hash, active/inactive status, names, and timestamps.
- User email uniqueness is scoped to `(organization, email)`, matching the tenant model.
- `AUTH_USER_MODEL` points to `identity.User`.
- A user’s tenant context is available through `user.organization`; no tenant is selected from an arbitrary request parameter.
- The initial identity migration is present at `backend/identity/migrations/0001_initial.py`.

### Tests implemented

The identity tests cover:

- Django resolves `identity.User` as its configured user model.
- Organization and user IDs are UUIDs, and the user belongs to the expected organization.
- Inactive user status is reflected by `is_active`.
- Passwords are stored hashed and can be verified with Django’s password checker.
- The same email can exist in different organizations, and user queries scoped to each organization return only that organization’s user.
- A duplicate email within the same organization is rejected by the database constraint.

**Current result:** the six foundation tests pass within the identity suite using an in-memory SQLite test database. The migration check reports no model/migration drift. PostgreSQL application of the migration and PostgreSQL test execution remain pending; use [Docker-Available Checklist](docker-available-checklist.md) to complete them.

### Important boundary

The identity foundation is distinct from session authentication. Django’s `auth.E003` and `auth.W004` checks are silenced because AEGIS intentionally makes email unique per organization; the configured backend authenticates using organization slug and email together.

## Milestone 2: Authentication + Session Management

### Implemented

- Organization-aware authentication using organization slug, email, and password.
- Generic authentication failures for wrong credentials, unknown organizations, and inactive users.
- `GET /api/v1/auth/csrf/`, `POST /api/v1/auth/login/`, `POST /api/v1/auth/logout/`, and `GET /api/v1/auth/me/`.
- Django session cookies, CSRF protection for unsafe requests, and credentialed development CORS.
- A consistent JSON error envelope for API and CSRF failures.
- `/me` returns identity and organization details; role and permission arrays remain empty until M3.

### Tests implemented

The identity/authentication suite covers model constraints, scoped authentication, login success/failure, inactive users, session creation, `/me`, logout, invalid/expired sessions, request validation, CSRF, rate-limit responses, and authentication event scope. The accountability suite covers event severity constraints, account/IP limits, rolling-window expiry, successful-login counter clearing, and stale-counter cleanup.

**Current result:** all 33 tests pass with an in-memory SQLite test database. `manage.py check` passes and `makemigrations --check --dry-run` reports no migration drift. PostgreSQL verification remains pending.

### Still pending

- Accepted [ADR-0001](adr/0001-security-event-scope.md) and updated the Business Rules, Data Architecture, System Architecture, and API Specification: one Security Event model uses a nullable organization only for platform-scoped events before tenant resolution. Activity event organization ownership remains required.
- Implemented the documented `SecurityEvent` model in `backend/accountability/`, including its initial migration and nullable organization/optional user fields. Model tests cover platform scope without organization/user and tenant scope with a resolved organization.
- [ADR-0002](adr/0002-authentication-events-and-rate-limits.md) defines severity values and authentication-event mappings, plus the account/IP rate-limit policy.
- Authentication success, failure, logout, and rate-limit-trigger events are persisted using the documented scope and severity. Raw account identifiers, IPs, passwords, and session tokens are not stored in counter records.
- Shared account/IP counters use PostgreSQL row locks and hashed keys. SQLite tests do not validate PostgreSQL concurrency behavior.
- `cleanup_auth_rate_limits` removes stale counter rows; production scheduling is environment-specific and not configured in this repository.
- Security-event read authorization tests must be added when the documented security-event monitoring API is implemented; organization users must never see platform-level or other-tenant events.
- M2 is not fully closed, and M3 should not begin yet.
- PostgreSQL migration and test runs remain blocked by Docker Desktop; see [Docker-Available Checklist](docker-available-checklist.md).

**Current result:** Django system check passes, `makemigrations --check --dry-run` reports no changes, and all 33 identity/authentication/security-event/rate-limit tests pass on in-memory SQLite. PostgreSQL verification remains pending.

## How to Test Now (Docker Unavailable)

Run this PowerShell command from the repository root. It temporarily selects an in-memory SQLite database for this process only, then checks Django, checks migration consistency across apps, and runs the identity, authentication, and accountability tests:

```powershell
.\venv\Scripts\python.exe -c "import os,sys; sys.path.insert(0,'backend'); os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); from django.conf import settings; settings.DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':':memory:'}}; import django; django.setup(); from django.core.management import call_command; call_command('check'); call_command('makemigrations','--check','--dry-run'); call_command('test','identity','accountability',verbosity=1)"
```

Expected results include a clean system check, `No changes detected`, and 33 passing tests. This verifies model behavior, API behavior, and migration application on SQLite only; it does not replace PostgreSQL checks or concurrency verification in the Docker checklist.

## Next Implementation Step

After PostgreSQL is available, complete the M0/M1/M2 database and concurrent rate-limit checks in the Docker checklist. Then close M2 and proceed to M3 RBAC. Security-event read-authorization tests belong with the future security-event monitoring API. Do not add authentication or organization-status rules that are not specified in the AEGIS docs.
