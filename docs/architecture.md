# AEGIS Architecture

AEGIS (Enterprise Knowledge Protection and Delivery Platform) is a multi-tenant SaaS platform for enterprise knowledge governance and delivery.

This document records the **initial high-level architecture**. It does not define product features or business rules.

**Status key**

- **Confirmed** — decided for this phase.
- **Proposed** — recommended starting point; not finalized.
- **To Be Decided** — must be resolved before that part of implementation.

---

## 1. System Overview

AEGIS is a web application with a React (TypeScript) frontend and a Django backend that uses Django REST Framework. The frontend is a client. The backend owns business logic, authorization, data access, and persistence. The two communicate over a versioned REST API (`/api/v1/`) using JSON. PostgreSQL is the primary database, shared across tenants in a shared schema.

The platform serves multiple Organizations (tenants) on a shared product. A User may belong to more than one Organization. Access is authenticated with JWTs and authorized with server-side RBAC. The product remains industry-independent and domain-neutral.

No production cloud provider, hosting platform, object-storage vendor, secret-management provider, monitoring provider, or database host is assumed.

---

## 2. Architectural Principles

**Confirmed**

- Security First.
- REST API based frontend/backend separation.
- Multi-tenancy is a design constraint for backend and database work.
- Tenant isolation must never depend only on frontend behavior.
- The platform stays industry-independent and domain-neutral.
- Prefer modular, maintainable, scalable, and secure design.
- Prefer simple, readable code over unnecessary complexity.
- Do not introduce dependencies unless they are justified.
- Follow the project’s domain-neutral terminology rules. Do not introduce industry-specific terminology.

**Proposed**

- Keep presentation in the frontend; keep business logic and data access in the backend.
- Treat validation, authorization, error handling, logging, and testing as part of each feature, not as later add-ons.

---

## 3. Frontend Architecture

**Confirmed**

- Frontend is React with TypeScript, in `frontend/`.
- Frontend package manager is npm.
- The frontend does not own the database or core business rules.
- The frontend talks to the backend through the REST API.
- The frontend may hide unavailable actions for usability. Frontend restrictions are never security controls.

**Proposed**

- A single-page application that authenticates users and calls Organization-scoped API endpoints.
- UI state for screens and forms lives in the client; authoritative data lives on the server.

**To Be Decided**

- React toolchain and project bootstrap.
- Routing, styling, and client-side state libraries.
- How the frontend stores and refreshes auth credentials in the browser.
- Whether any public, unauthenticated pages exist.

---

## 4. Backend Architecture

**Confirmed**

- Backend is Python Django with Django REST Framework, in `backend/`.
- Python dependencies are isolated with a virtual environment (`venv`).
- Django exposes the REST API and owns persistence via PostgreSQL.
- Backend queries and mutations that touch tenant-owned data must enforce Organization scoping.
- Authorization is always enforced server-side.

**Proposed**

- Layering: HTTP/API → business logic → data access → PostgreSQL.
- Django applications grouped by capability, not by industry.

**To Be Decided**

- Django project and app layout.
- Background job processing, if any.
- Caching, if any.

---

## 5. API Layer

**Confirmed**

- REST API.
- API base path: `/api/v1/`.
- JSON request and response format.
- OpenAPI documentation.
- Consistent API error responses.
- Server-side validation.
- Pagination and filtering conventions must be defined before the relevant APIs are implemented.

**Proposed**

- Resource-oriented URLs.
- The API never returns secrets or other Organizations’ data.

**To Be Decided**

- Pagination, filtering, and sorting conventions (define these before implementing the APIs that need them).
- Standard error JSON schema (responses must be consistent; the exact schema is not yet defined).
- OpenAPI generation tooling.
- CORS and allowed frontend origins.
- Rate limiting.

---

## 6. Database Layer

**Confirmed**

- Primary database is PostgreSQL.
- Shared PostgreSQL database with a shared schema.
- Organization represents a tenant.
- Tenant-owned records must have an explicit relationship to Organization.
- Database-level row-level security is not required for the initial implementation unless later justified.
- Design so the tenancy strategy can be strengthened later if required.

**Proposed**

- Django ORM as the default data-access layer.
- Migrations are the only supported schema-change path.
- Domain-neutral names for tables and fields (for example Organization, User, Role, Content).

**To Be Decided**

- Migration and backup procedures.
- Use of PostgreSQL-specific features beyond what Django requires.
- Production database hosting.

---

## 7. Multi-Tenancy Approach

**Confirmed**

- AEGIS is intended to become a multi-tenant SaaS platform.
- Shared PostgreSQL database with a shared schema.
- Organization represents a tenant.
- Tenant-owned records must have an explicit relationship to Organization.
- Backend queries and mutations must enforce Organization scoping.
- Cross-Organization access must be denied by default.
- Tenant isolation must never depend only on frontend behavior.
- Database-level row-level security is not required initially unless later justified.
- The tenancy strategy must be able to be strengthened later if required.
- A User may belong to multiple Organizations. Do not assume a User belongs to only one Organization.
- Membership between User and Organization is represented explicitly.
- A user’s permissions can differ between Organizations.
- The currently active Organization must be explicitly established for authenticated requests.

**To Be Decided**

- How the active Organization is established on each request (for example header, user preference, or another explicit mechanism).
- Platform-level (operator) users versus tenant users.
- Tenant provisioning and offboarding.

---

## 8. Authentication and Authorization

**Confirmed**

- Security First applies to identity and access.
- Secrets, tokens, and credentials must never be committed to the repository.
- Authentication is JWT-based initially and is handled by the Django backend.
- Access tokens must be short-lived.
- Refresh-token handling must follow secure practices.
- Authentication implementation details are finalized during backend setup.
- Authorization uses Role-Based Access Control (RBAC).
- Core concepts: User, Organization, Organization Membership, Role, Permission.
- Authorization must always be enforced server-side.
- The frontend may hide unavailable actions for usability; frontend restrictions are never security controls.

**To Be Decided**

- JWT issuance, storage, and refresh implementation details (finalized during backend setup).
- Password policy, lockout, and recovery.
- Single sign-on or external identity providers (none assumed).
- Invitation and user-provisioning flow.

---

## 9. Content and File Storage

**Confirmed**

- AEGIS governs and delivers enterprise knowledge; content is a first-class concern at the product level.
- During local development, files may use local storage.
- Production storage must be abstracted so it can use object storage without changing business logic.
- File metadata belongs in PostgreSQL.
- File access must respect Organization and Permission rules.
- Do not select a specific cloud storage vendor yet.

**To Be Decided**

- Production object-storage vendor.
- Content versioning model.
- Allowed file types, size limits, and scanning.
- Whether delivery is direct download, mediated by the API, or both.

---

## 10. Audit and Activity Tracking

**Confirmed**

- None beyond the general need for a production-quality, secure system.

**Proposed**

- Sensitive actions are recorded as Audit records (who, which Organization, what, when).
- Activity may record user-facing events separately from security audit, if both are required later.
- Audit data is tenant-scoped and is not editable through the normal product UI.

**To Be Decided**

- What must be audited in the first release.
- Retention and export.
- Whether Activity and Audit are one store or two.

---

## 11. Configuration and Environment Management

**Confirmed**

- Environment-specific values and secrets use environment variables.
- Secrets, credentials, API keys, tokens, and environment-specific sensitive data must not be committed.

**Proposed**

- Separate configuration for local development and production.
- Django `SECRET_KEY`, database connection, and similar values come from the environment.
- Frontend build-time public config (API base URL) is distinct from backend secrets.

**To Be Decided**

- Exact environment variable names and required set.
- How `.env` files are documented and loaded locally.
- Production secret-management provider.

---

## 12. Error Handling

**Confirmed**

- Features should include error handling.
- The API should not leak secrets or internal details to unauthorized clients.
- API error responses must be consistent.

**Proposed**

- Unexpected errors are logged on the server and returned as generic client messages plus a correlation identifier.
- Validation failures return structured field errors.
- Authorization failures return a generic forbidden or unauthorized response without extra data.

**To Be Decided**

- Standard error JSON schema.
- How the frontend presents errors and retries.

---

## 13. Logging

**Confirmed**

- Features should consider logging.
- Logs must not contain secrets or unnecessary personal data.

**Proposed**

- Use Django’s logging configuration.
- Log request identity at a coarse level (time, method, path, tenant, user id, status, duration).
- Distinguish operational logs from audit records.

**To Be Decided**

- Log format, levels, and retention.
- Where logs are written in production.
- Correlation of frontend errors with backend logs.
- Production monitoring provider.

---

## 14. Testing Strategy

**Confirmed**

- Backend tests use pytest.
- Frontend tests use Vitest and React Testing Library.
- API tests must cover authentication, authorization, validation, and Organization isolation.
- Tenant isolation is mandatory for relevant backend tests.
- Features should consider testing.

**Proposed**

- Backend: unit tests for business rules in addition to API tests.
- Frontend: tests for critical user flows once the UI exists.

**To Be Decided**

- Whether tests live only under `tests/` or also beside application code.
- Coverage expectations.
- How CI will run tests (CI platform is **To Be Decided**).

---

## 15. Development Environment

**Confirmed**

- Repository layout: `frontend/`, `backend/`, `docs/`, `tests/`.
- Frontend uses npm. Backend uses a Python virtual environment (`venv`).
- Use Docker Compose where practical for local infrastructure, especially PostgreSQL.
- Do not require Docker for the React or Django development processes unless there is a later reason to do so.
- Dependencies are not installed in this phase; React and Django projects are not initialized yet.

**Proposed**

- Developers run the Django API and the React app locally and point the frontend at the local API.
- Local secrets live in untracked environment files.

**To Be Decided**

- Python, Node, and PostgreSQL versions.
- Seed data for local Organizations and users.

---

## 16. Production Environment

**Confirmed**

- Production must follow Security First, environment-based secrets, and PostgreSQL as the primary database.
- Production file storage is abstracted so object storage can be used without changing business logic.
- No cloud provider, production hosting platform, production object-storage vendor, production secret-management provider, production monitoring provider, or production database host is selected.

**Proposed**

- Frontend is built as static assets and served separately from the Django process, or served by a production web server in front of Django.
- Django does not run with the development server in production.
- HTTPS is required.

**To Be Decided**

- Production hosting.
- Cloud provider.
- Process manager, reverse proxy, and TLS termination.
- Production database hosting and high availability.
- Production object-storage vendor.
- Production secret-management provider.
- Production monitoring provider.
- Backups and alerting.

---

## 17. High-Level Project Structure

**Confirmed** (current repository)

```
AEGIS/
├── frontend/          # React + TypeScript application (not initialized)
├── backend/           # Django + Django REST Framework (not initialized)
├── docs/              # Project documentation
├── tests/             # Tests
├── .cursor/rules/     # Cursor project rules
├── .gitignore
└── README.md
```

**Proposed**

- Keep this top-level split. Do not add new top-level application trees without an explicit decision.
- Internal folders inside `frontend/` and `backend/` are defined when those projects are created.

**To Be Decided**

- Exact Django app package names.
- Exact React source layout.
- Whether `tests/` remains the only test root or apps also contain tests.

---

## 18. Initial Architectural Decisions

These are in effect:

1. React with TypeScript frontend (npm) and Django with Django REST Framework backend (`venv`), separated by REST at `/api/v1/`.
2. JSON APIs, OpenAPI documentation, consistent error responses, and server-side validation.
3. PostgreSQL as the primary database; shared database and shared schema; Organization is the tenant.
4. Users may belong to multiple Organizations via explicit membership; permissions are Organization-scoped; the active Organization is explicit on authenticated requests.
5. JWT authentication (short-lived access tokens; secure refresh-token handling). Implementation details are finalized during backend setup.
6. Server-side RBAC using User, Organization, Organization Membership, Role, and Permission.
7. Local file storage in development; production storage abstracted for object storage; file metadata in PostgreSQL; file access follows Organization and Permission rules. No storage vendor selected.
8. pytest on the backend; Vitest and React Testing Library on the frontend; API tests cover authentication, authorization, validation, and Organization isolation.
9. Docker Compose for local infrastructure (especially PostgreSQL); React and Django are not required to run in Docker.
10. Security First: no secrets in source; environment-based configuration.
11. Industry-independent, domain-neutral language in architecture, schema, APIs, and UI.
12. Existing top-level folders stay as they are until an explicit structure change is requested.

---

## 19. Open Architectural Decisions

The items below still need decisions before the corresponding implementation. They are listed again, condensed, in **Open Decisions**.

---

### Confirmed Decisions

- Frontend: React with TypeScript
- Frontend package manager: npm
- Backend: Python Django with Django REST Framework
- Python dependency isolation: `venv`
- Database: PostgreSQL
- Architecture: REST API based frontend/backend separation
- API base path: `/api/v1/`
- JSON request and response format
- OpenAPI documentation
- Consistent API error responses
- Server-side validation
- Pagination and filtering conventions must be defined before the relevant APIs are implemented
- AEGIS is intended to become a multi-tenant SaaS platform
- Shared PostgreSQL database with a shared schema
- Organization represents a tenant
- Tenant-owned records have an explicit relationship to Organization
- Backend queries and mutations enforce Organization scoping
- Cross-Organization access is denied by default
- Tenant isolation must never depend only on frontend behavior
- Database-level row-level security is not required for the initial implementation unless later justified
- Tenancy strategy must be able to be strengthened later
- A User may belong to multiple Organizations
- Membership between User and Organization is represented explicitly
- A user’s permissions can differ between Organizations
- The currently active Organization must be explicitly established for authenticated requests
- Authentication: JWT, handled by the Django backend
- Access tokens are short-lived; refresh-token handling follows secure practices
- Tokens and secrets must never be committed
- Authentication implementation details are finalized during backend setup
- Authorization: server-side RBAC (User, Organization, Organization Membership, Role, Permission)
- Frontend may hide unavailable actions; that is not a security control
- Local development files may use local storage
- Production file storage is abstracted for object storage; no vendor selected
- File metadata belongs in PostgreSQL
- File access respects Organization and Permission rules
- Backend tests: pytest
- Frontend tests: Vitest and React Testing Library
- API tests cover authentication, authorization, validation, and Organization isolation
- Tenant isolation is mandatory for relevant backend tests
- Docker Compose where practical for local infrastructure, especially PostgreSQL
- Docker is not required for React or Django development processes unless later justified
- Security First is a core architectural principle
- AEGIS must remain industry-independent and domain-neutral

### Open Decisions

1. How the active Organization is established on each authenticated request.
2. JWT issuance, browser storage, and refresh implementation details (to be finalized during backend setup).
3. Password policy, recovery, invitations, and any external identity provider (none assumed).
4. Pagination, filtering, and sorting conventions (must be defined before the APIs that need them).
5. Exact API error JSON schema; OpenAPI generation tooling; CORS; rate limiting.
6. Django project/app layout and React source layout / bootstrap toolchain.
7. Content versioning, file-type limits, and file delivery method.
8. Audit versus Activity: what is recorded, storage, and retention.
9. Python, Node, and PostgreSQL versions; local seed data.
10. Whether tests live only in `tests/` or also beside application code; coverage and CI.
11. Background jobs and caching, if any.
12. Production hosting.
13. Cloud provider.
14. Production object-storage vendor.
15. Production secret-management provider.
16. Production monitoring provider.
17. Production database hosting.
18. Platform-level (operator) users versus tenant users; tenant provisioning and offboarding.
