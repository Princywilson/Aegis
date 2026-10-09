# AEGIS — ENTERPRISE KNOWLEDGE PROTECTION AND DELIVERY PLATFORM

# PHASE 5 — API SPECIFICATION

**Document Status:** Baseline

**Phase:** Phase 5 — API Design

**Backend:** Python Django

**API Style:** RESTful HTTP API

**Primary Client:** Web Application

**Future Clients:** Mobile / Other Authorized Applications

---

# 1. Purpose

The API layer defines how AEGIS clients communicate with the backend system.

The API provides controlled access to:

- Authentication
- Organization management
- User management
- Role and permission management
- Content management
- Content versioning
- Training programs
- Content assignments
- Content Consumer access
- Secure content delivery
- Activity tracking
- Audit records
- Security events
- Analytics

The API is the primary application boundary between the frontend and backend.

```
┌─────────────────────┐
│      AEGIS UI       │
│   React / Web App   │
└──────────┬──────────┘
           │
           │ HTTPS / REST API
           ▼
┌─────────────────────┐
│     API Layer       │
│   Django Backend    │
└──────────┬──────────┘
           │
     ┌─────┼──────────┐
     ▼     ▼          ▼
  Domain  Database   Storage
  Logic   PostgreSQL Object Storage
```

---

# 2. API Design Principles

The AEGIS API follows these principles.

## 2.1 REST-oriented

Resources are represented using predictable resource-oriented URLs.

Example:

```
/api/v1/content
/api/v1/content/{content_id}
/api/v1/users/{user_id}
```

---

## 2.2 Versioned API

Future breaking changes can therefore be introduced through:

```
/api/v2/
```

without immediately breaking existing clients.

---

## 2.3 HTTPS Only

All production API communication must occur over HTTPS.

Sensitive authentication credentials, tokens and protected content information must never be transmitted over unencrypted HTTP.

---

## 2.4 Authentication and Authorization are Separate

Authentication answers:

> Who is this user?
> 

Authorization answers:

> What is this user allowed to do?
> 

Both must be enforced by the backend.

```
Request
   │
   ▼
Authentication
   │
   ▼
Organization Context
   │
   ▼
Permission Check
   │
   ▼
Business Rule Validation
   │
   ▼
Resource Operation
```

---

## 2.5 Tenant Isolation

Every organization-owned request must operate within the authenticated user's organization context.

A user from Organization A must never be able to access Organization B's:

- users
- content
- versions
- programs
- assignments
- access records
- activities
- audit records

This follows the established rule that Organization is the tenant boundary.

---

## 2.6 Server-Side Authorization

The frontend must never be considered the security boundary.

Every protected API endpoint must independently enforce authorization.

This follows the established AEGIS architecture decision that authorization must ultimately be enforced by the backend.

---

## 2.7 Controlled Content Delivery

The API must not expose unrestricted original content files merely because a user has permission to view them.

Protected content must be delivered through the AEGIS controlled delivery mechanism.

This directly supports the project's core objective of preventing unnecessary exposure of proprietary presentation files.

---

# 3. Base URL

The conceptual production API base URL is:

```
https://<aegis-domain>/api/v1/
```

During development:

```
http://localhost:<port>/api/v1/
```

The actual production domain is a deployment decision and is therefore not fixed in this document.

---

# 4. Authentication Model

Protected API requests use a Django session cookie. A bearer-token/JWT subsystem is not part of the MVP.

Unsafe requests must include the CSRF token obtained from `GET /api/v1/auth/csrf/` in the `X-CSRFToken` header. The API must not assume that an authenticated session alone grants access to organizational resources.

The request must also satisfy:

```
Authenticated
      +
Organization Membership
      +
Required Permission
      +
Resource Access
```

---

# 5. Standard HTTP Methods

| Method | Purpose |
| --- | --- |
| GET | Retrieve resource(s) |
| POST | Create resource / perform controlled action |
| PUT | Replace a resource where applicable |
| PATCH | Partially update resource |
| DELETE | Remove/deactivate resource where permitted |

For security-sensitive operations, action-oriented endpoints may be used where they communicate intent more clearly.

Example:

```
POST /content/{id}/publish
POST /access/{id}/revoke
```

---

# 6. Standard Response Structure

Successful responses should use a consistent JSON structure.

## Single Resource

```json
{
    "data": {
        "id": "content_123",
        "name": "Safety Induction"
    }
}
```

## Collection

```json
{
    "data": [
        {
            "id": "content_123",
            "name": "Safety Induction"
        },
        {
            "id": "content_124",
            "name": "Working at Height"
        }
    ],
    "meta": {
        "page": 1,
        "page_size": 20,
        "total": 2
    }
}
```

---

# 7. Standard Error Response

API errors should follow a consistent structure.

```json
{
    "error": {
        "code": "CONTENT_NOT_FOUND",
        "message": "The requested content was not found.",
        "details": {}
    }
}
```

For validation:

```json
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "One or more fields are invalid.",
        "details": {
            "name": [
                "This field is required."
            ]
        }
    }
}
```

The API must not expose internal stack traces, database errors, object-storage paths, security-sensitive information or implementation details to clients.

---

# 8. HTTP Status Codes

| Status | Meaning | Typical Usage |
| --- | --- | --- |
| 200 | OK | Successful GET/PATCH/action |
| 201 | Created | Successful POST creation |
| 202 | Accepted | Asynchronous operation where applicable |
| 204 | No Content | Successful deletion/deactivation |
| 400 | Bad Request | Invalid request |
| 401 | Unauthorized | Authentication missing/invalid |
| 403 | Forbidden | Authenticated but not authorized |
| 404 | Not Found | Resource does not exist / is not visible |
| 409 | Conflict | Business/state conflict |
| 422 | Unprocessable Entity | Semantic validation failure where used |
| 429 | Too Many Requests | Rate limiting |
| 500 | Internal Server Error | Unexpected server failure |

---

# 9. API Resource Groups

The AEGIS API is organized into the following functional areas:

```
/api/v1/auth/
/api/v1/organizations/
/api/v1/users/
/api/v1/roles/
/api/v1/permissions/
/api/v1/content/
/api/v1/training-programs/
/api/v1/assignments/
/api/v1/access/
/api/v1/activities/
/api/v1/audits/
/api/v1/security-events/
/api/v1/analytics/
```

---

# 10. Authentication APIs

Authentication is the entry point for protected AEGIS operations.

## 10.1 Login

```
POST /api/v1/auth/login/
```

### Purpose

Authenticate a user and establish a Django session.

### Authentication

None.

### Authorization

None.

### Request

```json
{
    "organization_slug": "example-organization",
    "email": "trainer@example.com",
    "password": "********"
}
```

### Response

```json
{
    "data": {
        "user": {
            "id": "user_123",
            "name": "Trainer One",
            "organization_id": "org_001"
        }
    }
}
```

On success, Django sets the `sessionid` cookie. It is HttpOnly, SameSite=Lax, and Secure when `DEBUG` is false. The session expires after 14 days. No access token is returned.

### Validation

- Organization slug required
- Email required
- Password required
- Credentials must be valid
- User must be eligible for authentication
- Invalid credentials, unknown organizations, and inactive accounts use a generic authentication failure response.

### Errors

```
AUTHENTICATION_FAILED
```

### Status Codes

```
200
400
401
403 (CSRF failure)
429 (generic authentication rate limit)
```

## 10.2 CSRF Token Bootstrap

```
GET /api/v1/auth/csrf/
```

This unauthenticated endpoint issues the Django CSRF cookie and returns the matching token for the browser client to send in the `X-CSRFToken` header on unsafe requests. The response must not be cached.

```json
{
    "data": {
        "csrf_token": "<csrf-token>"
    }
}
```

The CSRF token is not an authentication credential. A valid session and valid CSRF token are both required for authenticated unsafe requests.

## 10.3 Login Rate Limiting

Apply independent rolling 15-minute limits to the normalized organization-scoped account identifier and source IP. Five account failures or twenty source-IP failures cause a 15-minute temporary block. A successful login clears the account counter but leaves the IP counter intact.

Rate-limited login attempts return a generic response that does not reveal whether the organization or account exists. The limit state uses shared atomic PostgreSQL storage. Use the direct request source IP unless an explicitly trusted proxy is configured; never trust arbitrary forwarded-IP headers. Record a rate-limit trigger as a `LOGIN_FAILURE` Security Event with `MEDIUM` severity and sanitized metadata.

---

# 11. Logout

```
POST /api/v1/auth/logout
```

### Authentication

Required.

### Authorization

Authenticated user.

### Request

```json
{}
```

### Response

```json
{
    "data": {
        "message": "Logout successful."
    }
}
```

### Status

```
200
401
```

The logout/session termination event is recorded as a `LOGOUT` Security Event with `INFO` severity.

---

# 12. Current User

```
GET /api/v1/auth/me/
```

### Purpose

Retrieve the currently authenticated user's identity and authorization context.

### Authentication

Required.

### Authorization

Authenticated user.

### Response

```json
{
    "data": {
        "id": "user_123",
        "name": "Trainer One",
        "email": "trainer@example.com",
        "organization": {
            "id": "org_001",
            "name": "Example Organization"
        },
        "roles": [],
        "permissions": []
    }
}
```

The roles and permissions arrays remain empty until the RBAC milestone is implemented.

## Authentication Event Visibility

Authentication security events are generated by trusted backend workflows. Events with a resolved organization are tenant-scoped. Events created before organization resolution have null `organization_id` and are platform-scoped; they must never be assigned to a default tenant.

Organization-level security-event queries must be constrained to the authenticated user's organization and must not expose platform-level or other-organization events. Platform-level events are available only to authorized platform-level monitoring. The API must not expose whether an organization, account, or password was valid through authentication responses.

### Status

```
200
401
```

---

# 13. Organization APIs

Organization is the tenant boundary of AEGIS.

## 13.1 Get Organization

```
GET /api/v1/organizations/{organization_id}
```

### Authentication

Required.

### Authorization

Organization-level permission required.

### Validation

The organization must belong to the authenticated user's organization context.

### Response

```json
{
    "data": {
        "id": "org_001",
        "name": "Example Organization",
        "status": "active"
    }
}
```

### Errors

```
ORGANIZATION_NOT_FOUND
FORBIDDEN
```

---

## 13.2 Update Organization

```
PATCH /api/v1/organizations/{organization_id}
```

### Authentication

Required.

### Authorization

Organization administration permission.

### Request

```json
{
    "name": "Updated Organization Name"
}
```

### Status

```
200
400
401
403
404
409
```

---

# 14. User APIs

## 14.1 List Users

```
GET /api/v1/users
```

### Authentication

Required.

### Authorization

`users.view`

### Query Parameters

```
?page=1
&page_size=20
&role=content_consumer
&status=active
&search=John
```

### Response

```json
{
    "data": [
        {
            "id": "user_001",
            "name": "John",
            "email": "john@example.com",
            "status": "active",
            "roles": [
                "Content Consumer"
            ]
        }
    ],
    "meta": {
        "page": 1,
        "page_size": 20,
        "total": 1
    }
}
```

### Status

```
200
401
403
```

---

# 15. Create User

```
POST /api/v1/users
```

### Authentication

Required.

### Authorization

`users.create`

### Request

```json
{
    "name": "John Trainer",
    "email": "john@example.com",
    "role_ids": [
        "role_content_consumer"
    ]
}
```

### Validation

- Name required
- Valid email
- Email uniqueness according to user/organization rules
- Organization context must be valid
- Requested roles must be assignable by the actor

### Response

```json
{
    "data": {
        "id": "user_001",
        "name": "John Trainer",
        "email": "john@example.com",
        "status": "active",
        "roles": [
            "Content Consumer"
        ]
    }
}
```

### Status

```
201
400
401
403
409
```

---

# 16. Get User

```
GET /api/v1/users/{user_id}
```

### Authentication

Required.

### Authorization

`users.view`

### Response

```json
{
    "data": {
        "id": "user_001",
        "name": "John Trainer",
        "email": "john@example.com",
        "status": "active",
        "roles": [
            "Content Consumer"
        ]
    }
}
```

---

# 17. Update User

```
PATCH /api/v1/users/{user_id}
```

### Authentication

Required.

### Authorization

`users.manage`

### Request

```json
{
    "name": "John Updated",
    "status": "inactive"
}
```

### Status

```
200
400
401
403
404
409
```

Important security-sensitive changes should generate audit records.

---

# 18. Role APIs

## 18.1 List Roles

```
GET /api/v1/roles
```

### Authentication

Required.

### Authorization

`roles.view`

### Response

```json
{
    "data": [
        {
            "id": "role_admin",
            "name": "Administrator"
        },
        {
            "id": "role_content_consumer",
            "name": "Content Consumer"
        }
    ]
}
```

---

# 19. Permission APIs

## 19.1 List Permissions

```
GET /api/v1/permissions
```

### Authentication

Required.

### Authorization

Administrative permission.

### Response

```json
{
    "data": [
        {
            "code": "content.view",
            "name": "View Content"
        },
        {
            "code": "content.manage",
            "name": "Manage Content"
        }
    ]
}
```

The exact permission matrix is determined by the functional/security design.

---

# 20. Content APIs

Content is one of the central resources of AEGIS.

## 20.1 List Content

```
GET /api/v1/content
```

### Authentication

Required.

### Authorization

Depends on the requested operation and user's permissions/access.

### Query Parameters

```
?page=1
&page_size=20
&status=published
&search=induction
&program_id=program_001
```

### Response

```json
{
    "data": [
        {
            "id": "content_001",
            "name": "Safety Induction",
            "status": "published",
            "current_version": {
                "id": "version_003",
                "version_number": 3
            }
        }
    ],
    "meta": {
        "page": 1,
        "page_size": 20,
        "total": 1
    }
}
```

---

# 21. Create Content

```
POST /api/v1/content
```

### Authentication

Required.

### Authorization

`content.create`

### Request

```json
{
    "name": "Safety Induction",
    "description": "General safety induction training content"
}
```

If content creation includes an initial file/version, the API may use a dedicated upload workflow rather than embedding large file data directly in the JSON request.

### Validation

- Name required
- Organization determined from authenticated context
- User must have content-creation permission
- Content metadata must satisfy domain rules

### Response

```json
{
    "data": {
        "id": "content_001",
        "name": "Safety Induction",
        "status": "draft"
    }
}
```

### Status

```
201
400
401
403
409
```

---

# 22. Get Content

```
GET /api/v1/content/{content_id}
```

### Authentication

Required.

### Authorization

Must satisfy both:

```
Permission
+
Content Access
```

### Response

```json
{
    "data": {
        "id": "content_001",
        "name": "Safety Induction",
        "description": "General safety induction training content",
        "status": "published",
        "current_version": {
            "id": "version_003",
            "version_number": 3,
            "status": "published"
        }
    }
}
```

---

# 23. Update Content

```
PATCH /api/v1/content/{content_id}
```

### Authentication

Required.

### Authorization

`content.manage`

### Request

```json
{
    "name": "Updated Safety Induction",
    "description": "Updated description"
}
```

### Important Rule

Updating metadata is different from modifying a published content file.

A published content version must not be silently overwritten.

A content-file modification creates a new version.

### Status

```
200
400
401
403
404
409
```

---

# 24. Archive Content

```
POST /api/v1/content/{content_id}/archive
```

### Authentication

Required.

### Authorization

`content.archive`

### Request

```json
{}
```

### Response

```json
{
    "data": {
        "id": "content_001",
        "status": "archived"
    }
}
```

### Status

```
200
401
403
404
409
```

The operation must generate an audit record.

---

# 25. Content Version APIs

Content and Content Version remain separate domain concepts.

```
Content
   │
   ├── Version 1
   ├── Version 2
   └── Version 3 ← Current
```

Historical versions must not be silently overwritten.

---

# 26. List Content Versions

```
GET /api/v1/content/{content_id}/versions
```

### Authentication

Required.

### Authorization

Must satisfy appropriate content/version access.

### Response

```json
{
    "data": [
        {
            "id": "version_001",
            "version_number": 1,
            "status": "archived"
        },
        {
            "id": "version_002",
            "version_number": 2,
            "status": "archived"
        },
        {
            "id": "version_003",
            "version_number": 3,
            "status": "published"
        }
    ]
}
```

---

# 27. Create Content Version

```
POST /api/v1/content/{content_id}/versions
```

### Authentication

Required.

### Authorization

`content.version.create`

### Request

Conceptually:

```json
{
    "version_notes": "Updated induction material",
    "file": "<uploaded-file>"
}
```

The actual upload mechanism may use multipart upload or a controlled upload workflow.

### Validation

- Content must exist
- Actor must have permission
- New version must follow content lifecycle rules
- Published historical versions must remain immutable
- File must satisfy supported-content/security validation

### Response

```json
{
    "data": {
        "id": "version_004",
        "content_id": "content_001",
        "version_number": 4,
        "status": "draft"
    }
}
```

### Status

```
201
400
401
403
404
409
```

---

# 28. Get Content Version

```
GET /api/v1/content/{content_id}/versions/{version_id}
```

### Authentication

Required.

### Authorization

Appropriate content/version permission or access.

### Response

```json
{
    "data": {
        "id": "version_003",
        "content_id": "content_001",
        "version_number": 3,
        "status": "published",
        "created_at": "<datetime>"
    }
}
```

The response must not expose unrestricted storage locations for protected content.

---

# 29. Publish Content Version

```
POST /api/v1/content/{content_id}/versions/{version_id}/publish
```

### Authentication

Required.

### Authorization

`content.version.publish`

### Request

```json
{}
```

### Validation

- Version exists
- Version belongs to content
- Content belongs to user's organization
- Version is in a publishable state
- Actor has publishing permission

### Response

```json
{
    "data": {
        "id": "version_003",
        "status": "published"
    }
}
```

Publishing must generate an audit record.

---

# 30. Archive Content Version

```
POST /api/v1/content/{content_id}/versions/{version_id}/archive
```

### Authentication

Required.

### Authorization

`content.version.archive`

### Status

```
200
400
401
403
404
409
```

Historical records must remain identifiable even after archival.

---

# 31. Training Program APIs

## 31.1 List Training Programs

```
GET /api/v1/training-programs
```

### Authentication

Required.

### Authorization

Based on organization membership and applicable permissions.

### Response

```json
{
    "data": [
        {
            "id": "program_001",
            "name": "Safety Induction",
            "status": "active"
        }
    ]
}
```

---

# 32. Create Training Program

```
POST /api/v1/training-programs
```

### Authentication

Required.

### Authorization

`program.create`

### Request

```json
{
    "name": "Safety Induction",
    "description": "General safety induction program"
}
```

### Response

```json
{
    "data": {
        "id": "program_001",
        "name": "Safety Induction",
        "status": "active"
    }
}
```

### Status

```
201
400
401
403
409
```

---

# 33. Get Training Program

```
GET /api/v1/training-programs/{program_id}
```

### Authentication

Required.

### Authorization

Organization membership plus applicable permission/access.

### Response

```json
{
    "data": {
        "id": "program_001",
        "name": "Safety Induction",
        "status": "active"
    }
}
```

---

# 34. Update Training Program

```
PATCH /api/v1/training-programs/{program_id}
```

### Authentication

Required.

### Authorization

`program.manage`

### Request

```json
{
    "name": "Updated Safety Induction"
}
```

---

# 35. Content Assignment APIs

Content Assignment represents the relationship between Training Programs and Content.

## 35.1 List Program Content

```
GET /api/v1/training-programs/{program_id}/content
```

### Authentication

Required.

### Authorization

Program/content access.

### Response

```json
{
    "data": [
        {
            "content_id": "content_001",
            "name": "Safety Induction",
            "status": "published"
        }
    ]
}
```

---

# 36. Assign Content to Program

```
POST /api/v1/training-programs/{program_id}/content
```

### Authentication

Required.

### Authorization

`program.content.manage`

### Request

```json
{
    "content_id": "content_001"
}
```

### Validation

- Program exists
- Content exists
- Both belong to same organization
- Actor has permission
- Duplicate assignment is prevented

### Response

```json
{
    "data": {
        "program_id": "program_001",
        "content_id": "content_001"
    }
}
```

### Status

```
201
400
401
403
404
409
```

---

# 37. Remove Content Assignment

```
DELETE /api/v1/training-programs/{program_id}/content/{content_id}
```

### Authentication

Required.

### Authorization

`program.content.manage`

### Status

```
204
401
403
404
409
```

The operation must not accidentally delete the Content itself.

It only removes the program-content relationship.

---

# 38. Training Access APIs

Training Access represents authorization for a user to access protected training resources.

This must remain separate from actual Content Access.

```
Authorization:
"Content Consumer A may access Content X."

Actual Access:
"Content Consumer A accessed Content X."
```

This distinction is established in the domain model.

---

# 39. Grant Training Access

```
POST /api/v1/access
```

### Authentication

Required.

### Authorization

`access.grant`

### Request

```json
{
    "user_id": "user_001",
    "program_id": "program_001"
}
```

Depending on the finalized access model, content-specific authorization may also be represented explicitly.

### Validation

- User exists
- User belongs to same organization
- Program belongs to same organization
- Actor has permission
- Required business conditions are satisfied

### Response

```json
{
    "data": {
        "id": "access_001",
        "user_id": "user_001",
        "program_id": "program_001",
        "status": "active"
    }
}
```

### Status

```
201
400
401
403
404
409
```

---

# 40. Revoke Training Access

```
POST /api/v1/access/{access_id}/revoke
```

### Authentication

Required.

### Authorization

`access.revoke`

### Response

```json
{
    "data": {
        "id": "access_001",
        "status": "revoked"
    }
}
```

After revocation, the user must not be allowed to initiate new protected access.

---

# 41. List User Access

```
GET /api/v1/users/{user_id}/access
```

### Authentication

Required.

### Authorization

Appropriate access-management permission.

### Response

```json
{
    "data": [
        {
            "id": "access_001",
            "program_id": "program_001",
            "status": "active"
        }
    ]
}
```

---

# 42. Secure Content Delivery APIs

This is one of the most security-sensitive API areas in AEGIS.

The API must not simply return:

```
original_file_url
```

to an authorized Content Consumer.

Instead, the backend controls the delivery process.

---

# 43. Start Content Access

```
POST /api/v1/content/{content_id}/access
```

### Authentication

Required.

### Authorization

The backend evaluates:

```
User authenticated
        ↓
Organization valid
        ↓
Permission valid
        ↓
Training Access valid
        ↓
Content assignment valid
        ↓
Content/version available
```

### Request

```json
{
    "program_id": "program_001"
}
```

### Response

Conceptually:

```json
{
    "data": {
        "access_id": "access_session_001",
        "content_id": "content_001",
        "version_id": "version_003",
        "delivery_token": "<short-lived-token>",
        "expires_at": "<datetime>"
    }
}
```

The exact delivery-token mechanism is a System Design implementation decision.

### Security

The response must not expose unrestricted object-storage credentials or permanent file URLs.

---

# 44. Content Delivery

```
GET /api/v1/content/{content_id}/delivery
```

or an equivalent controlled streaming endpoint.

### Authentication

Required.

### Authorization

The backend validates the active content-access context.

### Processing

Conceptually:

```
Request
   ↓
Authenticate
   ↓
Authorize
   ↓
Validate Access
   ↓
Identify Version
   ↓
Prepare Protected Delivery
   ↓
Apply Dynamic Watermark
   ↓
Deliver Content
   ↓
Record Activity
```

The exact streaming/rendering mechanism belongs to System Design.

The API specification defines the security contract rather than the internal implementation.

---

# 45. Content Access History

```
GET /api/v1/content/{content_id}/access
```

### Authentication

Required.

### Authorization

Appropriate activity/audit permission.

### Response

```json
{
    "data": [
        {
            "user_id": "user_001",
            "version_id": "version_003",
            "accessed_at": "<datetime>",
            "status": "completed"
        }
    ]
}
```

Sensitive access information must only be visible to appropriately authorized users.

---

# 46. Activity APIs

Activity records represent observable interactions with AEGIS.

Examples include:

- Content viewed
- Training material opened
- Content accessed
- Access attempts
- Content Consumer interactions

The project proposal explicitly identifies access logging and Content Consumer activity tracking as core capabilities.

---

# 47. Record Activity

```
POST /api/v1/activities
```

### Authentication

Required unless the event is generated internally by the backend.

### Authorization

The user may create only activities representing permitted operations.

The API must not allow clients to arbitrarily fabricate privileged audit history.

### Request

```json
{
    "type": "content_view",
    "resource_id": "content_001",
    "context_id": "access_session_001"
}
```

### Response

```json
{
    "data": {
        "id": "activity_001",
        "type": "content_view",
        "created_at": "<datetime>"
    }
}
```

---

# 48. View Activity

```
GET /api/v1/activities
```

### Authentication

Required.

### Authorization

`activity.view`

### Query Parameters

```
?user_id=user_001
&content_id=content_001
&from=<datetime>
&to=<datetime>
&type=content_view
```

### Response

```json
{
    "data": [
        {
            "id": "activity_001",
            "user_id": "user_001",
            "type": "content_view",
            "resource_id": "content_001",
            "created_at": "<datetime>"
        }
    ]
}
```

---

# 49. Audit APIs

Audit is distinct from normal activity.

Audit answers:

> What important business/security event occurred, who caused it, and when?
> 

---

# 50. List Audit Records

```
GET /api/v1/audits
```

### Authentication

Required.

### Authorization

`audit.view`

### Query Parameters

```
?actor_id=user_001
&action=content.publish
&resource_type=content
&resource_id=content_001
&from=<datetime>
&to=<datetime>
```

### Response

```json
{
    "data": [
        {
            "id": "audit_001",
            "actor_id": "user_001",
            "action": "content.publish",
            "resource_type": "content_version",
            "resource_id": "version_003",
            "created_at": "<datetime>"
        }
    ]
}
```

Audit records are historical records and should not be silently rewritten by ordinary application operations.

---

# 51. Security Event APIs

Security events represent security-sensitive occurrences.

Examples:

```
Unauthorized access attempt
Access denied
Authentication failure
Suspicious activity
Security-related event
```

---

# 52. View Security Events

```
GET /api/v1/security-events
```

### Authentication

Required.

### Authorization

Security/audit permission.

### Query Parameters

```
?severity=high
&type=unauthorized_access
&from=<datetime>
&to=<datetime>
```

### Response

```json
{
    "data": [
        {
            "id": "event_001",
            "type": "unauthorized_access",
            "severity": "high",
            "created_at": "<datetime>"
        }
    ]
}
```

Security information must be restricted to authorized users.

---

# 53. Analytics APIs

Analytics are derived primarily from activity, access and audit information.

## 53.1 Content Analytics

```
GET /api/v1/analytics/content
```

### Authentication

Required.

### Authorization

`analytics.view`

### Query Parameters

```
?content_id=content_001
&from=<datetime>
&to=<datetime>
```

### Response

```json
{
    "data": {
        "total_accesses": 125,
        "unique_users": 32,
        "most_accessed_version": 3
    }
}
```

The exact analytics metrics are subject to the finalized functional architecture.

---

# 54. Content Consumer Activity Analytics

```
GET /api/v1/analytics/trainers
```

### Authentication

Required.

### Authorization

`analytics.trainer.view`

### Response

```json
{
    "data": {
        "total_trainers": 20,
        "active_trainers": 17,
        "content_accesses": 842
    }
}
```

Advanced AI-based Content Consumer performance analysis remains future scope rather than an MVP API dependency. The project proposal identifies AI-based Content Consumer performance analytics as a future enhancement.

The aggregate response above is outside the Content Consumer's approved analytics scope. The legacy permission identifier and endpoint must not be assigned to this role unless the completed permission matrix explicitly permits an appropriately scoped response.

---

# 55. API Authorization Matrix

A simplified conceptual authorization matrix is:

| API Area | Administrator | Content Consumer |
| --- | --- | --- |
| Login | ✓ | ✓ |
| Own Profile | ✓ | ✓ |
| Organization Management | ✓ | — |
| User Management | ✓ | — |
| Role Management | ✓ | — |
| Permission Management | ✓ | — |
| Create Content | ✓ | — |
| Manage Content | ✓ | — |
| Create Version | ✓ | — |
| Publish Version | ✓ | — |
| Training Program Management | ✓ | — |
| Content Assignment | ✓ | — |
| Grant Access | ✓ | — |
| Revoke Access | ✓ | — |
| Access Authorized Content | ✓* | ✓ |
| Content Delivery | ✓* | ✓ |
| View Activity | ✓ | Limited/own |
| View Audit | ✓ | — |
| View Security Events | ✓ | — |
| Analytics | ✓ | Limited |
- Subject to the actual permission/access model.

This matrix is a high-level API authorization baseline; the detailed permission matrix belongs to the security/functional design. For the Content Consumer role, limited activity/report access is restricted to the user's own activity and reports for content/programs assigned to that user.

---

# 56. Organization Isolation at API Level

Every organization-scoped API must enforce:

```
Authenticated User
       │
       ▼
User Organization
       │
       ▼
Requested Resource Organization
       │
       ▼
      MATCH
       │
   ┌───┴───┐
   │       │
  YES      NO
   │       │
 Allow    Deny
```

A request such as:

```
GET /api/v1/content/content_from_other_org
```

must not reveal whether the resource exists if the caller is not authorized to know about it.

Depending on the security design, the system may return:

```
404 Not Found
```

instead of exposing a cross-tenant authorization distinction.

---

# 57. API Validation Layers

Validation occurs at multiple levels.

## Layer 1 — Request Validation

Examples:

- Required fields
- Data types
- Formats
- Maximum lengths

## Layer 2 — Authentication

```
Is the requester authenticated?
```

## Layer 3 — Tenant Validation

```
Does the resource belong to the user's organization?
```

## Layer 4 — Authorization

```
Does the actor have the required permission?
```

## Layer 5 — Domain Validation

```
Is this operation valid according to AEGIS business rules?
```

## Layer 6 — State Validation

```
Can this operation occur in the resource's current state?
```

Example:

```
Archived Version
      ↓
Publish?
      ↓
Business Rule Check
      ↓
Reject if invalid
```

---

# 58. Error Categories

The API should use stable machine-readable error codes.

Examples:

```
AUTHENTICATION_REQUIRED
INVALID_CREDENTIALS
FORBIDDEN
RESOURCE_NOT_FOUND
ORGANIZATION_MISMATCH
VALIDATION_ERROR
DUPLICATE_RESOURCE
INVALID_STATE
ACCESS_DENIED
ACCESS_REVOKED
VERSION_NOT_PUBLISHABLE
VERSION_IMMUTABLE
CONTENT_ARCHIVED
INVALID_PROGRAM
AUDIT_ACCESS_DENIED
RATE_LIMIT_EXCEEDED
INTERNAL_ERROR
```

The `code` should remain more stable than the human-readable `message`.

---

# 59. Pagination

Collection endpoints should support pagination.

Example:

```
GET /api/v1/content?page=2&page_size=20
```

Response:

```json
{
    "data": [],
    "meta": {
        "page": 2,
        "page_size": 20,
        "total": 150,
        "total_pages": 8
    }
}
```

Large collections such as:

- users
- content
- activity
- audit records
- security events

must not return unrestricted datasets by default.

---

# 60. Filtering and Searching

Collection APIs should support controlled filtering.

Example:

```
GET /api/v1/content?status=published
```

```
GET /api/v1/users?role=content_consumer&status=active
```

```
GET /api/v1/audits?action=content.publish
```

Filtering must itself respect authorization and tenant isolation.

---

# 61. Idempotency

Operations that may be retried by clients should be designed to avoid accidental duplicate business operations where appropriate.

For example:

```
POST /api/v1/training-programs/{id}/content
```

must not create duplicate Content Assignments.

Similarly, access-grant operations must prevent duplicate active grants where the domain rules prohibit them.

---

# 62. Concurrency and State Conflicts

The API must handle concurrent operations safely.

Example:

```
Administrator A
      │
      └── publishes Version 3

Administrator B
      │
      └── simultaneously publishes Version 4
```

The backend must enforce the business rule governing the current published version rather than relying on frontend state.

Conflicting operations should return an appropriate error such as:

```
409 Conflict
```

when applicable.

---

# 63. File Upload Security

Content-upload APIs must validate uploaded files before accepting them into the protected content lifecycle.

Validation may include:

- Supported file type
- File size
- File integrity
- Malicious-file detection
- Organization ownership
- Upload authorization
- Version lifecycle

The API must not trust a client-provided MIME type or filename as the sole security validation.

The exact file-security implementation belongs to System Design.

---

# 64. Protected File Storage Boundary

The API must maintain the boundary:

```
Client
   │
   ▼
AEGIS API
   │
   ▼
Authorization
   │
   ▼
Controlled Content Delivery
   │
   ▼
Object Storage
```

Not:

```
Client
   │
   └──────────────► Public Object Storage URL
```

This is consistent with the established decision that protected content should not be directly exposed through unrestricted storage URLs.

---

# 65. Dynamic Watermarking

When protected content is delivered, the delivery mechanism may apply a dynamic watermark based on the authorized access context.

Conceptually:

```
Authenticated User
       │
       ▼
Content Access
       │
       ▼
Content Version
       │
       ▼
Dynamic Watermark
       │
       ▼
Protected Delivery
```

The watermark may associate the displayed material with the relevant user/session/access context.

The exact watermark fields and rendering mechanism remain implementation-level decisions.

Dynamic watermarking is part of the proposed AEGIS protection mechanism, while advanced DRM remains future scope.

---

# 66. Activity and Audit Generation

Not every activity should necessarily require a client-generated audit request.

For security-sensitive operations, the backend should generate the authoritative audit record.

Example:

```
POST /content/{id}/versions/{version_id}/publish
             │
             ▼
       Business Operation
             │
       ┌─────┴─────┐
       ▼           ▼
 Content State   Audit Record
   Updated        Created
```

This prevents clients from being able to manipulate the authoritative audit trail.

---

# 67. API Request Lifecycle

Every protected API request follows the conceptual flow:

```
HTTP Request
     │
     ▼
API Router
     │
     ▼
Authentication
     │
     ▼
Organization Context
     │
     ▼
Permission Check
     │
     ▼
Input Validation
     │
     ▼
Domain / Business Rules
     │
     ▼
Service / Application Logic
     │
     ▼
Database / Storage
     │
     ▼
Activity / Audit
     │
     ▼
Response
```

---

# 68. Example End-to-End Content Flow

A Content Consumer opens a training program.

```
GET /api/v1/training-programs/{id}
```

The backend validates:

```
Authentication
      ↓
Organization
      ↓
Training Access
      ↓
Program Access
```

The Content Consumer selects protected content.

```
POST /api/v1/content/{id}/access
```

The backend validates:

```
Authentication
      ↓
Organization
      ↓
Permission
      ↓
Training Access
      ↓
Content Assignment
      ↓
Current Published Version
```

The backend creates an access context.

```
Access Session
      ↓
Protected Delivery
      ↓
Dynamic Watermark
      ↓
Content Presented
```

AEGIS records:

```
Content Access
Activity
Audit / Security Event where applicable
```

This provides the central AEGIS flow:

```
Authorized Content Consumer
       ↓
Training Program
       ↓
Content
       ↓
Current Version
       ↓
Controlled Access
       ↓
Protected Delivery
       ↓
Activity / Audit
```

---

# 69. API Security Requirements

The API must:

- Require authentication for protected endpoints.
- Enforce authorization server-side.
- Enforce organization isolation.
- Validate all input.
- Avoid exposing internal implementation details.
- Avoid exposing unrestricted protected-file URLs.
- Protect authentication credentials/tokens.
- Apply rate limiting where appropriate.
- Record security-sensitive operations.
- Prevent unauthorized modification of audit history.
- Prevent access to revoked resources.
- Validate resource ownership/tenant context.
- Avoid leaking cross-tenant resource existence.
- Use HTTPS in production.

---

# 70. APIs That Must Not Be Exposed Directly

Internal implementation details should not automatically become public APIs.

For example, AEGIS should not expose endpoints such as:

```
/database/query
/storage/raw-file
/internal/object/{id}
```

The API should expose business capabilities rather than internal infrastructure.

---

# 71. API-to-Domain Mapping

| Domain Concept | Primary API |
| --- | --- |
| Organization | `/organizations` |
| User | `/users` |
| Role | `/roles` |
| Permission | `/permissions` |
| Content | `/content` |
| Content Version | `/content/{id}/versions` |
| Training Program | `/training-programs` |
| Content Assignment | `/training-programs/{id}/content` |
| Training Access | `/access` |
| Content Access | `/content/{id}/access` |
| Activity | `/activities` |
| Audit | `/audits` |
| Security Event | `/security-events` |
| Analytics | `/analytics` |
| Authentication Session | `/auth/*` |
| Watermark | Internal protected-delivery capability |

This preserves the domain distinctions established earlier.

---

# 72. Initial API Endpoint Register

| # | Method | Endpoint | Purpose |
| --- | --- | --- | --- |
| 1 | POST | `/auth/login` | Authenticate |
| 2 | POST | `/auth/logout` | End session |
| 3 | GET | `/auth/me` | Current user |
| 4 | GET | `/organizations/{id}` | View organization |
| 5 | PATCH | `/organizations/{id}` | Update organization |
| 6 | GET | `/users` | List users |
| 7 | POST | `/users` | Create user |
| 8 | GET | `/users/{id}` | Get user |
| 9 | PATCH | `/users/{id}` | Update user |
| 10 | GET | `/users/{id}/access` | User access |
| 11 | GET | `/roles` | List roles |
| 12 | GET | `/permissions` | List permissions |
| 13 | GET | `/content` | List content |
| 14 | POST | `/content` | Create content |
| 15 | GET | `/content/{id}` | Get content |
| 16 | PATCH | `/content/{id}` | Update content |
| 17 | POST | `/content/{id}/archive` | Archive content |
| 18 | GET | `/content/{id}/versions` | List versions |
| 19 | POST | `/content/{id}/versions` | Create version |
| 20 | GET | `/content/{id}/versions/{version_id}` | Get version |
| 21 | POST | `/content/{id}/versions/{version_id}/publish` | Publish version |
| 22 | POST | `/content/{id}/versions/{version_id}/archive` | Archive version |
| 23 | GET | `/training-programs` | List programs |
| 24 | POST | `/training-programs` | Create program |
| 25 | GET | `/training-programs/{id}` | Get program |
| 26 | PATCH | `/training-programs/{id}` | Update program |
| 27 | GET | `/training-programs/{id}/content` | List assigned content |
| 28 | POST | `/training-programs/{id}/content` | Assign content |
| 29 | DELETE | `/training-programs/{id}/content/{content_id}` | Remove assignment |
| 30 | POST | `/access` | Grant access |
| 31 | POST | `/access/{id}/revoke` | Revoke access |
| 32 | POST | `/content/{id}/access` | Start content access |
| 33 | GET | `/content/{id}/delivery` | Controlled delivery |
| 34 | GET | `/content/{id}/access` | Access history |
| 35 | GET | `/activities` | Activity history |
| 36 | POST | `/activities` | Record activity where applicable |
| 37 | GET | `/audits` | Audit history |
| 38 | GET | `/security-events` | Security events |
| 39 | GET | `/analytics/content` | Content analytics |
| 40 | GET | `/analytics/trainers` | Content Consumer analytics |

---

# 73. API Design Boundary

Phase 5 defines:

```
What endpoint exists?
What HTTP method is used?
Who can call it?
What does it accept?
What does it return?
What validation applies?
What errors can occur?
What status codes are returned?
```

It does **not** yet define every implementation detail such as:

- Django view implementation
- Serializer classes
- URL routing code
- Service classes
- PostgreSQL queries
- Object-storage SDK code
- React API client code
- Deployment configuration

Those belong to implementation/design activities associated with later development.

---

# 74. Relationship Between Phase 5 and Phase 6

The API design now provides the contract that the UI can consume.

```
PHASE 5 — API
      │
      │ API Contract
      ▼
PHASE 6 — UI/UX
      │
      │ Screens + interactions
      ▼
PHASE 7 — DEVELOPMENT
```

For example:

```
Login Screen
     │
     ▼
POST /api/v1/auth/login
```

```
Content Management Screen
     │
     ├── GET  /api/v1/content
     ├── POST /api/v1/content
     ├── PATCH /api/v1/content/{id}
     └── POST /api/v1/content/{id}/archive
```

```
Content Consumer Content Viewer
     │
     ├── POST /api/v1/content/{id}/access
     └── GET  /api/v1/content/{id}/delivery
```

---

# 75. Final API Architecture

The complete conceptual API architecture is:

```
                         AEGIS CLIENTS
                              │
                 ┌────────────┴────────────┐
                 │                         │
              Web App                 Future Clients
                 │                         │
                 └────────────┬────────────┘
                              │
                           HTTPS
                              │
                              ▼
                    ┌──────────────────┐
                    │    REST API      │
                    │    /api/v1/      │
                    └────────┬─────────┘
                             │
          ┌──────────────────┼───────────────────┐
          │                  │                   │
          ▼                  ▼                   ▼
   Authentication      Authorization        Validation
          │                  │                   │
          └──────────────────┼───────────────────┘
                             │
                             ▼
                    Application / Domain
                         Services
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
          PostgreSQL    Object Storage   Audit/Activity
              │              │              │
              └──────────────┼──────────────┘
                             ▼
                    Protected Response
```

---

# 76. Phase 5 Completion Criteria

Phase 5 can be considered complete when:

- [x]  API architecture is defined
- [x]  API versioning strategy is defined
- [x]  Authentication boundary is defined
- [x]  Authorization boundary is defined
- [x]  Tenant isolation is defined
- [x]  Core resource endpoints are identified
- [x]  Content APIs are defined
- [x]  Content version APIs are defined
- [x]  Training program APIs are defined
- [x]  Content assignment APIs are defined
- [x]  Training access APIs are defined
- [x]  Secure content delivery APIs are defined
- [x]  Activity APIs are defined
- [x]  Audit APIs are defined
- [x]  Security-event APIs are defined
- [x]  Analytics APIs are defined
- [x]  Request/response structures are established
- [x]  Validation responsibilities are established
- [x]  Error structure is established
- [x]  HTTP status-code conventions are established
- [x]  API authorization matrix is established
- [x]  Protected content delivery boundary is established
- [x]  Future-client compatibility is considered

---

# 77. Final Phase 5 Decision

The AEGIS API will use a **versioned REST API** as the communication contract between clients and the Django backend.

The fundamental security flow is:

```
Client
  ↓
HTTPS
  ↓
Authentication
  ↓
Organization Context
  ↓
Authorization
  ↓
Business Rules
  ↓
Domain Operation
  ↓
Database / Protected Storage
  ↓
Activity / Audit
  ↓
Controlled Response
```

The most security-sensitive AEGIS operation remains:

```
Content Consumer
   ↓
Authenticate
   ↓
Authorize
   ↓
Validate Training Access
   ↓
Identify Content
   ↓
Identify Current Version
   ↓
Controlled Delivery
   ↓
Dynamic Watermark
   ↓
Activity / Audit
```

Therefore, the API is **not merely a CRUD interface over the database**.

It is the **application security and business-operation boundary through which AEGIS exposes its domain capabilities**.

---

# 78. Phase 5 → Phase 6

With the API contract established, the next phase is:

```
PHASE 6 — UI/UX DESIGN
```

Phase 6 will map the API/domain capabilities into actual user-facing experiences:

```
Authentication
        ↓
Dashboard
        ↓
Organization Management
        ↓
User & Role Management
        ↓
Content Management
        ↓
Content Versioning
        ↓
Training Programs
        ↓
Trainer Access
        ↓
Secure Content Viewer
        ↓
Activity / Audit
        ↓
Analytics
```

The UI should consume the APIs defined here rather than creating separate business logic of its own.