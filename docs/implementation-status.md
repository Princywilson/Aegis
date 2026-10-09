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

- Docker Desktop/PostgreSQL is unavailable, so the database connection and `migrate` command have not been verified against PostgreSQL.
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

**Current result:** all six identity tests pass with an in-memory SQLite test database. The migration check reports no model/migration drift. PostgreSQL application of the migration and PostgreSQL test execution remain pending; use [Docker-Available Checklist](docker-available-checklist.md) to complete them.

### Important boundary

The identity foundation is not the M2 authentication workflow. Login, logout, `/me`, an organization-aware authentication flow, session/CSRF integration tests, and login security-event recording are not implemented yet. Django’s global `auth.E003` check is silenced because AEGIS intentionally makes email unique per organization rather than globally; M2 must authenticate using both organization and email.

## How to Test Now (Docker Unavailable)

Run this PowerShell command from the repository root. It temporarily selects an in-memory SQLite database for this process only, then checks Django, checks migration consistency, and runs the identity tests:

```powershell
.\venv\Scripts\python.exe -c "import os,sys; sys.path.insert(0,'backend'); os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); from django.conf import settings; settings.DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':':memory:'}}; import django; django.setup(); from django.core.management import call_command; call_command('check'); call_command('makemigrations','identity','--check','--dry-run'); call_command('test','identity',verbosity=1)"
```

Expected results include a clean system check, `No changes detected in app 'identity'`, and six passing tests. This verifies model behavior and migration application on SQLite only; it does not replace the PostgreSQL checks in the Docker checklist.

## Next Implementation Step

After the Docker-backed M0/M1 checks pass, begin M2 from the implementation guide: organization-aware session login, logout, and current-user endpoints. Use the organization slug and email together when authenticating; global email lookup is incompatible with the approved tenant-scoped uniqueness rule.
