# APPENDIX 2

# API RESOURCE AND TEST EVIDENCE

## B.1 API Resource Groups

| Resource group | Representative endpoints |
|---|---|
| Authentication | `/api/v1/auth/csrf/`, `/auth/login/`, `/auth/logout/`, `/auth/me/` |
| Users and roles | `/api/v1/users/`, `/users/{id}/`, `/roles/`, `/permissions/` |
| Content | `/api/v1/content/`, `/content/{id}/`, `/content/{id}/archive/` |
| Versions | `/content/{id}/versions/`, `/versions/{id}/`, publish and archive actions |
| Delivery | `/content/{id}/preview/`, `/content/{id}/access/`, delivery endpoints |
| Programs | `/api/v1/programs/`, assignments and activation/deactivation |
| Grants | `/api/v1/program-access-grants/`, revoke, and user access views |
| Accountability | `/activities/`, `/audits/`, `/security-events/` |
| Risk | `/risk-signals/`, `/risk-signals/summary/`, `/risk-investigations/` |
| Analytics/search | `/analytics/content/`, `/reports/access/`, `/assistant/query/` |

All IDs are UUID values. Most list endpoints support organization scope and pagination where implemented.

## B.2 Common API Result

Successful list APIs may return `data` and `meta` fields. A successful resource action returns the resource or relevant operation data. Errors use a consistent JSON structure containing an error code and message; validation details may identify fields.

Unsafe requests require the CSRF token in `X-CSRFToken`. The browser client sends the session cookie using credentials and obtains the CSRF token from the backend.

## B.3 Authentication Test Cases

| Case | Expected |
|---|---|
| Valid organization, email and password | 200 success and session |
| Unknown organization | Generic authentication failure |
| Wrong password | Generic authentication failure |
| Inactive user | Authentication denied |
| Repeated account failures | Account rate limit |
| Repeated source-IP failures | Source-IP rate limit |
| Unsafe request without CSRF | CSRF failure |
| Logout | Session ended |

## B.4 Authorization Test Cases

| Case | Expected |
|---|---|
| Missing permission | Permission denied by backend |
| Cross-tenant resource ID | Not found or tenant denied |
| Cross-tenant role assignment | Validation failure |
| Draft content delivery | Delivery denied |
| Archived content delivery | Delivery denied |
| Missing assignment | Delivery denied |
| Missing/revoked/expired grant | Delivery denied |
| Active grant and assignment | Delivery permitted |
| Preview permission | Separate privileged preview permitted |

## B.5 Delivery Test Cases

| Case | Expected |
|---|---|
| Valid PDF | Page PNG returned |
| Valid raster image | Page PNG returned |
| Invalid page number | Validation or not-found response |
| Unsupported MIME type | Delivery denied |
| Grant revoked after viewer open | Next page denied |
| Assignment removed after viewer open | Next page denied |
| No public source URL | Source bytes remain private |
| Watermark context | User and access context appear on page |

## B.6 Recorded Verification

The implementation status records:

- 174 backend tests passing against disposable PostgreSQL;
- 11 delivery tests passing;
- 43 delivery, analytics and risk tests passing;
- 23 frontend Vitest tests passing across two files;
- successful Vite production build;
- successful Django system check;
- no migration drift in recorded checks.

These results are evidence for the implemented repository state. They must not be represented as production penetration testing or genuine accepted browser screenshots.
