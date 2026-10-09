# AEGIS Implementation Status

**Last reviewed:** 2026-10-09  
**Source of truth:** [Implementation Guide](implementation-guide.md.md)

This file records implementation progress and how to test the work that exists. A check passing on SQLite is not evidence that PostgreSQL integration has passed.

## Milestone 0: Development Foundation

### Verified

- Inspected the Django project structure, settings, API routing, requirements, environment template, migrations, and Docker Compose configuration.
- Python 3.12.10 and the pinned backend requirements are available in `venv`.
- `docker info` succeeds and the Compose PostgreSQL 16 service is running.
- The local PostgreSQL role credentials were aligned to the current Compose configuration to restore host authentication; no application data was changed.
- Django's system check passes.
- A custom-format backup of the existing `aegis` database, `aegis-before-migration-repair-20261009.dump`, was created locally, its archive listing verified, and restored into a disposable database before repair.
- The existing `aegis` database was repaired from the verified backup: the current identity migration is recorded, the login column and missing permission/group join tables match the current model, and the tenant-email constraint uses its current name.
- All current migrations now apply on `aegis`; `showmigrations` reports them applied and `makemigrations --check --dry-run` reports no changes.
- Temporary validation and repair-clone databases were removed after successful verification.

### Not yet complete

- `backend/.env` is absent. PostgreSQL validation used process-local environment variables; no credentials were added to source or documentation.
- The legacy recorder entry `identity.0001_initial_organization_and_user` is retained as historical metadata; the current `identity.0001_initial` entry is also recorded, so Django's current migration graph is consistent.
- Node.js and npm are unavailable, so the full M0 toolchain check is incomplete.
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
- `/me` returns identity and organization details; role and permission arrays remain empty until M3.
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
- Security-event read authorization tests belong with the future security-event monitoring API; organization users must never see platform-level or other-tenant events.
- The `activity_events` model is not implemented yet; validate its required organization ownership when its milestone begins.

## How to Test Now

### SQLite development checks

Run from the repository root. Test-only environment values let Django load settings when `backend/.env` is absent; the command then replaces the database with in-memory SQLite. It checks configuration and migration consistency, then runs the implemented identity and accountability tests. The PostgreSQL-only concurrency cases are skipped.

```powershell
.\venv\Scripts\python.exe -c "import os,sys; os.environ.update({'DJANGO_SECRET_KEY':'sqlite-test-only-secret','DJANGO_DEBUG':'true','POSTGRES_DB':'unused','POSTGRES_USER':'unused','POSTGRES_PASSWORD':'unused','POSTGRES_HOST':'127.0.0.1','POSTGRES_PORT':'5432'}); sys.path.insert(0,'backend'); os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); from django.conf import settings; settings.DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':':memory:'}}; import django; django.setup(); from django.core.management import call_command; call_command('check'); call_command('makemigrations','--check','--dry-run'); call_command('test','identity','accountability',verbosity=1)"
```

Expected results: a clean system check, `No changes detected`, and 35 tests with two PostgreSQL-only tests skipped.

### PostgreSQL integration checks

Use a clean PostgreSQL database and set the Django/PostgreSQL environment variables privately before running. Do not put credentials in this file. Run `.\venv\Scripts\python.exe backend\manage.py test identity accountability` from the repository root, or run `manage.py test` from `backend\` to discover the complete suite. Running bare `manage.py test` from the repository root discovers zero tests in this layout.

## Next Implementation Step

M0/M1 database gates and M2 PostgreSQL integration checks now pass. The approved domain-neutral role name is `Content Consumer`, defined as a user authorized to access and consume organizational content according to assigned permissions and access grants. This is a role of the existing `User`, not a separate user type/entity/table. The documentation rename does not change runtime authorization. Preserve the former Trainer role's permission associations exactly; do not infer additional permissions from the new name. The agreed high-level access boundary is assigned/authorized content and permitted current versions, searching only that authorized content, secure content delivery without source-file download/sharing, no content mutation/publishing/archiving/version creation/assignment changes absent separate explicit permission, and tracking significant content interactions. Limited analytics/report access is restricted to the user's own activity and reports for content/programs assigned to them; organization-wide analytics and audit/security-event access are excluded.

M3 RBAC implementation remains gated: current functional/API authorization tables are conceptual and do not establish a complete permission-by-permission role matrix. Their shared baseline grants sign-in, own-profile access, authorized content viewing/delivery and activity tracking; the functional matrix additionally indicates content/version/program viewing and watermark consumption. Both describe limited analytics, and the functional matrix also describes limited reports; these are bounded to the user's own activity and assigned content/programs. The API matrix explicitly excludes organization/user/role/permission management, content creation/management, version creation/publication, program management, assignment and access-grant management, audit, and security-event access. Before implementation, reconcile the summaries into an explicit capability-to-role mapping that preserves this agreed scope and the former Trainer associations, then implement the rename without changing authorization behavior. Legacy trainer-analytics API paths, permission identifiers, and response fields are unchanged by this documentation-only role rename; the aggregate analytics response is outside the Content Consumer's approved scope unless a completed permission matrix authorizes an appropriately scoped version. Training-specific concepts such as Training Program, Training Access, and Trainer Access are separate terminology-review items; their names and behavior have not been changed by the role rename.

M0 still needs Node.js/npm, a local `backend/.env`, and the clean-worktree/baseline checkpoint criteria.
