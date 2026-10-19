# AEGIS Local Setup and Manual Testing Guide

This guide is based on the current repository state in this workspace only. It is intended to help a developer set up and manually verify AEGIS from a fresh Windows terminal without modifying application code, database contents, or environment files beyond the repo-supported local configuration.

For an end-user description of the available application pages and workflows, see the [AEGIS User Manual](user-manual.md).

Important notes before starting:

- This repository does not currently include a committed `backend/.env` file. The existing template is `backend/.env.example`.
- The repo does not expose real secrets in source control. Keep all local credentials private.
- The project uses a Dockerized PostgreSQL service (`docker-compose.yml`), a Django backend under `backend/`, and a Vite + React frontend under `frontend/`.
- The repo documentation records successful validation against Docker/PostgreSQL and Node.js, but the document below separates verified facts from needs-verification items.
- The user instruction explicitly says not to execute application commands or modify the environment as part of this documentation task. This guide therefore reflects the repository as it exists and the supported commands to run on your machine, rather than commands that were run here.

## A. Prerequisites and repository layout

### A.1 Required software

The repository and status documents confirm the following as part of the current environment:

- Windows 10/11 with PowerShell
- Git
- Docker Desktop with Docker Engine
- Python 3.12.10 in the local project environment (`venv` documented in status notes)
- Node.js 24.20.0
- npm 11.19.0
- PostgreSQL 16 via Docker Compose, not as a local install required by the app itself

What is supplied by Docker vs local install:

- Supplied by Docker: PostgreSQL 16 container and its data volume
- Must be installed locally: Git, Docker Desktop, Python, Node.js/npm
- Optional: a PostgreSQL client for shell-level database inspection if you want it, but the repo does not require a separate local database install

### A.2 Repository root and layout

Repository root (Windows path on this machine):

- `C:\Users\Princy\OneDrive\Desktop\Aegis`

Relevant directories:

- `backend/` — Django project, settings, API routes, custom models, management commands, migrations, requirements
- `frontend/` — Vite + React application, package manifest, CSS, tests
- `docs/` — project requirements, design docs, implementation status, architecture notes, API specification
- `docker-compose.yml` — PostgreSQL service definition
- `README.md` — minimal repo overview
- `venv/` — project virtual environment (exists in this repo as documented; reuse it if present)

The root-level repo also contains `Notes.md`, which is pre-existing and intentionally left alone by the project status notes. Do not modify it unless you explicitly decide to do so as part of your own local work.

### A.3 Where commands run

The repo instructions use a mix of root-level and subdirectory commands:

- Run root-level commands from the repository root.
- Run Django commands from the repo root using `backend\manage.py`.
- Run frontend commands from `frontend/`.
- Run Docker commands from the repo root because the Compose file is at the root.

### A.4 Checking installed versions and Docker health

The project documentation confirms the following checks are the ones to use:

```powershell
# From the repo root
Get-Command git
Get-Command python
Get-Command node
Get-Command npm
Get-Command docker

python --version
node --version
npm --version

docker info
```

If Docker Desktop is running correctly, `docker info` should return engine metadata instead of a connection error. If it fails, start Docker Desktop and wait until the engine is ready before proceeding.

### A.5 Supported local configuration assumptions

The repo includes a Docker Compose service named `db` in the root `docker-compose.yml` and a PostgreSQL 16 image. The local host configuration used by the project is therefore:

- Host: `127.0.0.1`
- Port: `5432`
- Database name: `aegis`
- Database user: `aegis`
- Database password: private local value, not documented in source control

The actual password and secret values in the Compose file are not safe to disclose in a public document. Keep them private and matching between Compose and backend environment settings.

## B. Environment and configuration setup

### B.1 Actual environment sources inspected

The project contains the following relevant configuration pieces:

- `backend/.env.example` — required template for backend environment values
- `backend/config/settings.py` — reads `backend/.env` and validates required settings
- `docker-compose.yml` — defines PostgreSQL service and local credentials
- `frontend/vite.config.js` — configures the frontend proxy to `http://127.0.0.1:8000`
- `backend/requirements.txt` — pinned backend dependencies
- `frontend/package.json` — frontend package scripts and dependencies

### B.2 Configuration inventory

| Setting or variable | Used by | Required? | Where to configure it | Safe example or source | How to verify |
|---|---|---:|---|---|---|
| `DJANGO_SECRET_KEY` | Django backend | Yes | `backend/.env` | A long random local secret, kept private | `backend/config/settings.py` reads it and raises `ImproperlyConfigured` if empty |
| `DJANGO_DEBUG` | Django backend | Yes | `backend/.env` | `true` for local development, `false` for production-like checks | `django.conf.settings.DEBUG` should echo the chosen state, and the app uses it for CORS/CSRF settings |
| `POSTGRES_DB` | Django + PostgreSQL | Yes | `backend/.env` and `docker-compose.yml` | `aegis` | Confirm it matches the Compose service configuration |
| `POSTGRES_USER` | Django + PostgreSQL | Yes | `backend/.env` and `docker-compose.yml` | `aegis` | Confirm it matches the Compose service configuration |
| `POSTGRES_PASSWORD` | Django + PostgreSQL | Yes | `backend/.env` and `docker-compose.yml` | Keep privately in local config; do not commit or print it | Confirm the app can connect to the running container without exposing secrets |
| `POSTGRES_HOST` | Django | Yes | `backend/.env` | `127.0.0.1` | `settings.py` expects a host string for the local Dockerized database |
| `POSTGRES_PORT` | Django | Yes | `backend/.env` | `5432` | Confirm it matches the port exposed by Docker Compose |
| `AEGIS_PRIVATE_STORAGE_ROOT` | Local storage configuration | Optional | `backend/.env` | Use a local folder path under `backend/private_storage` if you need local file storage | Check the setting value in a Django shell or environment inspection |
| CORS origins | Django | Yes in debug mode | `backend/config/settings.py` | `http://localhost:5173`, `http://127.0.0.1:5173`, etc. | Browser requests from the Vite app to Django should be allowed in local development |
| `ALLOWED_HOSTS` | Django | Yes | `backend/config/settings.py` | `localhost`, `127.0.0.1` | Confirm app starts without host-header errors when served locally |
| `CSRF_TRUSTED_ORIGINS` | Django | Yes in debug mode | `backend/config/settings.py` | Same as local frontend origins | verifies state-changing requests like login/logout are accepted |
| Frontend API proxy | Vite | Yes | `frontend/vite.config.js` | `/api` proxy to `http://127.0.0.1:8000` | Confirm `npm run dev` resolves API traffic to the backend |
| File storage / upload limits | Django knowledge app | Partially verified in code and tests | App settings + knowledge-specific upload validation | Keep local storage private; avoid large test files in production-like conditions | Validate via targeted tests and browser behavior |

### B.3 Required environment file

File to create:

```powershell
Copy-Item .\backend\.env.example .\backend\.env
```

The file does not currently exist in the checked-in repo. The project expects it for local runs and raises an error if values are missing.

The backend settings file is explicit about the requirement:

```python
load_dotenv(BASE_DIR / ".env")
```

and it fails fast if any required variable is empty.

### B.4 What you must configure

At minimum, configure these values in `backend/.env`:

```text
DJANGO_SECRET_KEY=<replace with a private local secret>
DJANGO_DEBUG=true
POSTGRES_DB=aegis
POSTGRES_USER=aegis
POSTGRES_PASSWORD=<private local password that matches the Docker Compose database>
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

Optional local additions:

```text
AEGIS_PRIVATE_STORAGE_ROOT=C:/path/to/your/project/backend/private_storage
```

Keep the password and secret values private. Do not print them in terminal output or save them in an unencrypted shared document.

### B.5 Safe verification without exposing secrets

Use environment-safe checks such as:

```powershell
Get-Content .\backend\.env | Select-String -Pattern "^DJANGO_DEBUG|^POSTGRES_DB|^POSTGRES_USER|^POSTGRES_HOST|^POSTGRES_PORT|^AEGIS_PRIVATE_STORAGE_ROOT"
```

This confirms the file exists and the non-secret keys are present without printing the secret values. Do not use `Get-Content` to dump the whole file if it contains a password or secret key.

## C. First-time setup from a fresh terminal

This is the supported first-run sequence for a Windows developer machine, based on the repository structure and current project files.

### C.1 Open the repo and terminal

1. Open the repository root in VS Code.
2. Open a PowerShell terminal in VS Code.
3. Ensure you are in the repo root.

```powershell
Set-Location "C:\Users\Princy\OneDrive\Desktop\Aegis"
```

### C.2 Check Git status before doing work

```powershell
git status --short
```

This helps you avoid overwriting or losing local changes. The repo is clean in this workspace, but your machine may not be.

### C.3 Confirm Docker is operational

```powershell
docker info
```

If Docker is not running, start Docker Desktop and wait for the engine to become ready before continuing.

### C.4 Check the actual Compose service names

```powershell
docker compose ps
```

The repo `docker-compose.yml` defines a service named `db`, which is the PostgreSQL database service for AEGIS.

### C.5 Start the database service

```powershell
docker compose up -d db
```

This starts the PostgreSQL 16 container in the background and preserves the data volume generated by the compose file.

### C.6 Create or update backend environment values

```powershell
Copy-Item .\backend\.env.example .\backend\.env
notepad .\backend\.env
```

Edit `backend/.env` to set the values described in Section B. Keep the secret values private.

### C.7 Set up or reuse the Python virtual environment

If the repo already has `venv`, reuse it:

```powershell
.\venv\Scripts\Activate.ps1
```

If it does not yet exist on your machine:

```powershell
python -m venv .venv
.\venv\Scripts\Activate.ps1
```

### C.8 Install backend dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r .\backend\requirements.txt
```

The backend requirements file is `backend/requirements.txt` and includes Django, DRF, Postgres drivers, CORS headers, dotenv support, Pillow, and PDF-related dependencies.

### C.9 Verify Django configuration

```powershell
.\venv\Scripts\python.exe .\backend\manage.py check
```

Success means Django can load the project and environment values without import or configuration errors.

### C.10 Determine whether migrations are pending and then apply them

```powershell
.\venv\Scripts\python.exe .\backend\manage.py showmigrations
.\venv\Scripts\python.exe .\backend\manage.py migrate
```

The repo documentation explicitly states migrations were verified against the configured PostgreSQL database, and that migration drift checks are expected to be clean. Do not run `migrate` on a production or shared local database unless you intend to preserve it and understand the effect. This is a local development database and not a destructive reset step.

### C.11 Initialize RBAC and assign the first organization role

The repository includes management commands for role initialization and assignment. The shipped code supports:

```powershell
.\venv\Scripts\python.exe .\backend\manage.py seed_rbac
```

This command seeds the permission catalogue and default roles for each organization in the database.

To assign a role to the first administrator user, create an organization and user in Django shell, then assign a role. The repo does not currently contain a public bootstrap registration API or a shipped `bootstrap_organization` management command. The repo docs mention a conceptual `bootstrap_organization` example, but the actual implementation in `backend/identity/management/commands/` contains `seed_rbac` and `assign_user_role` instead.

Use a guarded shell example such as:

```powershell
.\venv\Scripts\python.exe .\backend\manage.py shell -c "from identity.models import Organization, User; org, _ = Organization.objects.get_or_create(name='NIST Global', slug='nist'); user, _ = User.objects.get_or_create(email='princywilson2002@gmail.com', organization=org, defaults={'first_name': 'Princy', 'last_name': 'W'}); user.set_password('Princy@22'); user.is_staff = True; user.save(); print(org.slug, user.email)"
```

Then assign a role:

```powershell
.\venv\Scripts\python.exe .\backend\manage.py assign_user_role myOrg princywilson@gmail.com administrator
```

This is the supported bootstrapping pattern evidenced by the shipped commands and tests.

### C.12 Start the Django development server

```powershell
.\venv\Scripts\python.exe .\backend\manage.py runserver 127.0.0.1:8000
```

Open the backend URL once the process is running:

- `http://127.0.0.1:8000/admin/`
- `http://127.0.0.1:8000/api/v1/auth/csrf/`

The Django backend is separate from the Vite app; it must be running before the browser can log in and fetch `/api/v1/...` routes.

### C.13 Install frontend dependencies and start the Vite app

From the repo root:

```powershell
cd .\frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

This starts the React app, which is configured in `frontend/vite.config.js` to proxy `/api` to `http://127.0.0.1:8000`.

### C.14 Open the app in the browser

Open:

- `http://127.0.0.1:5173`

The frontend is a separate service from the Django backend. If you open the frontend without the backend running, login and data fetches will fail.

## D. Running AEGIS during normal development

### D.1 Repeatable development flow

After the initial setup, use this pattern:

1. Start Docker if it is not already running.
2. Start the PostgreSQL container if it is not already running:

```powershell
docker compose up -d db
```

3. Activate the virtual environment:

```powershell
.\venv\Scripts\Activate.ps1
```

4. Start Django in one terminal window:

```powershell
.\venv\Scripts\python.exe .\backend\manage.py runserver 127.0.0.1:8000
```

5. Start the frontend in another terminal window:

```powershell
cd .\frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

6. Open:

```text
http://127.0.0.1:5173
```

### D.2 Required services

The repo’s current structure expects:

- PostgreSQL container running
- Django backend running on `127.0.0.1:8000`
- React frontend running on `127.0.0.1:5173`

Do not assume the frontend alone is the application. The app is split across separate services.

### D.3 How to stop and restart safely

- Stop Django: press `Ctrl+C` in the backend terminal.
- Stop Vite: press `Ctrl+C` in the frontend terminal.
- Stop PostgreSQL: `docker compose stop db` or leave it running as a background container.

To restart:

```powershell
docker compose up -d db
.\venv\Scripts\python.exe .\backend\manage.py runserver 127.0.0.1:8000
cd .\frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

### D.4 How to verify PostgreSQL is running

```powershell
docker compose ps
docker compose logs --tail 50 db
```

You are looking for the `db` service to be healthy and listening on port `5432`.

### D.5 How to verify the backend without a health-check endpoint

The repo does not include a custom `/health/` endpoint in the inspected backend. The supported verification method is to hit actual project endpoints. For example, the app and tests use:

- `GET /api/v1/auth/csrf/`
- `POST /api/v1/auth/login/`
- `GET /api/v1/auth/me/`

You can verify the backend is responsive with a browser or a curl-like call such as:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/v1/auth/csrf/
```

This should return a JSON response containing a CSRF token or an expected application error if the service is not ready.

### D.6 How to tell frontend vs backend vs database issues apart

- Frontend not rendering or blank screen: likely a React/Vite issue or a missing page route.
- Frontend loads but requests to `/api/v1/...` fail: likely Django is not running or the database is unavailable.
- Browser dev-tools shows `401` or `403`: likely authentication or authorization problems, not a database problem.
- Browser dev-tools shows database or ORM errors in Django logs: likely backend and database issue.
- `docker compose ps` shows the DB service not running: likely PostgreSQL stack issue.

The repo’s current frontend calls `/api/v1/...` using `fetch` against the same origin via Vite proxy, and the backend uses Django session authentication plus CSRF protection.

## E. Initial organization and administrator login

### E.1 How authentication works

The repository verifies that authentication is organization-aware:

- `LoginSerializer` expects:
  - `organization_slug`
  - `email`
  - `password`
- `OrganizationEmailBackend.authenticate()` resolves the user by `organization__slug` and email, then checks the password and `user.is_active`.
- Session auth is used; the app uses Django session cookies and CSRF tokens rather than JWT.

The frontend login form uses those three fields.

### E.2 Actual login requirements

The frontend form asks for:

- Organization slug
- Email
- Password

The backend requires the session and CSRF token for unsafe requests.

### E.3 Supported initial account creation workflow

There is no public organization-registration endpoint in the implementation docs. The design specifically says: “Do not create a public organization-registration endpoint for the MVP.”

The repository contains the following supported bootstrap pattern:

1. Create the `Organization` record in Python shell or via a controlled bootstrap script.
2. Create the admin user in the same organization.
3. Run `seed_rbac` to populate the permission and role catalogue.
4. Run `assign_user_role` to assign the administrator role.

This is the safest pattern currently supported by shipped code.

### E.4 Management commands and exact syntax

Command names verified in the code:

```powershell
.\venv\Scripts\python.exe .\backend\manage.py seed_rbac
.\venv\Scripts\python.exe .\backend\manage.py assign_user_role <organization_slug> <email> <role_code>
```

Examples:

```powershell
.\venv\Scripts\python.exe .\backend\manage.py assign_user_role example admin@example.com administrator
```

Supported role codes from the deployed RBAC model include:

- `administrator`
- `content_manager`
- `content_consumer`
- `management`

### E.5 How to verify the user belongs to the correct organization

Use a Django shell check like this:

```powershell
.\venv\Scripts\python.exe .\backend\manage.py shell -c "from identity.models import User; u = User.objects.get(email='admin@example.com', organization__slug='example'); print(u.organization.slug, u.email, u.is_active)"
```

For role verification:

```powershell
.\venv\Scripts\python.exe .\backend\manage.py shell -c "from identity.models import User; from identity.rbac import effective_permission_codes; u = User.objects.get(email='princywilson2002@gmail.com', organization__slug='myOrg'); print(sorted(code for code in effective_permission_codes(u)))"
```

This confirms both organization membership and the effective permission set.

### E.6 If a user exists but cannot log in

Check the following:

- The user belongs to the same `organization_slug` used at login.
- The email is normalized and matches the stored value exactly.
- The user status is `ACTIVE`.
- The password was set correctly and not lost or changed inadvertently.
- The account is not rate-limited by the shared auth counter logic.

Good safe checks:

```powershell
.\venv\Scripts\python.exe .\backend\manage.py shell -c "from identity.models import User; u = User.objects.get(email='admin@example.com', organization__slug='example'); print(u.status, u.is_active, u.organization.slug)"
```

If the user is inactive or the role/permission set is missing, re-create or reassign as needed through the supported shell and command workflows.

### E.7 Password handling

Current code and tests show a temporary-password creation flow for new users, but the repo does not provide a one-click “reset password” page or a universal bootstrap command. A safe workflow is:

- create the initial organization and user in a controlled local shell or admin script;
- use a secure password in local development;
- store it outside the repo and outside shared documents;
- treat the temporary password as a one-time secure handoff when creating a user programmatically.

### E.8 Implementation gap to document clearly

The repo docs mention a conceptual `bootstrap_organization` command, but the actual shipped code in `backend/identity/management/commands/` includes only:

- `seed_rbac.py`
- `assign_user_role.py`

No actual `bootstrap_organization` command was found in the repository. This means the initial organization + admin user setup is a deliberate implementation/documentation gap unless you use the shell-based method described above.

## F. Application tour

The current frontend exposes the following routes after login. The app uses an authenticated single-page shell with a sidebar and route-based screens.

| Route | Screen name | Purpose | Prerequisites | Status |
|---|---|---|---|---|
| `/login` | Login | Sign into AEGIS using organization slug, email, and password | Backend running, database available | Implemented |
| `/` | Dashboard | Workspace overview, metrics, quick links | Valid session | Implemented |
| `/administration` (`/administrator` alias) | Administration | Manage organization users and view seeded roles/permissions | `USER_VIEW`, `ROLE_MANAGE`, or related permissions | Implemented |
| `/content` | Content library | Create and manage content, versions, archive/publish flows | `CONTENT_VIEW` or create rights depending on action | Implemented |
| `/programs` | Programs | Create, list, deactivate/activate programs and content assignments | `PROGRAM_VIEW` and related write permissions | Implemented |
| `/access` | Access and grants | Manage user access grants, delivery workflows, protected content access | `ACCESS_GRANT`, `ACCESS_REVOKE`, `PROFILE_VIEW_OWN`, and/or delivery rights | Implemented |
| `/viewer` | Secure viewer | Protected content delivery viewer | `SECURE_DELIVERY` permission and valid content access | Implemented |
| `/preview/{content_id}/{version_id}` | Privileged content preview | Render a selected non-archived draft or published version | `CONTENT_PREVIEW`, `CONTENT_VIEW`, and `VERSION_VIEW` | Implemented; migrations applied; manual acceptance pending |
| `/activity` | Activity | View organization activity data | Read rights for activity | Implemented |
| `/audit` | Audit records | View audit records | Organization audit permissions | Implemented |
| `/security-events` | Security events | Review security events | Security-event view permission | Implemented |
| `/analytics` | Analytics | Review analytics across content | Analytics permissions | Implemented |
| `/reports` | Reports | Review access reports | Report view permissions | Implemented |

### F.1 Frontend-to-backend routing overview

The actual API prefix is:

```text
/api/v1/
```

The current app calls endpoints such as:

- `/api/v1/auth/csrf/`
- `/api/v1/auth/login/`
- `/api/v1/auth/logout/`
- `/api/v1/auth/me/`
- `/api/v1/content/`
- `/api/v1/programs/`
- `/api/v1/analytics/content/`
- `/api/v1/reports/access/`
- `/api/v1/activities/`
- `/api/v1/audits/`
- `/api/v1/security-events/`

The Vite config proxies `/api` to the Django API origin at `http://127.0.0.1:8000`.

### F.2 How to distinguish empty screens vs failures

- Empty screen with no data: may simply mean no content or no assigned programs for the current user.
- Permission denied: UI often hides routes or returns access errors; check the user’s effective permissions.
- API failure: dev-tools network tab shows a failed request or `401`/`403`/`500`.
- Unimplemented feature: route may exist but UI or API is not available; the repo status notes explicitly call out that organization-management APIs remain unavailable in the current implementation.

## G. End-to-end manual testing scenarios

The following scenarios are supported by the shipped code and by the repo status documents. Anything marked “Needs verification” should be confirmed in your environment before treating it as a working feature.

### G1. Login, logout, and session handling

- Objective: Verify the session-based login flow works and user context loads correctly.
- Prerequisites: Django backend and frontend started; valid organization+user record exists.
- Role and organization: administrator or any known organization member.
- Starting screen: `/login`.
- Actions:
  1. Enter organization slug, email, password.
  2. Submit the sign-in form.
  3. Confirm the application loads the workspace overview.
  4. Open browser DevTools and confirm the session cookie is created.
  5. Sign out using the sidebar button.
  6. Confirm the app returns to `/login` and `/auth/me/` no longer returns a valid session.
  7. If an authorized disposable test account can safely trigger the configured login rate limit, confirm the UI gives a wait-and-retry message without exposing a precise countdown or whether the account exists. Do not trigger repeated failures against a shared or production account.
- Expected result: session created, secure page loads, logout clears session.
- Relevant backend results: `POST /api/v1/auth/login/`, `GET /api/v1/auth/me/`, `POST /api/v1/auth/logout/` with CSRF.
- Status: Implemented and verified in repo docs.

### G2. Organization isolation and access denial

- Objective: Ensure users cannot access data from another organization.
- Prerequisites: At least two organizations and users.
- Role and organization: administrator or content manager in one org; second org user exists.
- Actions:
  1. Log in as a user in `example`.
  2. Attempt to fetch or manipulate data from another organization via the UI or API.
  3. Confirm the request fails or the UI hides data.
- Expected result: cross-tenant access is blocked.
- Relevant backend result: tenant-scoped model filters and permission checks.
- Status: Implemented and supported by tests.

### G3. Role and permission enforcement

- Objective: Confirm effective permissions match assigned roles.
- Prerequisites: `seed_rbac` run and a user assigned to `administrator`, `content_manager`, `content_consumer`, or `management`.
- Actions:
  1. Log in as the user.
  2. Navigate to pages that should be visible or hidden.
  3. Cross-check the route access with the role and permission catalogue.
- Expected result: unauthorized screens or operations do not appear or fail with access errors.
- Relevant backend result: `effective_permission_codes()` and permission checks on APIs.
- Status: Implemented and tested.

### G4. Content creation, editing, versioning, and publication

- Objective: Create a content record, add a version, publish it, then archive or manage it.
- Prerequisites: a user with content-management rights.
- Starting screen: `/content`.
- Actions:
  1. Create a new content item.
  2. Add or upload a draft version.
  3. Publish the version.
  4. Verify the current version and status are updated.
  5. Archive the content or version if allowed by role.
- Expected result: content goes from draft to published behavior in the UI and backend.
- Relevant backend endpoints: `content/`, `content/<uuid>/versions/`, publish/archive endpoints.
- Status: Implemented; validate with repo tests and the browser UI.

### G5. Program creation, assignment, and activation

- Objective: Create a program and attach content to it.
- Prerequisites: authorized admin or program manager user.
- Starting screen: `/programs`.
- Actions:
  1. Create a program.
  2. Assign content to the program.
  3. Activate or deactivate the program.
  4. Verify it is visible or blocked appropriately.
- Relevant backend result: `Program` and `ContentAssignment` behavior, program access rules.
- Status: Implemented.

### G6. Access grants, revocation, expiry, and authorization checks

- Objective: Confirm authorized users can consume protected content only when grant and assignment rules allow it.
- Prerequisites: active program access grant and content assignment.
- Starting screen: `/access` or `/viewer`.
- Actions:
  1. Ensure the recipient is an active user with the `content_consumer` role. Create the user with that role from `/administrator`; an existing user's role can currently be assigned through the trusted `assign_user_role` management command.
  2. Select the active Content Consumer from `/access` (requires `USER_VIEW`), or enter that user's UUID when the role cannot view the directory.
  3. Create an access grant for that Content Consumer.
  4. Attempt delivery of protected content.
  5. Revoke or expire the grant and attempt access again.
- Expected result: access is allowed only under active grant and assignment conditions.
- Relevant backend result: `ProgramAccessGrant` logic and protected delivery enforcement.
- Status: Implemented and verified in repo tests.

### G7. Activity tracking, audit records, and security events

- Objective: Confirm the app records meaningful events.
- Prerequisites: proper permissions to view those screens.
- Starting screen: `/activity`, `/audit`, or `/security-events`.
- Actions:
  1. Perform a user or content operation that should emit an event.
  2. Refresh the screen.
  3. Confirm the record appears with correct organization scoping.
- Expected result: event records show tenant-scoped data and proper role gating.
- Relevant backend result: accountability models and event APIs.
- Status: Implemented.

### G8. Analytics and reports

- Objective: Review analytics and access metrics.
- Prerequisites: user has analytics/report permission.
- Starting screen: `/analytics` and `/reports`.
- Actions:
  1. Open the analytics page.
  2. Review metrics and report output.
  3. Compare with real content access data.
- Expected result: data loads and reflects content access patterns.
- Status: Implemented.

### G9. Invalid input and validation messages

- Objective: Confirm the UI and backend reject malformed or invalid input.
- Prerequisites: any logged-in user with access.
- Actions:
  1. Submit invalid or duplicate email values.
  2. Try empty organization slug or password.
  3. Try invalid upload or form fields.
- Expected result: a clear validation message is displayed; backend returns structured error payloads.
- Status: Implemented.

### G10. Unauthenticated and unauthorized API requests

- Objective: Confirm backend access control fails safely.
- Actions:
  1. Request `/api/v1/auth/me/` without a session.
  2. Attempt a restricted API call as an unauthorized user.
  3. Attempt to view a protected content or audit screen without rights.
- Expected result: generic, safe failures such as `401` or `403`.
- Related repo tests: identity and accountability authentication/authorization test suites.
- Status: Implemented and validated in repo docs.

### G11. File upload limits and oversized files

- Objective: Confirm upload limits are enforced.
- Prerequisites: content upload workflow with permissions.
- Actions:
  1. Upload an allowed file type and size.
  2. Attempt an oversized or unsupported file.
- Expected result: allowed files succeed; unsupported/oversized files fail with a clear error.
- Relevant backend validation: file type, MIME, and size allowlist.
- Status: Implemented; verify against the repo-specific rules and any local environment limits.

### G12. Browser recovery and non-destructive retries

- Objective: Ensure failed operations do not leave the app in a broken state.
- Actions:
  1. Trigger a failed login.
  2. Trigger an upload failure.
  3. Repeat the same action after fixing the input.
- Expected result: the app recovers and is ready for the next valid interaction.
- Status: Implemented as a product requirement; validate with the browser UI.

### G13. Privileged content preview

- Objective: Verify the separately authorized operator-preview workflow without
  changing consumer grants or assignment rules.
- Prerequisites: an active Administrator or Content Manager with
  `CONTENT_PREVIEW`, `CONTENT_VIEW`, and `VERSION_VIEW`; a non-archived Content
  item with a DRAFT or PUBLISHED PDF/image version; a synthetic or approved
  test file. The preview migrations and `seed_rbac` have already been applied
  to the configured local `aegis` development database. Do not reapply them.
- Starting screen: `/content`.
- Actions:
  1. Select the Content item and confirm **Preview** is present for eligible
     versions.
  2. Open a DRAFT version without publishing it or assigning it to a Program.
  3. Confirm the page renders with the visible `PREVIEW` watermark and the
     selected user, organization, time, Content, and version context.
  4. In browser Network tools, verify the start request is
     `POST /api/v1/content/{content_id}/preview/` and page requests use
     `GET /api/v1/content/{content_id}/preview/{access_id}/delivery?page=1`.
     Confirm page responses are watermarked PNG with `private, no-store`;
     no source-file URL or bytes are returned.
  5. Confirm a `CONTENT_PREVIEW_STARTED` audit record and preview-context
     viewer activity exist. Confirm no Program grant or Content assignment was
     created or changed, and preview activity is absent from consumer reports,
     analytics, and access-burst signals.
  6. Archive the Content or version, revoke `CONTENT_PREVIEW`, and try another
     page request. Confirm access is rejected. Also verify another user and a
     user in another organization cannot reuse the preview ID.
  7. Sign in as a Content Consumer with no preview permission and confirm no
     Preview action is shown and the API denies a preview start.
- Expected result: only the permitted operator can inspect eligible
  organization-owned content; current authorization is checked on each page;
  consumer grant/assignment behavior and consumer metrics remain unchanged.
- Status: Automated backend and frontend tests pass. Run authenticated browser
  acceptance using the configured development database and synthetic or
  approved test content. Record the outcome in `docs/implementation-status.md`.
  The migrations are installed on local `aegis`; do not repeat the migration or
  RBAC-seeding steps for this manual test.

### G14. Sidebar scrolling

- Objective: Confirm the desktop sidebar remains usable when its contents are
  taller than the viewport while the account controls remain fixed at the
  bottom and the navigation scrollbar stays visually hidden.
- Starting screen: Any authenticated page on a desktop-sized browser window.
- Actions:
  1. Reduce the browser viewport height until all navigation items and the
     account/sign-out area no longer fit.
  2. Confirm the profile name and **Sign out** control remain visible at the
     bottom while navigation items overflow above them.
  3. Scroll over the navigation list and confirm only its items move while the
     scrollbar itself is not visible.
  4. Use keyboard navigation to reach the final navigation item and the
     **Sign out** control.
  5. Widen/reduce the viewport to mobile size and confirm the horizontal
     navigation behavior remains intact.
- Expected result: Desktop navigation remains vertically scrollable and
  keyboard reachable without a visible scrollbar; profile and sign-out remain
  fixed at the bottom. Mobile navigation is unchanged.
- Status: Implemented; verify in browser as part of manual UI acceptance.

## H. Browser developer tools and API verification

### H.1 Use the browser dev tools

Open Chrome or Edge DevTools and inspect:

- Console tab for JavaScript errors and login issues
- Network tab for `/api/v1/...` fetch requests
- Cookies tab for the session cookie created by `login(request, user)`

### H.2 Confirm the frontend-to-backend flow

The repo’s frontend code uses a fetch wrapper and CSRF refresh logic in `frontend/src/api.js`:

- `refreshCsrfToken()` hits `/api/v1/auth/csrf/`
- `apiRequest()` sends `X-CSRFToken` on non-GET requests
- For state-changing requests, the browser includes credentials and a `same-site` session cookie

The backend uses Django session auth. This means the important browser artifacts to inspect are:

- Session cookie creation and persistence
- `X-CSRFToken` value on unsafe requests
- `401` or `403` responses and error payloads

Do not print or expose any actual token or cookie value in the guide or in chat. Only verify that it exists and is used.

### H.3 Inspect HTTP status codes and payloads

The repo uses a structured JSON error envelope such as:

```json
{
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "The supplied credentials are invalid or temporarily unavailable."
  }
}
```

Use the browser Network tab to inspect:

- status code
- request URL
- request method
- response body
- whether the failure was from React or the API response itself

### H.4 How to localize the failure origin

- React app errors in Console: frontend issue
- Failed `/api/v1/...` request without backend response: Django or database issue
- `401` or `403` without body or with generic error: auth/authorization issue
- `500` or server stack trace in API response: backend or database issue
- `docker compose ps` shows PostgreSQL stopped: DB issue
- Django dev server logs show a configuration problem: backend settings issue

This differentiation is important because the frontend is separate from the backend and both must be started and working.

## I. Automated tests and quality checks

The repo includes supported automated checks. Run them from the repo root or inside `frontend/` as appropriate.

### I.1 Django system checks and migration checks

```powershell
.\venv\Scripts\python.exe .\backend\manage.py check
.\venv\Scripts\python.exe .\backend\manage.py makemigrations --check --dry-run
```

These validate the Django configuration and confirm no migration drift is present.

### I.2 Backend tests

The repo status docs call out the following as relevant:

```powershell
.\venv\Scripts\python.exe .\backend\manage.py test identity
.\venv\Scripts\python.exe .\backend\manage.py test accountability
.\venv\Scripts\python.exe .\backend\manage.py test identity accountability knowledge
```

Use the project-specific labels rather than a bare `manage.py test` from the repo root, because the layout is set up as a Django project under `backend/`.

### I.3 Frontend tests

```powershell
cd .\frontend
npm test
```

This runs the Vite/React test suite. The `package.json` includes `vitest run` as the project test command.

### I.4 Frontend production build

```powershell
cd .\frontend
npm run build
```

This validates the front-end production build and is a useful sanity check before manual browser validation.

### I.5 Dependency and vulnerability checks

The repo status notes state that `npm audit` reported 0 vulnerabilities in the frontend. If you want to rerun the check:

```powershell
cd .\frontend
npm audit
```

This is a local verification step, not a destructive change.

### I.6 Formatting/linting

The project does not show a configured lint or formatting script in the frontend `package.json` beyond `dev`, `build`, and `test`. No additional formatter or linting tool is visibly configured in the repo.

### I.7 Distinguish automated tests and manual browser verification

- Automated tests verify code behavior under test conditions.
- Manual browser testing verifies real session, routing, and UI user flow behavior.
- The repo docs distinguish SQLite validation from PostgreSQL validation; do not treat SQLite results as proof of PostgreSQL correctness.

## J. Troubleshooting guide

| Symptom | Likely cause | Safe diagnostic step | Safe resolution |
|---|---|---|---|
| Docker Desktop not running | Docker engine unavailable | `docker info` | Start Docker Desktop and wait for the engine to become ready |
| PostgreSQL container not running | Compose service not started | `docker compose ps` and `docker compose logs --tail 50 db` | `docker compose up -d db` |
| Port conflict on 5432 or 5173 | Another local service is using the port | `netstat -ano` or browser error output | Stop the conflicting local process or choose a different local port only if the project configuration is updated intentionally |
| Database connection failure | Missing or wrong `.env` values | Check `backend/.env` keys and the Compose service values | Update the local env file to match the compose DB service without printing secrets |
| Django config error | Missing env variable or bad value | `python backend\manage.py check` | Fix the local `.env` values; do not commit secrets |
| Migration drift or pending migrations | Schema mismatch | `python backend\manage.py showmigrations` and `makemigrations --check --dry-run` | Apply migrations with `migrate` only when the DB is intended to be updated |
| Missing backend dependencies | Python packages not installed | `python -m pip install -r backend\requirements.txt` | Reinstall the repo’s pinned backend requirements |
| Missing frontend dependencies | Node modules absent | `cd frontend` then `npm ci` | Reinstall dependencies from the lockfile |
| Vite not starting | Node/npm or port issue | `npm run dev -- --host 127.0.0.1 --port 5173` | Fix local Node version or port conflict |
| Frontend loads but API calls fail | Django backend or database not running | Check browser network tab and backend terminal logs | Start Django and confirm the API is running on `127.0.0.1:8000` |
| CSRF or session issue | Missing CSRF token or stale session | Verify `/api/v1/auth/csrf/` and inspect browser cookies | Ensure the frontend is using the session auth path and the backend is started |
| Login page works but login fails | Wrong organization slug, email, or password | Check user record and org slug in Django shell | Recreate the org/user and assign the right role |
| Organization or role missing | Bootstrapping incomplete | `python backend\manage.py seed_rbac` and inspect the user record | Make sure the role is assigned using `assign_user_role` |
| User creation or access grant returns a validation error | Invalid email/role input, duplicate organization email, or the selected grant recipient is not an active Content Consumer | Read the field-specific message displayed with the 400 response | Correct the highlighted input; grant access only to an active Content Consumer in the same organization |
| No users appear in the `/access` grant dropdown | The dropdown lists only active users assigned the `content_consumer` role; organization membership by itself is not sufficient | Check the user's active status and role in `/administrator` or inspect organization-scoped role assignments | Create the user with the Content Consumer role in `/administrator`. To assign it to an existing user, an authorized operator can run `.\venv\Scripts\python.exe .\backend\manage.py assign_user_role <organization_slug> <email> content_consumer`; confirm the organization and intended role before running it |
| Organization user is not on the first page | The directory is paginated | Use the Previous/Next controls below the user list and check the current search filter | Clear the search or move through the pages |
| Permission denied | Missing permission or wrong role | Check effective permission codes in Django shell | Assign the proper role to the user |
| Content upload fails | Wrong file, unsupported type, or size limit | Check upload file type and size | Use a supported upload through the app and confirm the local storage path is valid |
| Protected viewer fails | Missing access grant, assignment, or valid published version | Check the content access grant and program assignment data | Correct the grant and published version state |
| Analytics/report missing data | No access events or permission issue | Compare with activity screens and backend permissions | Confirm the user has the required permission and events were recorded |
| Test failure | Local mismatch or environment drift | Run the targeted Django or frontend test command | Use the repo-specific command and keep the environment state explicit |

### J.1 Safe command examples

```powershell
# Check Docker

docker compose ps

docker compose logs --tail 50 db

# Check Django config
.\venv\Scripts\python.exe .\backend\manage.py check

# Check migrations
.\venv\Scripts\python.exe .\backend\manage.py showmigrations
.\venv\Scripts\python.exe .\backend\manage.py makemigrations --check --dry-run

# Check frontend build
cd .\frontend
npm run build
```

Never use a command that deletes data, drops volumes, or resets a database as a first attempt. The repository guidance explicitly warns against destructive resets and database deletion for routine troubleshooting.

## K. Security, data protection, and local-development limitations

### K.1 Verified security properties

The repo status notes and tests document the following security properties that were checked in the current implementation:

- Generic authentication failures do not reveal whether an organization or account exists.
- Session cookies are HttpOnly and CSRF-protected for unsafe requests.
- Organization scoping is enforced for user and audit data.
- Security-event and activity data are restricted by organization and role.
- Login failures are rate-limited with shared PostgreSQL storage.
- Cross-organization role assignment is rejected.

### K.2 Partial verification or gaps

The following items are either partly verified or still need explicit confirmation in a fresh local setup:

- There is no real public registration workflow for the initial organization.
- There is no full admin bootstrap flow in the shipped management commands.
- A `bootstrap_organization` example appears in the design documentation, but it was not found in the actual command set.
- Production scheduling for cleanup jobs is environment-specific and is not configured in the repo.
- Some acceptance criteria or operational follow-ups remain documented as “needs verification” or “not yet complete.”

### K.3 Local dev vs production differences

- Local development uses `DJANGO_DEBUG=true` and local CORS/CSRF origins.
- The repo documents production cookie security settings; they are different from local testing config.
- The app is running on a local machine with a Dockerized PostgreSQL service, not behind a production ingress or a managed cloud database.
- Local storage for uploaded files and protected content is not a production-grade object-store service.

### K.4 Data handling and safety

- Do not check in or share `backend/.env` files.
- Do not paste real credentials or secrets into the chat or guide.
- Do not use real customer or organizational data during local testing.
- Keep all local test data and temporary users inside a dev-only environment.
- Avoid destructive cleanup commands or DB resets unless you know exactly what you are doing and have a safe backup.

## L. Manual testing checklist and evidence log

### L.1 Reusable checklist

- [ ] Environment ready (Git, Docker, Python, Node/npm installed)
- [ ] PostgreSQL container is running
- [ ] Django backend is running on `127.0.0.1:8000`
- [ ] Frontend is running on `127.0.0.1:5173`
- [ ] Login successful with a valid organization and user
- [ ] Organization and role verified
- [ ] Dashboard and main navigation tested
- [ ] Content flow tested
- [ ] Program flow tested
- [ ] Access grant and delivery flow tested
- [ ] Activity, audit, and security-event screens checked
- [ ] Analytics and reports checked
- [ ] Authorization and org isolation tested
- [ ] Browser console checked for errors
- [ ] Browser network tab checked for API success and failure status
- [ ] Relevant Django and frontend tests rerun
- [ ] Known limitations documented

### L.2 Evidence table template

| Date | Environment | Test ID | Result | Evidence or error summary | Follow-up |
|---|---|---|---|---|---|
| YYYY-MM-DD | Local Windows dev | G1 | Pass/Fail/Blocked | Example: login succeeded, session created, logout returned to `/login` | If fail, check org slug, email, password, and Docker/Django availability |
| YYYY-MM-DD | Local Windows dev | G3 | Pass/Fail/Blocked | Example: role-based route access matched expected permissions | If fail, verify `seed_rbac` and `assign_user_role` outputs |
| YYYY-MM-DD | Local Windows dev | I2 | Pass/Fail/Blocked | Example: identity tests passed | If fail, check PostgreSQL connectivity and `.env` values |

Do not record passwords, access tokens, or secrets in the evidence log.

## Final verification before completing the guide

Before treating this guide as complete, check the following:

- Paths and filenames match the repository layout.
- The environment variable names match `backend/config/settings.py` and `backend/.env.example`.
- The port numbers and services match the project configuration.
- The first-time setup flow is separated from the normal restart flow.
- The instructions preserve existing data and do not instruct destructive resets.
- No real credentials, secrets, or passwords appear in the document.
- Unverified gaps are explicitly called out as “Needs verification.”

## Summary of the repository reality

The repository clearly supports a local Windows workflow that includes:

- Dockerized PostgreSQL (`db` service)
- Django backend under `backend/`
- Vite/React frontend under `frontend/`
- A project-specific RBAC system initialized via `seed_rbac`
- A role assignment command, `assign_user_role`
- A session-based auth flow with organization slug + email + password
- A set of API endpoints, screens, and tests covering identity, accountability, and knowledge work

The major remaining gap is that the repository does not appear to provide a fully documented, shipped, safe bootstrap flow for creating the first organization and administrator user out of the box. The code and docs do show the supported pattern, but it requires a controlled Django shell or a manual shell-based bootstrap procedure.

## M. Scope expansion: manual verification

This section extends the local setup guide for risk review, investigations, and knowledge retrieval. Complete sections A–K first. Use only a development database and synthetic content; do not use production or customer data.

### M.1 Read the current feature boundary first

The current implementation exposes these additions through the backend API and React application:

- A React **Risk signals** page and advisory signal/summary APIs. These are not contextual access policies and do not grant, deny, or revoke access.
- A React **Risk investigations** workflow and organization-scoped list/detail/create/update endpoints. The workflow supports validated filters, pagination, evidence references, edits, and lifecycle transitions.
- A React **Knowledge search** page and permission-aware retrieval endpoint over Content titles and descriptions. It is retrieval-only, not semantic document search and not a generative RAG assistant.

The feature APIs use existing session authentication and permissions. The risk and investigation endpoints require organization-wide security-event visibility; the retrieval endpoint requires content-search permission and also checks content-view permission. Evidence sources are independently permission-checked and hidden if they are no longer visible to the caller. Risk signals and investigations are available in the React navigation to users with the corresponding permission. The procedures below combine UI checks with direct API checks for negative authorization and validation cases.

### M.2 Verification limitations to account for

The following are implementation limitations that affect expected manual results. Record them as gaps; do not treat a missing result as a successful acceptance test:

1. The repeated-denial signal reads the normal `ACCESS_DENIED` `SecurityEvent` path and requires a content resource and non-null user. Do not insert fabricated evidence into a shared or persistent database to make this signal appear.
2. Risk, investigation, and metadata-search workflows have focused automated backend/frontend coverage, but authenticated browser acceptance has not yet been recorded.
3. Investigation evidence references are limited to persisted Security Events and Audit Records, at most 25 per case. Security-event evidence must be a Content `ACCESS_DENIED` event; audit evidence is limited to supported Content-related resource types. Source visibility is checked again when a case is read.
4. Retrieval searches only title and description metadata. It does not extract or search the private PDF/PPTX document body, create chunks, or call an AI model. Its response text is fixed retrieval status, not an LLM answer.
5. The existing risk thresholds and severity assignments are not validated risk scores or formally approved business policy. No labeled anomaly dataset or real-world precision/recall evaluation exists.
6. Retrieval is live case-insensitive substring matching with a 200-character query limit and at most five results. There is no persistent index or semantic relevance ranking, and the endpoint is not a completed generative RAG assistant.
7. The risk API applies inclusive timezone-aware `from`/`to` filters and bounded pagination. The list defaults to page 1 with 20 items and allows at most 100 items per page. The summary endpoint accepts the same time and signal filters but no pagination parameters.

These findings mean the three capabilities are not yet equivalent to contextual access-policy enforcement, complete evidence-integrated case management, or generative RAG. The retrieval-only endpoint may be manually exercised, but describe it accurately as permission-aware metadata retrieval.

### M.3 Prepare test data

Use the normal application UI with an authorized test administrator:

1. Confirm the administrator can see the intended workspace and has `SECURITY_EVENT_VIEW_ORGANIZATION`.
2. Create or identify a separate active Content Consumer in the same organization.
3. Create at least three synthetic content records with distinct titles/descriptions. Upload and publish a supported version for each.
4. Create an active program, assign all three published content items to it, and grant the Content Consumer access to that program.
5. If testing tenant isolation, use a second test organization and a consumer in that organization. Never reuse a real user account.

Do not change the application authorization model or manually modify protected records as part of these checks. Access tests should use the application endpoints and existing admin screens.

### M.4 Create an authenticated PowerShell API session

Run in PowerShell. Substitute the test account's organization slug and credentials locally. Do not save this script with credentials or include secrets in test evidence.

```powershell
$BaseUrl = "http://127.0.0.1:8000/api/v1"
$Session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

$CsrfResponse = Invoke-RestMethod `
  -Uri "$BaseUrl/auth/csrf/" `
  -Method Get `
  -WebSession $Session
$CsrfToken = $CsrfResponse.data.csrf_token

$OrganizationSlug = Read-Host "Test organization slug"
$Email = Read-Host "Test user email"
$SecurePassword = Read-Host "Test user password" -AsSecureString
$PasswordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
try {
  $PlainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($PasswordPointer)
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($PasswordPointer)
}
$LoginBody = @{
  organization_slug = $OrganizationSlug
  email = $Email
  password = $PlainPassword
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "$BaseUrl/auth/login/" `
  -Method Post `
  -WebSession $Session `
  -Headers @{ "X-CSRFToken" = $CsrfToken } `
  -ContentType "application/json" `
  -Body $LoginBody
Remove-Variable PlainPassword, LoginBody, SecurePassword -ErrorAction SilentlyContinue

Invoke-RestMethod -Uri "$BaseUrl/auth/me/" -Method Get -WebSession $Session
```

The `/auth/me/` response should identify the expected organization, roles, and effective permissions. Repeat this setup using a separate session when testing as the Content Consumer or second-organization user.

For subsequent unsafe requests in the same session, pass `-WebSession $Session` and `-Headers @{ "X-CSRFToken" = $CsrfToken }`. Use GET requests without a CSRF header. If the session expires, repeat the CSRF and login steps.

### M.5 Capability A — advisory risk signal checks

**A1. Access-burst rule (supported by normal access flow)**

1. Sign in as the Content Consumer test user.
2. Open at least four access sessions over three or more distinct, published, assigned content items during the configured 24-hour window. For each item, use the normal viewer flow or call the existing access-start endpoint:

   ```powershell
   $ContentId = "<published-assigned-content-uuid>"
   $ProgramId = "<active-program-uuid>"
   $Body = @{ program_id = $ProgramId } | ConvertTo-Json
   Invoke-RestMethod `
     -Uri "$BaseUrl/content/$ContentId/access/" `
     -Method Post `
     -WebSession $Session `
     -Headers @{ "X-CSRFToken" = $CsrfToken } `
     -ContentType "application/json" `
     -Body $Body
   ```

   Repeat for a total of at least four successful access starts and at least three distinct content IDs. Each attempt creates a granted access record; do not reuse the same content ID for every attempt if testing the distinct-content threshold.
3. Sign in as the authorized administrator, open **Risk signals** from the sidebar, and check the signal type, severity, event count, content count (for bursts), observed window, and explanation. Set optional **From** and **To** filters and use the pagination controls.
4. Verify that a timezone-aware bounded API request returns the same filtered result and pagination metadata:

   ```powershell
   $From = [DateTimeOffset]::UtcNow.AddHours(-24).ToString("o")
   $To = [DateTimeOffset]::UtcNow.ToString("o")
   Invoke-RestMethod -Uri "$BaseUrl/risk-signals/?from=$([uri]::EscapeDataString($From))&to=$([uri]::EscapeDataString($To))&page=1&page_size=20" -Method Get -WebSession $Session
   Invoke-RestMethod -Uri "$BaseUrl/risk-signals/summary/?from=$([uri]::EscapeDataString($From))&to=$([uri]::EscapeDataString($To))" -Method Get -WebSession $Session
   ```

5. Check for an `ACCESS_BURST` signal for the consumer, with the expected organization scope, event count, content count, reason, and timestamps.
6. Confirm the consumer's access still succeeds or is denied solely according to existing grants, assignments, publication, and permission checks. A signal must not change that outcome.

**Expected:** The burst appears only when the rule thresholds and time window are met. The signal is informational; no access state changes.

**A2. Repeated-denial rule**

1. As the consumer, attempt a delivery operation for content to which the user is not authorized.
2. Confirm the request is denied and the existing security-event screen/API records the access-denied security event.
3. Query the Risk signals page or `/risk-signals/` as the authorized administrator.
4. Confirm that at least three denied Content events for that user in one rolling 24-hour window produce `REPEATED_DENIALS` with MEDIUM severity.

Do not create denied `ContentAccess` or `SecurityEvent` evidence by hand in a shared or production database. Use the normal denial path or deterministic automated test fixtures.

**A3. Authorization and tenant isolation**

1. Sign in as a user without `SECURITY_EVENT_VIEW_ORGANIZATION`; request `/risk-signals/` and `/risk-investigations/`. Expect authorization failure.
2. Sign in as an authorized administrator for Organization A. Verify the returned signal data contains no user/resource identifiers from Organization B.
3. Try filtering using any unsupported query parameter. Expect a validation error rather than silently accepted filters.
4. Try a reversed or timezone-naive date range, page zero, a non-integer page size, and a page size above 100. Expect a validation response for each.

### M.6 Capability B — risk-investigation workflow and API checks

Use an administrator with `SECURITY_EVENT_VIEW_ORGANIZATION`. To test Audit Record evidence visibility, the account also needs `AUDIT_VIEW_ORGANIZATION`.

1. In the React navigation, open **Risk investigations**. Verify the list, status/severity filters, pagination, empty state, and loading/error feedback. Confirm **Apply filters** is aligned with the fields and uses the primary blue button style.
2. Select **+ New investigation** and verify the creation form opens in a dialog. Select an existing Security Event reference from the evidence selector, enter a synthetic title/summary/note, choose a severity, and create the case. The selector contains only currently visible Content `ACCESS_DENIED` events; do not fabricate IDs or modify source records.
3. Open the new case. Verify its details and evidence metadata. Edit title, summary, notes, severity, or evidence, then save. Confirm success/error feedback and that the saved data is reloaded from the API.
4. Exercise allowed transitions (`OPEN` → `IN_REVIEW` or `DISMISSED`; `IN_REVIEW` → `RESOLVED` or `DISMISSED`) and verify terminal statuses expose no further transition controls and all detail fields are read-only.
5. For each terminal status, attempt an API PATCH with a changed title, notes, severity, evidence, or repeated status. Expect HTTP 400, no record mutation, and no new successful-mutation audit record. Confirm an authorized GET still returns the closed record.
6. Obtain the case UUID from the investigation list API, then inspect its audit records using an account authorized to view audit records:

   ```powershell
   $Cases = Invoke-RestMethod `
     -Uri "$BaseUrl/risk-investigations/?page=1&page_size=100" `
     -Method Get `
     -WebSession $Session
   $InvestigationId = $Cases.results[0].id
   Invoke-RestMethod `
     -Uri "$BaseUrl/audits/?resource_type=risk_investigation&resource_id=$InvestigationId" `
     -Method Get `
     -WebSession $Session
   ```

   Verify creation, every meaningful edit (including a notes-only edit), evidence changes, and transitions are represented by audit actions. Confirm audit metadata identifies changed field names and evidence counts but does not contain raw notes, summary, or title text.
7. For negative API checks, attempt `OPEN` → `RESOLVED`, an invalid status/severity, an unknown field, a duplicate/malformed/nonexistent evidence reference, or a cross-organization evidence ID. Expect a validation failure and no partial mutation. Use only IDs from test data.
8. Confirm a user without `SECURITY_EVENT_VIEW_ORGANIZATION` is denied list, detail, create, and update. Confirm a different organization's authorized operator receives not-found for the case. If a source permission is revoked, verify that source is omitted from the case detail without exposing its ID or metadata.
9. Re-read the original evidence record before and after edits; it must remain unchanged.

These steps exercise both the React workflow and backend authorization boundary. Automated tests cover more transition combinations and evidence cases; manual checks must still be recorded separately.

### M.7 Capability C — permission-aware metadata retrieval checks

Use the React **Knowledge search** page with a consumer account. Confirm that its explanation says it searches Content metadata only, enter a title/description phrase, and verify the authorized citations or empty state appears in the results table within the search panel. The API endpoint is `POST /assistant/query/`; use a session for the consumer whose permissions/grants are under test for the negative checks below.

```powershell
$Body = @{ question = "Distinctive exact phrase in a published content title" } | ConvertTo-Json
Invoke-RestMethod `
  -Uri "$BaseUrl/assistant/query/" `
  -Method Post `
  -WebSession $Session `
  -Headers @{ "X-CSRFToken" = $CsrfToken } `
  -ContentType "application/json" `
  -Body $Body
```

Run these checks:

1. **Authorized match:** Use a distinctive title or description phrase from a published, assigned item in an active program with an active grant. Expect a citation with content ID, title, current version number, authorized Program names where the user has `PROGRAM_VIEW`, and metadata summary. Do not expect a generated answer or passage citation.
2. **No match:** Search for a phrase absent from authorized titles/descriptions. Expect an empty citation list and `insufficient_authorized_sources: true`.
3. **Cross-organization isolation:** Sign in as a consumer in another organization and search for Organization A's distinctive phrase. Expect no citation for Organization A.
4. **Revoked grant:** Revoke the test consumer's grant and repeat the query. The source must no longer be cited.
5. **Inactive assignment/program, unpublished content, or stale/mismatched current version:** Change the test fixture through authorized application workflows, then repeat retrieval. The ineligible item must not be cited. Restore test data only through normal supported management actions.
6. **Permission failure:** Use a user without `CONTENT_SEARCH`; expect authorization failure. If search permission exists but content-view permission is removed in a controlled test role, retrieval must also fail.
7. **Invalid/blank question:** Send an empty or whitespace-only question; expect HTTP 400 and no sources.
8. **Citation metadata scope:** Assign the same Content to another Program that is not granted to the consumer. Repeat the query and verify the unauthorized Program name is absent. Also verify citations do not include raw storage keys/URLs, file content, or inaccessible resource metadata.

The UI supports metadata search and citations, but does not provide semantic retrieval, document-body indexing, citation passage offsets, model grounding, or generative RAG.

### M.8 Scope-expansion evidence log

Use the evidence table in L.2 and add a row for each test ID. Record the account role and organization using synthetic labels only. Never capture credentials, session cookies, CSRF tokens, or private content.

| Test ID | Capability | Expected result | Current status |
|---|---|---|---|
| M-A1 | Access burst | Advisory signal at the documented threshold; access decision unchanged | Manually verify |
| M-A2 | Repeated denials | Signal from denial evidence | Automated tests pass; manual verify with normal events |
| M-A3 | Signal authorization/tenant isolation | Unauthorized request denied; no cross-org data | Manually verify |
| M-B1 | Investigation transitions and edits | Allowed transitions succeed; invalid transitions rejected; meaningful edits audited | Automated tests pass; manual verify |
| M-B2 | Evidence references and read visibility | Valid source references accepted; malformed/cross-tenant/unauthorized references rejected; revoked source hidden | Automated tests pass; manual verify |
| M-B3 | Investigation authorization/tenant isolation | Denied or not found across unauthorized scope | Automated tests pass; manual verify |
| M-C1 | Authorized metadata retrieval | Current authorized citation only | Automated tests pass; manual verify |
| M-C2 | Revocation and stale/ineligible source exclusion | Source omitted after access/lifecycle change | Automated tests pass; manual verify |
| M-C3 | Invalid query / insufficient sources | Safe validation or empty-source response | Automated tests pass; manual verify |
| M-UI1 | Investigation/search layout and dialog | Filter controls align; investigation creation is modal; authorized metadata matches display in the search panel | Automated tests pass; manual verify |
| M-UI2 | Navigation and rate-limit guidance | Sidebar remains usable at small viewport heights; sign-out is recognizable; 429 advises waiting without inventing a retry time | Automated tests pass; manual verify |

### M.9 Do not declare all scope expansion capabilities complete based on manual checks

Manual testing can exercise the implemented paths, but the current code does not enforce contextual access policies and does not implement semantic document retrieval or a generative RAG assistant. Record manual outcomes in `docs/implementation-status.md`; do not mark a failed or unavailable check as passed.
