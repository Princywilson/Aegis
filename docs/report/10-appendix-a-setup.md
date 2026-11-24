# APPENDIX 1

# LOCAL SETUP AND OPERATION

## A.1 Prerequisites

- Python 3.12
- Node.js 24 or compatible LTS
- npm
- Docker Engine and Docker Compose
- PostgreSQL 16 container
- Modern web browser

## A.2 Environment Preparation

Copy `backend/.env.example` to `backend/.env` and provide a unique Django secret key and database values. Do not commit real credentials. The environment values include:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `AEGIS_PRIVATE_STORAGE_ROOT` when custom private storage is required

## A.3 Start PostgreSQL

```powershell
docker compose up -d db
docker compose ps
```

The Compose service creates database `aegis` and a persistent named volume. Docker Compose credentials are development defaults and must be replaced for a deployed environment.

## A.4 Initialize the Backend

```powershell
.\venv\Scripts\python.exe backend\manage.py migrate
.\venv\Scripts\python.exe backend\manage.py seed_rbac
.\venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

The seed command creates the permission catalogue and standard organization roles. It is not a source of synthetic content or real user data.

## A.5 Start the Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` or the Vite URL reported by the terminal.

## A.6 Run Backend Tests

Run the test suite through the repository virtual environment. The application layout expects the Django apps to be discovered from `backend`.

```powershell
cd backend
..\venv\Scripts\python.exe manage.py test identity accountability knowledge --verbosity 1
```

PostgreSQL-only tests require PostgreSQL test database creation permission and should not be replaced by SQLite evidence.

## A.7 Run Frontend Tests

```powershell
cd frontend
npm test -- --run
npm run build
```

## A.8 Manual Smoke Test

1. Create or provision a synthetic organization and user.
2. Obtain a temporary password through the approved test procedure.
3. Open the login page.
4. Enter organization slug, email and password.
5. Confirm the correct workspace and role menu.
6. Create synthetic content and upload a PDF or raster image.
7. Publish a version.
8. Create a program and assignment.
9. Grant a synthetic consumer.
10. Open the secure viewer and confirm the page and watermark.
11. Revoke the grant and confirm a later page request is denied.
12. Review activity, audit and analytics using synthetic events.
13. Sign out.

Do not capture or publish real passwords, cookies, production secrets or confidential documents.
