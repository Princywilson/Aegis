# AEGIS — PHASE 3

# Data Architecture & Database Design

**Project:** AEGIS — Enterprise Knowledge Protection and Delivery Platform

**Phase:** Phase 3 — Data Architecture

**Status:** Baseline / Proposed Database Design

**Primary Database:** PostgreSQL

**Tenant Strategy:** Shared Database with Logical Tenant Isolation

**Backend:** Python Django

---

# 1. Purpose

Phase 3 converts the stable AEGIS domain model and functional architecture into a concrete **data architecture**.

The purpose of this phase is to define:

- The database entities
- Tables
- Columns
- Primary keys
- Foreign keys
- Relationships
- Cardinalities
- Unique constraints
- Check constraints
- Indexes
- Tenant isolation
- Content versioning
- Audit structure
- Activity/event storage
- Object-storage metadata
- Data lifecycle considerations

The database design must support the established AEGIS principles:

```
Security First
Multi-Tenant
Cloud Native
Simple for Content Consumers
Scalable
Auditable
```

The database must therefore preserve the distinction between:

```
Business Entity
      ↓
Authorization
      ↓
Actual Access
      ↓
Activity
      ↓
Audit
```

---

# 2. Data Architecture Principles

The following principles govern the AEGIS database.

## DA-001 — Organization is the Tenant Boundary

Every organization using AEGIS is treated as an independent tenant.

```
AEGIS
 │
 ├── Organization A
 │      ├── Users
 │      ├── Content
 │      ├── Programs
 │      └── Activity
 │
 ├── Organization B
 │      ├── Users
 │      ├── Content
 │      ├── Programs
 │      └── Activity
 │
 └── Organization C
        ├── Users
        ├── Content
        ├── Programs
        └── Activity
```

An organization must never be able to access another organization's data.

---

# 3. Database Architecture Decision

## 3.1 Primary Database

AEGIS will use:

> **PostgreSQL as the primary relational database.**
> 

This is now the preferred and formal Phase 3 decision.

PostgreSQL is responsible for:

- Identity-related application data
- Organizations
- Roles and permissions
- Content metadata
- Content versions
- Programs
- Assignments
- Access grants
- Activity
- Security events
- Audit records
- Relationships
- Transactional integrity

---

# 4. Object Storage Architecture

Training files themselves should not be stored directly inside PostgreSQL.

The architecture is:

```
                    AEGIS
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
     PostgreSQL              Object Storage
          │                       │
          │                       ├── Content File
          │                       ├── Version File
          │                       └── Protected Asset
          │
          ├── Metadata
          ├── Ownership
          ├── Version
          ├── Lifecycle
          └── Storage Reference
```

PostgreSQL stores the metadata and reference required to locate the object.

It does **not** store the large training file as the normal database payload.

---

# 5. High-Level ER Model

The conceptual database relationship is:

```
                              ┌────────────────┐
                              │  Organization  │
                              └───────┬────────┘
                                      │
             ┌────────────────────────┼────────────────────────┐
             │                        │                        │
             ▼                        ▼                        ▼
          Users                    Content              Programs
             │                        │                        │
             │                        ▼                        │
             │                Content Versions                │
             │                        │                        │
             │                        │                        ▼
             │                        └──────────────► Content Assignments
             │                                                   │
             ▼                                                   ▼
      User Roles                                          Training Access
             │                                                   │
             ▼                                                   │
       Permissions                                               │
                                                                 ▼
                                                           Content Access
                                                                 │
             ┌───────────────────────────────────────────────────┤
             │                                                   │
             ▼                                                   ▼
       Activity Events                                      Security Events
             │                                                   │
             └──────────────────────┬────────────────────────────┘
                                    ▼
                              Audit Records
```

---

# 6. Database Entity Catalogue

The initial AEGIS database consists of the following principal entities.

| Entity | Table | Tenant-Owned |
| --- | --- | --- |
| Organization | `organizations` | No |
| User | `users` | Yes |
| Role | `roles` | Yes |
| Permission | `permissions` | No / System |
| User Role | `user_roles` | Yes |
| Role Permission | `role_permissions` | Depends |
| Content | `contents` | Yes |
| Content Version | `content_versions` | Yes |
| Program | `programs` | Yes |
| Content Assignment | `content_assignments` | Yes |
| Training Access | `training_access` | Yes |
| Content Access | `content_access` | Yes |
| Activity Event | `activity_events` | Yes |
| Security Event | `security_events` | Tenant or platform scoped |
| Authentication Rate Limit Counter | `authentication_rate_limit_counters` | No / hashed keys |
| Audit Record | `audit_records` | Yes |
| Authentication Session | Django session infrastructure | Yes / User-scoped |

Some technical authentication tables may be supplied by Django rather than custom-designed by AEGIS.

---

# 7. Organization

## Table

```
organizations
```

## Purpose

Represents an AEGIS tenant.

## Columns

| Column | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | UUID | Yes | Primary key |
| `name` | VARCHAR | Yes | Organization name |
| `slug` | VARCHAR | Yes | Unique organization identifier |
| `status` | VARCHAR | Yes | Organization lifecycle state |
| `created_at` | TIMESTAMP | Yes | Creation timestamp |
| `updated_at` | TIMESTAMP | Yes | Last modification timestamp |

## Primary Key

```
PK: id
```

## Constraints

```
UNIQUE(slug)
```

Organization status should be constrained to supported lifecycle values, for example:

```
ACTIVE
SUSPENDED
ARCHIVED
```

---

# 8. User

## Table

```
users
```

AEGIS should use Django's authentication foundation rather than inventing a completely independent authentication mechanism.

The application-specific user representation should support organizational membership.

## Columns

| Column | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | UUID | Yes | Primary key |
| `organization_id` | UUID | Yes | Tenant |
| `email` | VARCHAR | Yes | Login/contact identity |
| `password_hash` | VARCHAR | Yes | Authentication credential |
| `first_name` | VARCHAR | No | First name |
| `last_name` | VARCHAR | No | Last name |
| `status` | VARCHAR | Yes | User state |
| `last_login_at` | TIMESTAMP | No | Last successful login |
| `created_at` | TIMESTAMP | Yes | Creation timestamp |
| `updated_at` | TIMESTAMP | Yes | Last modification timestamp |

## Primary Key

```
PK: id
```

## Foreign Key

```
organization_id
    → organizations.id
```

## Important Constraint

Email uniqueness should be evaluated according to the tenant model.

For the initial shared database:

```
UNIQUE(organization_id, email)
```

This allows different organizations to have users with the same email while preventing duplicate user identities inside the same organization.

---

# 9. Role

## Table

```
roles
```

## Purpose

Represents a collection of permissions within an organization.

Initial operational roles:

```
Administrator
Content Consumer
```

The architecture remains extensible for future roles.

## Columns

| Column | Type | Required |
| --- | --- | --- |
| `id` | UUID | Yes |
| `organization_id` | UUID | Yes |
| `name` | VARCHAR | Yes |
| `description` | TEXT | No |
| `is_system_role` | BOOLEAN | Yes |
| `created_at` | TIMESTAMP | Yes |
| `updated_at` | TIMESTAMP | Yes |

## Constraints

```
UNIQUE(organization_id, name)
```

---

# 10. Permission

## Table

```
permissions
```

## Purpose

Represents an atomic authorization capability.

Examples:

```
content.view
content.create
content.update
content.publish
content.archive

program.view
program.create
program.update

user.view
user.create
user.update

access.grant
access.revoke

activity.view
audit.view
```

## Columns

| Column | Type | Required |
| --- | --- | --- |
| `id` | UUID | Yes |
| `code` | VARCHAR | Yes |
| `name` | VARCHAR | Yes |
| `description` | TEXT | No |

## Constraint

```
UNIQUE(code)
```

Permissions are primarily application/system-defined capabilities.

---

# 11. User Role

## Table

```
user_roles
```

This is the association between users and roles.

```
User
  │
  ├── Role
  ├── Role
  └── Role
```

## Columns

| Column | Type | Required |
| --- | --- | --- |
| `id` | UUID | Yes |
| `organization_id` | UUID | Yes |
| `user_id` | UUID | Yes |
| `role_id` | UUID | Yes |
| `assigned_at` | TIMESTAMP | Yes |
| `assigned_by` | UUID | No |

## Constraints

```
UNIQUE(organization_id, user_id, role_id)
```

The organization context is retained so that the relationship itself cannot accidentally cross tenant boundaries.

---

# 12. Role Permission

## Table

```
role_permissions
```

Represents:

```
Role
  ↓
Permissions
```

## Columns

| Column | Type | Required |
| --- | --- | --- |
| `id` | UUID | Yes |
| `role_id` | UUID | Yes |
| `permission_id` | UUID | Yes |

## Constraint

```
UNIQUE(role_id, permission_id)
```

---

# 13. Content

## Table

```
contents
```

## Purpose

Represents the logical training resource.

This is intentionally separate from the physical file and from individual versions.

```
Content
   │
   ├── Version 1
   ├── Version 2
   └── Version 3
```

## Columns

| Column | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | UUID | Yes | Primary key |
| `organization_id` | UUID | Yes | Owner tenant |
| `title` | VARCHAR | Yes | Content title |
| `description` | TEXT | No | Description |
| `status` | VARCHAR | Yes | Lifecycle state |
| `current_version_id` | UUID | No | Current delivery version |
| `created_by` | UUID | Yes | Creating user |
| `created_at` | TIMESTAMP | Yes | Creation time |
| `updated_at` | TIMESTAMP | Yes | Last update |

## Relationship

```
Organization
      │
      ▼
   Content
      │
      ▼
Content Versions
```

---

# 14. Content Version

## Table

```
content_versions
```

## Purpose

Represents one immutable revision of a content item.

## Columns

| Column | Type | Required |
| --- | --- | --- |
| `id` | UUID | Yes |
| `organization_id` | UUID | Yes |
| `content_id` | UUID | Yes |
| `version_number` | INTEGER | Yes |
| `status` | VARCHAR | Yes |
| `storage_key` | VARCHAR | Yes |
| `original_filename` | VARCHAR | Yes |
| `mime_type` | VARCHAR | Yes |
| `file_size` | BIGINT | Yes |
| `checksum` | VARCHAR | Yes |
| `created_by` | UUID | Yes |
| `created_at` | TIMESTAMP | Yes |
| `published_at` | TIMESTAMP | No |
| `archived_at` | TIMESTAMP | No |

## Constraints

```
UNIQUE(organization_id, content_id, version_number)
```

Version number should be positive:

```
version_number > 0
```

## Immutability

Once a version becomes published, its core content/file identity must not be modified.

A modification creates:

```
New Content Version
```

rather than altering the existing published version.

---

# 15. Current Version Relationship

`contents.current_version_id` identifies the currently active delivery version.

```
Content
   │
   ├── Version 1
   ├── Version 2
   └── Version 3 ← current_version_id
```

The relationship must ensure that the referenced version belongs to the same:

```
organization
+
content
```

This prevents a content record from pointing to another organization's version.

---

# 16. Program

## Table

```
programs
```

## Purpose

Represents the business/training context in which content is used.

## Columns

| Column | Type | Required |
| --- | --- | --- |
| `id` | UUID | Yes |
| `organization_id` | UUID | Yes |
| `name` | VARCHAR | Yes |
| `description` | TEXT | No |
| `status` | VARCHAR | Yes |
| `created_by` | UUID | Yes |
| `created_at` | TIMESTAMP | Yes |
| `updated_at` | TIMESTAMP | Yes |

## Constraint

```
UNIQUE(organization_id, name)
```

---

# 17. Content Assignment

## Table

```
content_assignments
```

## Purpose

Represents the relationship between a Program and Content.

```
Program
       │
       ▼
Content Assignment
       │
       ▼
Content
```

## Columns

| Column | Type | Required |
| --- | --- | --- |
| `id` | UUID | Yes |
| `organization_id` | UUID | Yes |
| `program_id` | UUID | Yes |
| `content_id` | UUID | Yes |
| `display_order` | INTEGER | No |
| `is_required` | BOOLEAN | Yes |
| `assigned_at` | TIMESTAMP | Yes |
| `assigned_by` | UUID | Yes |

## Constraint

```
UNIQUE(
    organization_id,
    program_id,
    content_id
)
```

A content item should not be assigned to the same program more than once.

---

# 18. Training Access

## Table

```
training_access
```

## Purpose

Represents authorization granted to a user for a program/context.

This is **not an access event**.

It answers:

> "Is this user authorized to use this training context?"
> 

## Columns

| Column | Type | Required |
| --- | --- | --- |
| `id` | UUID | Yes |
| `organization_id` | UUID | Yes |
| `user_id` | UUID | Yes |
| `program_id` | UUID | Yes |
| `status` | VARCHAR | Yes |
| `granted_at` | TIMESTAMP | Yes |
| `granted_by` | UUID | Yes |
| `revoked_at` | TIMESTAMP | No |
| `revoked_by` | UUID | No |
| `expires_at` | TIMESTAMP | No |

## Constraint

```
UNIQUE(
    organization_id,
    user_id,
    program_id
)
```

Possible status values:

```
ACTIVE
REVOKED
EXPIRED
```

---

# 19. Content Access

## Table

```
content_access
```

## Purpose

Represents an actual instance of protected content access.

This is different from `training_access`.

```
Training Access
= authorization

Content Access
= actual access occurrence
```

## Columns

| Column | Type | Required |
| --- | --- | --- |
| `id` | UUID | Yes |
| `organization_id` | UUID | Yes |
| `user_id` | UUID | Yes |
| `content_id` | UUID | Yes |
| `content_version_id` | UUID | Yes |
| `program_id` | UUID | No |
| `accessed_at` | TIMESTAMP | Yes |
| `session_id` | UUID / reference | No |
| `access_result` | VARCHAR | Yes |
| `client_context` | JSONB | No |

`access_result` may distinguish events such as:

```
GRANTED
DENIED
```

For successful protected delivery, the version actually delivered must be recorded.

This is important because:

```
Content
    ↓
Version 3
    ↓
Content Consumer accessed Version 3
```

must remain historically determinable even after Version 4 becomes current.

---

# 20. Activity Events

## Table

```
activity_events
```

## Purpose

Stores significant normal user/system activity.

Examples:

```
CONTENT_VIEWED
CONTENT_OPENED
CONTENT_ACCESSED
TRAINING_STARTED
TRAINING_ACTIVITY
CONTENT_ACCESS_ATTEMPTED
```

## Columns

| Column | Type | Required |
| --- | --- | --- |
| `id` | UUID | Yes |
| `organization_id` | UUID | Yes |
| `user_id` | UUID | No |
| `event_type` | VARCHAR | Yes |
| `occurred_at` | TIMESTAMP | Yes |
| `content_id` | UUID | No |
| `content_version_id` | UUID | No |
| `program_id` | UUID | No |
| `session_id` | UUID | No |
| `metadata` | JSONB | No |

The JSONB field should be used only for event-specific information rather than replacing proper relational fields.

---

# 21. Security Events

## Table

```
security_events
```

## Purpose

Stores security-sensitive events.

Examples:

```
LOGIN_FAILURE
ACCESS_DENIED
UNAUTHORIZED_ACCESS_ATTEMPT
SESSION_SECURITY_EVENT
SUSPICIOUS_ACTIVITY
```

## Columns

| Column | Type | Required |
| --- | --- | --- |
| `id` | UUID | Yes |
| `organization_id` | UUID | No |
| `user_id` | UUID | No |
| `event_type` | VARCHAR | Yes |
| `severity` | VARCHAR | Yes |
| `occurred_at` | TIMESTAMP | Yes |
| `resource_type` | VARCHAR | No |
| `resource_id` | UUID | No |
| `metadata` | JSONB | No |

Security events are retained independently from ordinary activity because their purpose is security monitoring and investigation.

### Security Event Scope

`organization_id` is nullable only to represent a platform-level event that occurs before a tenant can be resolved. A non-null value identifies a tenant-scoped event. A null value identifies a platform-level event; it must never be treated as belonging to a default organization.

Examples include recording an authentication failure with `organization_id = null` when the supplied organization slug does not resolve, and recording an authentication event with the resolved organization when the organization exists. `user_id` remains nullable for attempts where no user can be resolved.

Activity Events remain organization-owned: `activity_events.organization_id` is required and is not changed by this rule.

Event metadata must be minimal and sanitized. Authentication secrets, including passwords and session tokens, must never be stored. Platform-level events must be restricted to authorized platform-level monitoring; organization-level access must be constrained to events whose `organization_id` matches the authenticated user's organization.

### Security Event Severity and Authentication Event Mapping

Allowed severity values are `INFO`, `LOW`, `MEDIUM`, and `HIGH`. Each event type must have an explicit severity mapping before implementation.

| Event Type | Severity | Description |
| --- | --- | --- |
| `LOGIN_SUCCESS` | `INFO` | Authentication completed successfully. |
| `LOGIN_FAILURE` | `MEDIUM` | An authentication attempt failed, including a rate-limit trigger. |
| `LOGOUT` | `INFO` | An authenticated session was terminated normally. |

Severity is independent of whether an event is tenant- or platform-scoped. `LOW` and `HIGH` remain available for event types that receive an explicit mapping.

## 21.1 Authentication Rate Limit Counters

### Table

```
authentication_rate_limit_counters
```

This technical table provides shared, atomic counter state for login attempts. It is stored in PostgreSQL, not process-local memory.

| Column | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | UUID | Yes | Primary key |
| `key_type` | VARCHAR | Yes | `ACCOUNT` or `SOURCE_IP` |
| `key_hash` | VARCHAR(64) | Yes | HMAC-SHA-256 digest; raw identifiers are not stored |
| `failure_timestamps` | JSONB | Yes | Failed-attempt timestamps in the active rolling window |
| `blocked_until` | TIMESTAMP | No | End of the active 15-minute block |
| `updated_at` | TIMESTAMP | Yes | Last counter update |

Constraints:

```
UNIQUE(key_type, key_hash)
CHECK(key_type IN ('ACCOUNT', 'SOURCE_IP'))
```

Counter rows are locked while they are read and updated so concurrent application instances share consistent state. Failure timestamps older than the rolling window are discarded. The counter keys are HMAC-SHA-256 digests of the normalized organization-scoped account identifier or source IP, using the Django secret key; credentials, raw email addresses, and raw IP values are not stored in this table.

Run `python manage.py cleanup_auth_rate_limits` periodically to delete counter rows that have no failures or active block within the rolling window. The deployment scheduler and cadence are environment-specific and must be configured without adding process-local counter storage.

The direct request source address is used for the IP key. Forwarded-IP headers are accepted only if a trusted-proxy configuration is explicitly established; arbitrary client-provided forwarding headers must not be trusted.

---

# 22. Audit Records

## Table

```
audit_records
```

## Purpose

Stores important business/security changes that must remain historically traceable.

Examples:

```
USER_CREATED
USER_ROLE_CHANGED

CONTENT_CREATED
CONTENT_UPDATED
CONTENT_PUBLISHED
CONTENT_ARCHIVED

VERSION_CREATED
VERSION_PUBLISHED

ACCESS_GRANTED
ACCESS_REVOKED

PERMISSION_CHANGED
```

## Columns

| Column | Type | Required |
| --- | --- | --- |
| `id` | UUID | Yes |
| `organization_id` | UUID | Yes |
| `actor_user_id` | UUID | No |
| `action` | VARCHAR | Yes |
| `resource_type` | VARCHAR | Yes |
| `resource_id` | UUID | Yes |
| `occurred_at` | TIMESTAMP | Yes |
| `old_values` | JSONB | No |
| `new_values` | JSONB | No |
| `metadata` | JSONB | No |

Audit records should be treated as historical records.

Normal application operations must not silently rewrite historical audit information.

---

# 23. Authentication Sessions

AEGIS will use Django's authentication/session architecture rather than creating a completely independent authentication subsystem.

Where session persistence is required, Django's session infrastructure can be used.

Conceptually:

```
User
  │
  ▼
Authentication Session
  │
  ├── Content Access
  ├── Activity
  └── Security Events
```

The exact Django session implementation remains framework-managed rather than being unnecessarily duplicated in the AEGIS domain schema.

---

# 24. Watermark Data

Dynamic watermarking is a content-protection mechanism rather than necessarily a permanent domain entity.

The watermark may be generated during protected content delivery using contextual information such as:

```
Authenticated User
Organization
Session
Content
Content Version
Access Time
```

Therefore, the initial database does **not** require a standalone:

```
watermarks
```

table.

Instead, relevant watermark context can be derived from the access/session information.

If future requirements require watermark templates, policies or historical watermark instances, a dedicated structure can be introduced.

---

# 25. Complete Relationship Model

The primary relationships are:

```
Organization
│
├── Users
│    │
│    └── User Roles
│          │
│          └── Roles
│                │
│                └── Permissions
│
├── Content
│    │
│    └── Content Versions
│
├── Programs
│    │
│    └── Content Assignments
│              │
│              └── Content
│
├── Training Access
│    │
│    ├── User
│    └── Program
│
├── Content Access
│    │
│    ├── User
│    ├── Content
│    ├── Content Version
│    └── Program
│
├── Activity Events
│
├── Security Events
│
└── Audit Records
```

---

# 26. Cardinality Model

## Organization

```
Organization 1 ──── N Users
Organization 1 ──── N Roles
Organization 1 ──── N Contents
Organization 1 ──── N Programs
Organization 1 ──── N Training Access Records
Organization 1 ──── N Activity Events
Organization 1 ──── N Security Events
Organization 1 ──── N Audit Records
```

## Content

```
Content 1 ──── N Content Versions
Content 1 ──── N Content Assignments
Content 1 ──── N Content Access Records
```

## Program

```
Program 1 ──── N Content Assignments
Program 1 ──── N Training Access Records
Program 1 ──── N Content Access Records
```

## User

```
User N ──── N Roles
User N ──── N Programs
User 1 ──── N Content Access
User 1 ──── N Activity Events
User 1 ──── N Security Events
User 1 ──── N Audit Records
```

---

# 27. Many-to-Many Relationships

AEGIS contains several many-to-many relationships.

## User ↔ Role

Implemented through:

```
user_roles
```

```
User
  │
  ├── User Role ── Role
  ├── User Role ── Role
  └── User Role ── Role
```

## Role ↔ Permission

Implemented through:

```
role_permissions
```

## Program ↔ Content

Implemented through:

```
content_assignments
```

## User ↔ Program

Implemented through:

```
training_access
```

This distinction is important because these relationships represent different business meanings and therefore must not be collapsed into generic relationship tables.

---

# 28. Tenant Isolation Strategy

AEGIS will initially use:

> **Shared Database + Shared Schema + Logical Tenant Isolation**
> 

Conceptually:

```
PostgreSQL
│
├── organizations
│
├── users
│      └── organization_id
│
├── contents
│      └── organization_id
│
├── content_versions
│      └── organization_id
│
├── programs
│      └── organization_id
│
├── training_access
│      └── organization_id
│
├── activity_events
│      └── organization_id
│
└── audit_records
       └── organization_id
```

---

# 29. Tenant Isolation Rule

Every tenant-owned table must contain an explicit:

```
organization_id
```

where practical.

This avoids relying only on indirect relationships.

For example:

```
content_versions
```

should not merely contain:

```
content_id
```

but also:

```
organization_id
```

This allows the database to enforce:

```
Content Version Organization
=
Content Organization
```

---

# 30. Composite Foreign-Key Strategy

For security-sensitive tenant-owned relationships, AEGIS should use composite relationships where appropriate.

For example:

```
Content
(
    organization_id,
    id
)
```

and:

```
Content Version
(
    organization_id,
    content_id
)
```

must reference the same organization.

Conceptually:

```
(content.organization_id, content.id)
            ▲
            │
            │
(content_version.organization_id,
 content_version.content_id)
```

This prevents a record from accidentally connecting:

```
Organization A Content
        ↓
Organization B Content Version
```

even if an application-level bug attempts such a relationship.

This provides an additional layer of tenant isolation.

---

# 31. Application-Level Tenant Enforcement

Database constraints alone are not sufficient.

Django must establish the organization context before querying tenant-owned data.

Conceptually:

```
Request
   │
   ▼
Authenticated User
   │
   ▼
Organization Context
   │
   ▼
Authorization
   │
   ▼
Tenant-Scoped Query
   │
   ▼
Database
```

Every protected query must be scoped to the current organization.

For example:

```
Current Organization
        +
Requested Resource
        ↓
Authorization Check
        ↓
Tenant-Scoped Query
```

The frontend must never be treated as the tenant-security boundary.

---

# 32. Tenant Isolation Defence in Depth

AEGIS should therefore use multiple layers:

```
Layer 1
Authentication
      ↓
Layer 2
Organization Membership
      ↓
Layer 3
Role / Permission Authorization
      ↓
Layer 4
Tenant-Scoped Application Query
      ↓
Layer 5
Foreign-Key / Database Constraints
      ↓
Layer 6
Protected Object-Storage Access
```

This is consistent with the established requirement that authorization be enforced server-side.

---

# 33. Unique Constraints

Tenant-owned business objects should generally use organization-scoped uniqueness.

Examples:

```
UNIQUE(organization_id, email)

UNIQUE(organization_id, role_name)

UNIQUE(organization_id, content_title)

UNIQUE(organization_id, program_name)

UNIQUE(
    organization_id,
    content_id,
    version_number
)

UNIQUE(
    organization_id,
    program_id,
    content_id
)

UNIQUE(
    organization_id,
    user_id,
    program_id
)
```

This prevents accidental collisions without making unrelated organizations compete for the same namespace.

---

# 34. Referential Integrity

Foreign keys must be used wherever a stable domain relationship exists.

Examples:

```
users.organization_id
        → organizations.id

contents.organization_id
        → organizations.id

content_versions.content_id
        → contents.id

programs.organization_id
        → organizations.id

content_assignments.program_id
        → programs.id

content_assignments.content_id
        → contents.id

training_access.user_id
        → users.id

training_access.program_id
        → programs.id
```

Foreign-key relationships must not permit cross-organization relationships.

---

# 35. Delete Strategy

Because AEGIS requires historical traceability, unrestricted cascading deletion should be avoided.

In particular:

```
Content
   ↓
Content Versions
   ↓
Access History
   ↓
Activity
   ↓
Audit
```

must not be destroyed simply because the current content record is removed from active use.

The preferred business approach is:

```
ACTIVE
   ↓
ARCHIVED
```

rather than physical deletion.

---

# 36. Content Lifecycle

Content follows a controlled lifecycle.

```
              ┌───────────┐
              │   Draft   │
              └─────┬─────┘
                    │
                    ▼
              ┌───────────┐
              │ Published │
              └─────┬─────┘
                    │
                    ▼
              ┌───────────┐
              │ Archived  │
              └───────────┘
```

Only appropriate content states should be available for protected delivery.

---

# 37. Content Version Lifecycle

A version follows a similar controlled lifecycle:

```
Created
   │
   ▼
Draft
   │
   ▼
Published
   │
   ▼
Archived
```

Once published:

```
Published Version
        │
        └── Immutable
```

A change requires:

```
New Version
```

rather than modification of the historical published version.

---

# 38. Versioning Structure

The database deliberately separates:

```
contents
```

from:

```
content_versions
```

Example:

```
contents
────────────────────────────
id = C001
title = Working at Height
current_version_id = V003

content_versions
────────────────────────────
V001 → Version 1 → Archived
V002 → Version 2 → Archived
V003 → Version 3 → Published
```

This allows AEGIS to determine exactly which version was delivered at a historical point in time.

---

# 39. Object Storage Key Strategy

The object-storage reference should not expose a public URL.

A logical storage key may follow a tenant-aware structure such as:

```
organizations/{organization_id}/contents/{content_id}/versions/{version_id}/file
```

The database stores the storage reference:

```
storage_key
```

rather than a permanent public download URL.

The actual storage provider and infrastructure will be finalized during System Architecture.

---

# 40. Content Security Boundary

The intended access flow is:

```
Content Consumer
   │
   ▼
Authenticate
   │
   ▼
Organization Validation
   │
   ▼
Permission Check
   │
   ▼
Training Access Check
   │
   ▼
Content Assignment Check
   │
   ▼
Current/Authorized Version
   │
   ▼
Secure Content Delivery
   │
   ├── Watermark Context
   ├── Activity Event
   └── Content Access Record
```

The user should not receive an unrestricted object-storage URL.

---

# 41. Audit Data Design

Audit records are intentionally separated from ordinary activity.

```
Activity
= normal usage tracking

Audit
= historical accountability record
```

Example:

```
Activity:
Content Consumer opened Content X.

Audit:
Protected Content X was accessed by Content Consumer A
at time T.
```

This distinction must remain in the database.

---

# 42. Audit Immutability

Audit records should be treated as append-oriented historical records.

Normal business operations should not:

- overwrite old audit events
- alter the original event timestamp
- replace the original actor
- silently remove audit history

If corrections are ever required, they should themselves be traceable.

---

# 43. Activity Data vs Audit Data

| Requirement | Activity | Audit |
| --- | --- | --- |
| Track normal user activity | ✓ |  |
| Content usage analytics | ✓ |  |
| Content Consumer activity | ✓ |  |
| Security investigation |  | ✓ |
| Business change history |  | ✓ |
| Permission changes |  | ✓ |
| Access grant/revocation |  | ✓ |
| Historical accountability |  | ✓ |

This keeps analytics-oriented event data separate from accountability-oriented records.

---

# 44. Indexing Strategy

Indexes should primarily support:

1. Tenant filtering
2. Authentication
3. Authorization
4. Content lookup
5. Version lookup
6. Access verification
7. Activity reporting
8. Audit reporting

---

# 45. Core Indexes

## Organizations

```
UNIQUE INDEX(slug)
```

## Users

```
INDEX(organization_id)

UNIQUE INDEX(
    organization_id,
    email
)
```

## Roles

```
INDEX(organization_id)

UNIQUE INDEX(
    organization_id,
    name
)
```

## Contents

```
INDEX(organization_id)

INDEX(
    organization_id,
    status
)
```

## Content Versions

```
INDEX(
    organization_id,
    content_id
)

INDEX(
    organization_id,
    content_id,
    version_number
)

INDEX(
    organization_id,
    status
)
```

## Programs

```
INDEX(organization_id)

INDEX(
    organization_id,
    status
)
```

## Training Access

```
INDEX(
    organization_id,
    user_id
)

INDEX(
    organization_id,
    program_id
)

INDEX(
    organization_id,
    user_id,
    status
)
```

## Content Access

```
INDEX(
    organization_id,
    user_id,
    accessed_at
)

INDEX(
    organization_id,
    content_id,
    accessed_at
)

INDEX(
    organization_id,
    content_version_id,
    accessed_at
)
```

## Activity

```
INDEX(
    organization_id,
    occurred_at
)

INDEX(
    organization_id,
    user_id,
    occurred_at
)

INDEX(
    organization_id,
    event_type,
    occurred_at
)
```

## Security Events

```
INDEX(
    organization_id,
    occurred_at
)

INDEX(
    organization_id,
    severity,
    occurred_at
)
```

## Audit

```
INDEX(
    organization_id,
    occurred_at
)

INDEX(
    organization_id,
    resource_type,
    resource_id
)

INDEX(
    organization_id,
    actor_user_id,
    occurred_at
)
```

---

# 46. Timestamp Strategy

All persisted timestamps should be stored consistently using UTC.

Application/UI layers may convert timestamps into the organization's or user's local timezone for presentation.

Recommended conceptual fields:

```
created_at
updated_at
occurred_at
published_at
archived_at
granted_at
revoked_at
expires_at
```

Historical event timestamps should never be replaced with the current time during later processing.

---

# 47. Identifier Strategy

UUIDs are preferred for AEGIS primary keys.

Example:

```
organization.id
user.id
content.id
content_version.id
program.id
activity_event.id
audit_record.id
```

Rationale:

- Suitable for distributed systems
- Avoids predictable sequential identifiers
- Makes cross-system integration easier
- Better suited to future SaaS growth
- Reduces accidental exposure of record counts/sequences

---

# 48. JSONB Usage

PostgreSQL `JSONB` may be used for genuinely variable event metadata.

Examples:

```
activity_events.metadata
security_events.metadata
audit_records.old_values
audit_records.new_values
audit_records.metadata
```

However, core business relationships must remain relational.

For example, these should remain proper columns:

```
organization_id
user_id
content_id
content_version_id
program_id
```

They should not be hidden inside JSON.

---

# 49. Data Integrity Constraints

Important database constraints include:

### Organization

```
name NOT NULL
slug NOT NULL
```

### User

```
organization_id NOT NULL
email NOT NULL
```

### Content

```
organization_id NOT NULL
title NOT NULL
```

### Content Version

```
content_id NOT NULL
version_number > 0
storage_key NOT NULL
checksum NOT NULL
```

### Program

```
organization_id NOT NULL
name NOT NULL
```

### Training Access

```
user_id NOT NULL
program_id NOT NULL
```

### Activity

```
event_type NOT NULL
occurred_at NOT NULL
```

### Audit

```
action NOT NULL
resource_type NOT NULL
resource_id NOT NULL
occurred_at NOT NULL
```

---

# 50. Data Integrity Rules

The database must prevent invalid states such as:

```
Content Version
        ↓
Non-existent Content
```

or:

```
Training Access
        ↓
Non-existent User
```

or:

```
Content Assignment
        ↓
Program from Organization A
        +
Content from Organization B
```

or:

```
Content
        ↓
Current Version
        ↓
Version belonging to another Content
```

These must be prevented through a combination of:

```
Foreign Keys
+
Composite Constraints
+
Application Validation
```

---

# 51. Core Database Schema Summary

The initial AEGIS relational schema is therefore:

```
organizations

users
roles
permissions
user_roles
role_permissions

contents
content_versions

programs
content_assignments
training_access

content_access
activity_events
security_events
audit_records
```

Django-managed authentication/session tables complement these application tables.

---

# 52. Simplified ER Diagram

```
                              ORGANIZATIONS
                                   │
                 ┌─────────────────┼──────────────────┐
                 │                 │                  │
                 ▼                 ▼                  ▼
               USERS             CONTENT            PROGRAMS
                 │                 │                  │
                 ▼                 ▼                  │
             USER_ROLES     CONTENT_VERSIONS          │
                 │                 │                  │
                 ▼                 │                  ▼
               ROLES               │          CONTENT_ASSIGNMENTS
                 │                 │                  │
                 ▼                 │                  ▼
            PERMISSIONS            └──────────────► CONTENT
                                                        │
                                                        │
                       ┌────────────────────────────────┘
                       │
                       ▼
                 TRAINING_ACCESS
                       │
                       ▼
                      USER
                       │
                       ▼
                 CONTENT_ACCESS
                       │
             ┌─────────┼─────────┐
             │         │         │
             ▼         ▼         ▼
          ACTIVITY   SECURITY   AUDIT
           EVENTS     EVENTS    RECORDS
```

---

# 53. End-to-End Data Flow

A typical AEGIS content-delivery lifecycle becomes:

```
Organization Created
        │
        ▼
User Created
        │
        ▼
Role Assigned
        │
        ▼
Content Created
        │
        ▼
Content Version Created
        │
        ▼
Version Published
        │
        ▼
Program Created
        │
        ▼
Content Assigned to Program
        │
        ▼
Content Consumer Granted Training Access
        │
        ▼
Content Consumer Authenticates
        │
        ▼
Authorization Checked
        │
        ▼
Content Access Granted
        │
        ├──────────────► Content Access Record
        │
        ├──────────────► Activity Event
        │
        ├──────────────► Security Context
        │
        └──────────────► Audit Record
```

---

# 54. Important Database Distinctions

The following distinctions must be preserved.

## Content ≠ Content Version

```
Content
= logical training resource

Content Version
= specific revision
```

## Training Access ≠ Content Access

```
Training Access
= permission/authorization

Content Access
= actual access occurrence
```

## Activity ≠ Audit

```
Activity
= what happened during usage

Audit
= what important event must be historically accountable
```

## Object Storage ≠ Database

```
PostgreSQL
= metadata + relationships

Object Storage
= training files
```

## User ≠ Content Consumer

```
User
= authenticated identity

Content Consumer
= role/capability of a user
```

This avoids creating an unnecessary separate role-specific user table.

---

# 55. Tables Deliberately Not Introduced

The following are intentionally not core MVP tables.

## AI Analysis

```
trainer_ai_analysis
```

Future scope.

## DRM

```
drm_policies
drm_keys
```

Not required for the MVP.

## Mobile Device

No dedicated mobile-device domain is required for the current MVP.

## Offline Viewer

No offline-content synchronization schema is required.

## External Integrations

No integration-specific tables are introduced until an actual integration requirement exists.

## Watermark Instances

No permanent watermark table is required at this stage.

These remain consistent with the project's future enhancement direction, which includes AI analytics, DRM-inspired protection, mobile support, offline encrypted viewing and external integrations.

---

# 56. Data Lifecycle Strategy

AEGIS should prefer logical lifecycle management over aggressive physical deletion.

Example:

```
ACTIVE
  ↓
INACTIVE
  ↓
ARCHIVED
```

Historical content versions, access events and audit records should remain available according to the eventual retention policy.

A future retention mechanism may be introduced for high-volume event data.

---

# 57. High-Volume Data Consideration

The following tables are expected to grow faster than normal business tables:

```
content_access
activity_events
security_events
audit_records
```

Therefore, the schema should be designed so that future partitioning or archival can be introduced without redesigning the domain.

For example:

```
activity_events
       │
       ├── current data
       │
       └── historical/archived data
```

Partitioning is **not required for the initial MCA MVP** but the schema should not prevent it later.

---

# 58. Security Considerations

The database architecture must assume that the data itself is security-sensitive.

Important controls include:

- Tenant-scoped queries
- Foreign-key integrity
- Restricted database access
- No public object-storage URLs
- Immutable historical versions
- Append-oriented audit records
- Server-side authorization
- Controlled database credentials
- Encryption in transit
- Encryption at rest where supported by infrastructure
- Secure backup strategy

Infrastructure-level implementation belongs to Phase 4.

---

# 59. Backup and Recovery Boundary

The database will contain critical organizational metadata and historical records.

Therefore:

```
PostgreSQL
    ↓
Backup
    ↓
Recovery
```

must preserve:

- Organizations
- Users
- Authorization
- Content metadata
- Version history
- Access history
- Activity
- Audit history

Object-storage backups/lifecycle management must be handled separately from PostgreSQL backups.

The exact backup infrastructure is a Phase 4 concern.

---

# 60. Database vs Application Responsibility

Not every business rule should be implemented exclusively in SQL.

## Database should enforce:

```
Primary keys
Foreign keys
Required values
Uniqueness
Basic value constraints
Referential integrity
Tenant relationship consistency
```

## Application should enforce:

```
Authorization
Role permissions
Content lifecycle transitions
Publishing rules
Access eligibility
Business workflows
Watermark generation
Secure content delivery
```

The two layers work together:

```
Business Logic
      │
      ▼
Django
      │
      ▼
Database Integrity
```

---

# 61. Final Phase 3 Architecture

The complete Phase 3 architecture can be summarized as:

```
                         AEGIS
                           │
                           ▼
                    ORGANIZATION
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
        USERS           CONTENT           PROGRAMS
          │                │                │
          ▼                ▼                ▼
       ROLES          VERSIONS       CONTENT ASSIGNMENTS
          │                │                │
          ▼                └───────┬────────┘
    PERMISSIONS                     │
                                    ▼
                             TRAINING ACCESS
                                    │
                                    ▼
                              AUTHORIZED USER
                                    │
                                    ▼
                              CONTENT ACCESS
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
                 ▼                  ▼                  ▼
              ACTIVITY          SECURITY             AUDIT
               EVENTS            EVENTS             RECORDS
```

Supporting storage:

```
                    AEGIS
                      │
             ┌────────┴────────┐
             │                 │
             ▼                 ▼
        PostgreSQL        Object Storage
             │                 │
       Metadata / Data     Training Files
       Relationships
       Audit / Activity
```

---

# 62. Phase 3 Decisions

The following decisions are now established for the AEGIS Data Architecture:

| Decision | Status |
| --- | --- |
| PostgreSQL as primary database | Accepted |
| Shared database initially | Accepted |
| Shared schema initially | Accepted |
| Organization as tenant boundary | Accepted |
| Logical tenant isolation | Accepted |
| `organization_id` on tenant-owned entities | Accepted |
| Tenant-aware uniqueness | Accepted |
| Composite tenant relationship protection where required | Accepted |
| Django authentication foundation | Accepted |
| Object storage for training files | Accepted |
| File metadata in PostgreSQL | Accepted |
| Content / Content Version separation | Accepted |
| Immutable published versions | Accepted |
| Training Access / Content Access separation | Accepted |
| Activity / Audit separation | Accepted |
| UUID primary identifiers | Accepted |
| UTC timestamps | Accepted |
| Audit as historical append-oriented data | Accepted |
| Dynamic watermark as delivery mechanism rather than mandatory table | Accepted for MVP |
| Future partitioning for high-volume event tables | Reserved |
| Database-per-tenant | Not selected for MVP |

---

# 63. Phase 3 Deliverables

Phase 3 now consists of:

```
PHASE 3 — DATA ARCHITECTURE
│
├── Database Architecture
│
├── ER Model
│
├── Entity Catalogue
│
├── Table Design
│
├── Column Design
│
├── Primary Keys
│
├── Foreign Keys
│
├── Cardinality
│
├── Unique Constraints
│
├── Check Constraints
│
├── Index Strategy
│
├── Tenant Isolation Strategy
│
├── Content Versioning Structure
│
├── Object Storage Metadata Strategy
│
├── Activity Data Model
│
├── Security Event Model
│
├── Audit Data Model
│
├── Data Lifecycle
│
└── Data Integrity Rules
```

---

# 64. Boundary to Phase 4

Phase 3 defines:

> **How AEGIS data is structured and related.**
> 

It does **not** yet define the complete infrastructure/system architecture.

Therefore, the following remain for Phase 4:

```
Application Components
        ↓
Django Architecture
        ↓
Frontend Architecture
        ↓
Content Delivery Architecture
        ↓
Object Storage Provider
        ↓
Security Boundaries
        ↓
Caching
        ↓
Background Processing
        ↓
Deployment
        ↓
Docker / Nginx
        ↓
Infrastructure
        ↓
Monitoring
        ↓
Scalability
```

The earlier proposal also identifies Docker/Nginx as future deployment infrastructure, which belongs naturally in this later system-architecture stage.

---

# 65. Final Phase 3 Data Architecture Statement

The AEGIS database is therefore centered on one fundamental structure:

```
Organization
      ↓
Users / Roles / Permissions
      ↓
Content
      ↓
Content Versions
      ↓
Programs
      ↓
Content Assignments
      ↓
Training Access
      ↓
Actual Content Access
      ↓
Activity / Security Events
      ↓
Audit History
```

with:

```
PostgreSQL
      +
Object Storage
      +
Organization-level tenant isolation
```

The most important architectural property is that **tenant ownership, authorization, historical versioning and auditability are represented directly in the data architecture rather than being left entirely to application convention.**

This gives AEGIS a database foundation that is:

- secure enough for the project's core IP-protection objective,
- simple enough for the MCA implementation,
- consistent with the established domain model,
- compatible with Django,
- suitable for an initial shared-database SaaS model,
- and extensible toward future scale.

---

# 66. Phase Roadmap Position

The project now stands as:

```
PHASE 0 — PRODUCT DESIGN
    ✅ Product Vision
    ✅ Product Philosophy
    ✅ Architecture Principles
    ✅ MVP Scope
    ✅ Future Roadmap

                ↓

PHASE 1 — DOMAIN / REQUIREMENTS DESIGN
    ✅ PRD
    ✅ SRS
    ✅ Domain Model
    ✅ Business Rules
    🟢 ADR Register initiated

                ↓

PHASE 2 — FUNCTIONAL ARCHITECTURE
    ✅ Modules
    ✅ Responsibilities
    ✅ Actors
    ✅ Inputs / Outputs
    ✅ Permissions
    ✅ Workflows
    ✅ Dependencies

                ↓

PHASE 3 — DATA ARCHITECTURE
    ✅ Database Architecture
    ✅ ER Model
    ✅ Entities
    ✅ Tables
    ✅ Columns
    ✅ PK / FK
    ✅ Constraints
    ✅ Indexes
    ✅ Tenant Isolation
    ✅ Versioning
    ✅ Audit Structure
    ✅ Object Storage Metadata

                ↓

PHASE 4 — SYSTEM ARCHITECTURE
    ⬅ NEXT
```

**Phase 3 — Data Architecture is now the baseline database design for AEGIS.**