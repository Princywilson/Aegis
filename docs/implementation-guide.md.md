# AEGIS — MVP Implementation & Development Guide

**Project:** AEGIS — Enterprise Knowledge Protection and Delivery Platform  
**Purpose:** Practical implementation guide for building the MCA MVP in VS Code without Cursor  
**Development approach:** Build and understand the system milestone-by-milestone  
**Backend:** Python + Django + Django REST Framework  
**Frontend:** React  
**Database:** PostgreSQL  
**Architecture:** Modular Django monolith  
**Target submission:** 1 November 2026

---

# 1. How We Will Use This Document

This is the implementation roadmap we will follow together.

The goal is **not** to write the whole application at once.

For every milestone we will follow:

```text
Understand
   ↓
Inspect current code
   ↓
Implement one small capability
   ↓
Run migrations / checks
   ↓
Write or update tests
   ↓
Manually verify
   ↓
Review security + tenant isolation
   ↓
Commit/checkpoint
   ↓
Move to next milestone
```

### Important rule

We will not jump ahead just because a later feature looks easy.

For example:

```text
Do not build the viewer before:
User
  ↓
Organization
  ↓
Role/Permission
  ↓
Content
  ↓
Content Version
  ↓
Training Program
  ↓
Assignment
  ↓
Training Access
```

This keeps the implementation understandable and aligned with the approved architecture.

---

# 2. Source of Truth

The implementation is based on the project material already completed:

```text
Phase 0
Product Design
        ↓
Phase 1
PRD
SRS
Domain Model
Business Rules
ADRs
        ↓
Phase 2
Functional Architecture
        ↓
Phase 3
Data Architecture
        ↓
Phase 4
System Architecture
        ↓
Phase 5
API Specification
        ↓
IMPLEMENTATION
```

The attached project proposal establishes the original problem, objective, technology direction and intended project outcome.

The later architecture documents are treated as the more detailed implementation baseline.

Where an early proposal statement conflicts with a later accepted architectural decision, the **latest accepted architecture wins**.

---

# 3. Final MVP Boundary

The MVP includes:

- Authentication
- Organization/Tenant Management
- User Management
- Role & Permission Management
- Content Repository
- Content Upload/Management
- Content Versioning
- Training Programs
- Content Assignment
- Controlled Trainer Access
- Secure Browser-Based Delivery
- Dynamic Watermarking
- Activity Tracking
- Access Logging
- Audit Logs
- Basic Analytics
- Basic Reports
- Administrative Configuration

The following remain outside the MVP:

- AI-based performance analysis
- AI recommendations
- AI-generated insights
- Advanced DRM
- Offline encrypted viewer
- Mobile application
- QR-based authentication
- Live training analytics
- LDAP / Active Directory / SSO
- LMS integrations
- Cloud storage integrations
- Microservices
- Unnecessary distributed infrastructure

The MVP should be small enough to finish reliably and strong enough to demonstrate the project's core security and governance idea.

---

# 4. Architecture We Are Actually Building

## 4.1 High-level system

```text
                         ┌─────────────────────┐
                         │        User         │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    React Frontend   │
                         └──────────┬──────────┘
                                    │ HTTPS / API
                                    ▼
                 ┌──────────────────────────────────────┐
                 │          Django Backend               │
                 │                                      │
                 │ Authentication                       │
                 │ Tenant Context                       │
                 │ Authorization / RBAC                  │
                 │ Content Management                   │
                 │ Version Management                   │
                 │ Program / Access Management          │
                 │ Secure Delivery                      │
                 │ Watermarking                         │
                 │ Activity / Security / Audit          │
                 │ Analytics / Reporting                │
                 └───────────────┬──────────────┬───────┘
                                 │              │
                                 ▼              ▼
                         ┌─────────────┐  ┌───────────────┐
                         │ PostgreSQL  │  │ Private File  │
                         │             │  │ Storage       │
                         │ Business    │  │               │
                         │ Data        │  │ Protected     │
                         │             │  │ Content       │
                         └─────────────┘  └───────────────┘
```

The browser must never receive unrestricted access to PostgreSQL or private storage.

---

# 5. Backend Architecture

We will use a **modular monolithic Django backend**.

The functional modules do not need to become one Django app each.

A practical implementation structure is:

```text
backend/
├── manage.py
├── config/
│   ├── settings/
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── common/
│   ├── exceptions.py
│   ├── responses.py
│   ├── tenant.py
│   ├── permissions.py
│   ├── models.py
│   └── services/
│
├── identity/
│   ├── models.py
│   ├── admin.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── services.py
│   ├── permissions.py
│   └── tests/
│
├── knowledge/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── services.py
│   ├── storage.py
│   └── tests/
│
├── programs/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── services.py
│   └── tests/
│
├── delivery/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── services.py
│   ├── watermark.py
│   └── tests/
│
└── accountability/
    ├── models.py
    ├── serializers.py
    ├── views.py
    ├── urls.py
    ├── services.py
    └── tests/
```

This is a starting structure, not a reason to create files unnecessarily.

---

# 6. Core Architectural Rules

These rules apply throughout development.

## Rule 1 — Organization is the tenant boundary

Every tenant-owned resource must belong to exactly one organization.

```text
Organization A
   ├── Users
   ├── Content
   ├── Programs
   ├── Access
   └── Activity

Organization B
   ├── Users
   ├── Content
   ├── Programs
   ├── Access
   └── Activity
```

Organization A must never access Organization B data.

---

## Rule 2 — Backend is the security boundary

The frontend can hide buttons.

It cannot enforce authorization.

Every protected operation must be authorized by Django.

---

## Rule 3 — Never trust organization IDs supplied by the client

Tenant context comes from the authenticated user/session.

Do not trust:

```text
?organization_id=...
```

or an arbitrary organization ID in a request body.

---

## Rule 4 — Use UUID primary keys

Application entities use UUID identifiers.

This applies particularly to user and business entities.

---

## Rule 5 — Published versions are immutable

If Version 1 is published and a change is required:

```text
V1
 ↓
Create V2
 ↓
Publish V2
```

Do not overwrite V1.

---

## Rule 6 — Content is not access

These concepts remain separate:

```text
Content
= logical resource

Content Version
= specific revision

Content Assignment
= content/program relationship

Training Access
= authorization

Content Access
= actual access occurrence
```

---

## Rule 7 — Activity, Security and Audit are different

```text
ActivityEvent
= usage/activity

SecurityEvent
= security-related event

AuditRecord
= historically accountable business/admin event
```

Do not merge all three into one generic log table.

---

## Rule 8 — Private files stay private

Protected source files are stored outside public web access.

There must be no permanent public URL to a protected source file.

---

## Rule 9 — Services own business rules

Views should remain thin.

Preferred:

```text
HTTP request
    ↓
View
    ↓
Serializer / validation
    ↓
Service
    ↓
Business rules
    ↓
Model / storage
```

Avoid putting complex business decisions directly inside views.

---

## Rule 10 — No unnecessary architecture

For the MVP:

```text
Django monolith
+
PostgreSQL
+
private local storage
+
React
```

No microservices, message broker, distributed cache or complex infrastructure unless a real requirement appears.

---

# 7. Frozen Implementation Decisions

The following decisions are now treated as implementation decisions.

## Authentication

Use Django session authentication.

```text
POST /auth/login/
        ↓
Django authentication
        ↓
Session created
        ↓
Secure HttpOnly session cookie
```

Use CSRF protection for unsafe requests.

No JWT subsystem is required for the MVP.

---

## Login identity

Login should use:

```text
organization_slug
+
email
+
password
```

Email uniqueness is organization-scoped.

Conceptually:

```text
UNIQUE(organization_id, email)
```

This permits the same email address to exist in different organizations.

---

## Initial organization creation

Do not create a public organization-registration endpoint for the MVP.

Use a controlled management command for initial setup.

Example:

```bash
python manage.py bootstrap_organization
```

---

## Initial user password

For MVP bootstrap/admin creation:

- generate a temporary password server-side
- store only the password hash
- display/return the temporary password only once through the controlled setup flow
- never store plaintext passwords

A complete invitation/password-reset workflow can be expanded later.

---

## Storage

Use a private local storage adapter for the MVP.

Hide storage behind a service interface so that future S3-compatible storage can be introduced without rewriting content business logic.

---

## Roles

The MVP role set is:

```text
Administrator
Content Manager
Trainer
Management
```

Do not use Django Groups as the AEGIS role model.

---

## Client activity events

Client activity is restricted to a closed allowlist of viewer events and must be associated with valid content-access context.

Security events and audit records are generated by trusted backend workflows.

---

# 8. Core Data Model

The initial application tables are:

```text
organizations

users
roles
permissions
user_roles
role_permissions

contents
content_versions

training_programs
content_assignments
training_access

content_access
activity_events
security_events
audit_records
```

Django's authentication/session tables complement these.

---

# 9. End-to-End Business Flow

The complete MVP flow is:

```text
Organization
    ↓
User
    ↓
Role
    ↓
Content
    ↓
Content Version
    ↓
Publish
    ↓
Training Program
    ↓
Content Assignment
    ↓
Training Access
    ↓
Authentication
    ↓
Authorization
    ↓
Content Access
    ↓
Secure Delivery
    ↓
Dynamic Watermark
    ↓
Activity Tracking
    ↓
Security/Audit
    ↓
Analytics/Reports
```

This is the backbone of the entire implementation.

---

# 10. Development Milestones

We will build the MVP in the following order.

```text
M0  Development Foundation
 ↓
M1  Organization + Custom Identity
 ↓
M2  Authentication + Session Management
 ↓
M3  RBAC
 ↓
M4  Content Repository
 ↓
M5  Content Versioning
 ↓
M6  Training Programs + Assignments
 ↓
M7  Training Access
 ↓
M8  Secure Delivery
 ↓
M9  Dynamic Watermarking
 ↓
M10 Activity + Security + Audit
 ↓
M11 Analytics + Reports
 ↓
M12 React Frontend
 ↓
M13 Security Hardening + Integration Testing
 ↓
M14 Demo Data + Documentation + Submission
```

---

# 11. Milestone 0 — Development Foundation

## Objective

Get a clean, reproducible development environment.

## Tasks

### 0.1 Verify tools

Confirm:

```text
Python
pip
Django
Django REST Framework
Node.js
npm
Docker
Docker Compose
PostgreSQL container
Git
VS Code
```

### 0.2 Verify repository

Before changing anything:

```text
Inspect:
- backend structure
- settings
- urls
- Docker files
- requirements
- environment files
- existing migrations
```

### 0.3 Establish environment configuration

Secrets/configuration belong in environment variables.

Examples:

```text
SECRET_KEY
DEBUG
DATABASE_URL
DB_NAME
DB_USER
DB_PASSWORD
DB_HOST
DB_PORT
```

Never commit real secrets.

### 0.4 Create baseline

Run:

```bash
python manage.py check
python manage.py migrate
python manage.py test
```

If no tests exist yet, that is acceptable at baseline.

## Completion criteria

- Django starts
- PostgreSQL connection works
- migrations work
- repository is clean
- baseline Git checkpoint exists

---

# 12. Milestone 1 — Organization + Custom Identity

## Objective

Replace the default Django user foundation with the AEGIS identity model.

## Organization

Create:

```text
Organization
```

Important attributes include:

```text
id: UUID
name
slug
status
created_at
updated_at
```

Exact columns must follow the approved Data Architecture.

## User

Create a custom Django user model.

Important characteristics:

```text
UUID primary key
organization relationship
email
password
active/inactive status
timestamps
```

Configure:

```python
AUTH_USER_MODEL
```

before introducing dependent application models.

## Tenant context foundation

Introduce a safe tenant-context mechanism.

The conceptual contract:

```python
request.user
      ↓
request.user.organization
      ↓
current organization
```

Do not derive tenant identity from arbitrary request parameters.

## Tests

At minimum:

```text
Organization creation
User creation
User belongs to organization
UUID identifiers
Inactive user state
Custom Django authentication model
Tenant context resolution
Cross-organization isolation foundation
```

## Stop point

Do not implement RBAC or content yet.

---

# 13. Milestone 2 — Authentication + Session Management

## Objective

Make users able to securely log in and out.

## Endpoints

Implement the approved authentication API.

Conceptually:

```text
GET  /api/v1/auth/csrf/
POST /api/v1/auth/login/
POST /api/v1/auth/logout/
GET  /api/v1/auth/me/
```

The CSRF endpoint issues the token required for unsafe session-authenticated requests. Send it in the `X-CSRFToken` header.

Login input:

```text
organization_slug
email
password
```

## Login flow

```text
Request
  ↓
Validate organization
  ↓
Validate user identity within organization
  ↓
Validate password
  ↓
Validate active status
  ↓
Create Django session
  ↓
Return authenticated user context
```

## Failure behavior

Do not reveal unnecessary information such as whether a particular email exists.

Use safe authentication failure responses.

## Session security

Configure:

```text
HttpOnly
Secure in production
SameSite policy
CSRF protection
session expiry/timeout
```

Development may use HTTP locally; production settings must enforce HTTPS-related protections.

## Audit/security

Login success/failure and logout should feed the appropriate security/audit workflows.

Authentication security events use the approved severity mapping in Data Architecture. Login attempts use the documented independent account and source-IP limits; counter state must be shared and atomic rather than process-local.

## Tests

Test:

```text
valid login
wrong password
unknown organization
inactive user
cross-organization login attempt
session creation
authenticated /me
logout
expired/invalid session
CSRF-protected unsafe requests
account and source-IP rate limits
security-event tenant/platform scope and severity
```

---

# 14. Milestone 3 — RBAC

## Objective

Implement AEGIS roles and permissions.

## Entities

```text
Role
Permission
UserRole
RolePermission
```

## Seed roles

Create:

```text
Administrator
Content Manager
Trainer
Management
```

## Permission examples

Use the approved capability-oriented model, such as:

```text
USER_VIEW
USER_CREATE
USER_UPDATE
USER_DEACTIVATE

ROLE_MANAGE

CONTENT_VIEW
CONTENT_CREATE
CONTENT_UPDATE
CONTENT_ARCHIVE
CONTENT_PUBLISH

VERSION_CREATE
VERSION_VIEW
VERSION_PUBLISH

PROGRAM_CREATE
PROGRAM_UPDATE

ACCESS_GRANT
ACCESS_REVOKE

ACTIVITY_VIEW
AUDIT_VIEW
REPORT_VIEW
ANALYTICS_VIEW
CONFIGURATION_MANAGE
```

Do not invent a huge permission catalogue.

Start with the permissions required by actual MVP workflows.

## Authorization helper

Build a reusable server-side authorization mechanism.

Conceptually:

```python
has_permission(user, "CONTENT_CREATE")
```

and/or a service-oriented equivalent.

## Important

A role is not itself a security decision.

The system evaluates:

```text
authenticated user
+
organization
+
role/permission
+
resource ownership/access
+
requested action
```

## Tests

Test every role against representative permissions.

---

# 15. Milestone 4 — Content Repository

## Objective

Create the central content-management capability.

## Content entity

Conceptually:

```text
Content
 ├── organization
 ├── title
 ├── description
 ├── status
 └── current version reference
```

Use the exact approved Data Architecture fields when implementing.

## Content operations

MVP:

```text
Create
List
Retrieve
Update metadata
Archive
```

## Upload

Content creation should eventually lead to:

```text
Content
   ↓
Content Version
   ↓
Private stored file
```

Do not make files public.

## Storage service

Introduce an abstraction such as:

```text
StorageService
```

Responsibilities:

```text
store file
retrieve protected file
delete/archive file when allowed
build internal storage key
```

The rest of AEGIS should not care whether storage is local or S3-compatible.

## Tenant isolation

A user from Organization A must never retrieve Organization B content.

## Tests

```text
content creation
content listing
metadata update
archive
tenant isolation
permission denial
invalid file input
storage metadata
```

---

# 16. Milestone 5 — Content Versioning

## Objective

Implement immutable content versions.

## Model

```text
Content
   │
   ├── Version 1
   ├── Version 2
   └── Version 3
```

## Rules

### Rule A

Published versions cannot be overwritten.

### Rule B

Changing published content creates a new version.

### Rule C

Only an appropriate published version can be delivered.

### Rule D

Historical versions remain identifiable.

## Workflow

```text
Content
  ↓
Create version
  ↓
Upload file
  ↓
Validate
  ↓
Draft
  ↓
Publish
  ↓
Current published version
```

## Tests

```text
version creation
version numbering
publishing
immutable published version
historical version retention
current version resolution
cross-content version mismatch
tenant isolation
```

---

# 17. Milestone 6 — Training Programs + Content Assignment

## Objective

Create the organizational delivery context.

## Training Program

Conceptually:

```text
Training Program
   ├── Content A
   ├── Content B
   └── Content C
```

## Content Assignment

Represents the relationship:

```text
Program
+
Content
```

It does NOT mean a user is authorized.

## Operations

```text
create program
update program
activate/deactivate
assign content
remove assignment
list program content
```

## Rules

Prevent:

```text
Content from Organization A
        +
Program from Organization B
```

## Tests

```text
program creation
content assignment
duplicate assignment prevention
tenant isolation
cross-organization rejection
inactive program behavior
```

---

# 18. Milestone 7 — Training Access

## Objective

Separate authorization from actual content usage.

The distinction is critical:

```text
Training Access
= authorization

Content Access
= actual access occurrence
```

## Access flow

```text
User
 ↓
Program
 ↓
Training Access
 ↓
Assignment exists?
 ↓
Content belongs to same organization?
 ↓
Content version deliverable?
```

## Authorization gate

For protected content:

```text
Authenticated?
    ↓ yes
Organization valid?
    ↓ yes
Permission valid?
    ↓ yes
Training Access active?
    ↓ yes
Assignment exists?
    ↓ yes
Content/version valid?
    ↓ yes
ALLOW
```

Otherwise:

```text
DENY
```

## Cross-tenant security

Where required by the API/security design, do not reveal whether another organization's resource exists. Use safe not-found behavior.

## Tests

Build explicit authorization tests before building the viewer.

---

# 19. Milestone 8 — Secure Content Delivery

## Objective

Deliver protected content through AEGIS rather than exposing the source file as a normal public download.

## Critical flow

```text
Browser
  ↓
API request
  ↓
Authentication
  ↓
Tenant resolution
  ↓
Permission check
  ↓
Training Access check
  ↓
Assignment check
  ↓
Version check
  ↓
Content Access record
  ↓
Protected delivery
  ↓
Viewer
```

## Important architecture rule

The browser never receives:

```text
public-storage-url
```

for a protected source file.

## MVP implementation strategy

Start with the simplest secure mechanism that fits the approved architecture.

Possible implementation sequence:

```text
1. Backend authorizes access
2. Backend opens private file
3. Backend generates/streams a protected representation
4. Browser renders it
5. Source storage path remains private
```

The exact presentation mechanism should be selected based on the supported content format and the approved API design.

Do not pretend browser viewing makes copying technically impossible.

The security claim should be:

> AEGIS avoids normal uncontrolled source-file distribution and places authorization, tracking and watermarking around protected delivery.

## Tests

```text
authorized delivery
unauthorized delivery
expired/revoked access
wrong organization
wrong version
missing content
private storage inaccessible directly
```

---

# 20. Milestone 9 — Dynamic Watermarking

## Objective

Make delivered content traceable to the accessing user/context.

## Watermark information

Generate at delivery time using information such as:

```text
user identity
organization identity
access/session context
timestamp
content/version context
```

Only use information approved by the project's security/privacy design.

## Important design rule

Do not create a permanent `watermarks` table for the MVP unless a later requirement actually needs persistent watermark records.

The watermark is a delivery-time protection mechanism.

## Flow

```text
Authorized Access
       ↓
Resolve User + Organization
       ↓
Resolve Content Version
       ↓
Generate Watermark
       ↓
Deliver Protected Representation
```

## Tests

Verify:

```text
watermark generated
watermark corresponds to current user
watermark changes appropriately per access context
unauthorized users never reach watermark generation
```

---

# 21. Milestone 10 — Activity + Security + Audit

## Objective

Make AEGIS accountable.

## Activity events

Capture meaningful viewer/user activity.

Example allowlisted events:

```text
VIEWER_OPENED
VIEWER_CLOSED
SLIDE_NEXT
SLIDE_PREVIOUS
SLIDE_JUMP
PAUSED
RESUMED
```

Only implement events actually required by the MVP.

Client activity must not become a generic arbitrary event injection API.

## Security events

Examples:

```text
LOGIN_SUCCESS
LOGIN_FAILURE
LOGOUT
ACCESS_DENIED
SUSPICIOUS_ACCESS
```

Security events are generated by trusted backend logic.

## Audit records

Examples:

```text
USER_CREATED
USER_DEACTIVATED
CONTENT_CREATED
CONTENT_UPDATED
CONTENT_ARCHIVED
VERSION_CREATED
VERSION_PUBLISHED
PROGRAM_CREATED
ACCESS_GRANTED
ACCESS_REVOKED
```

Audit records are append-only.

Do not provide arbitrary update/delete APIs for audit history.

## Tests

Verify that important workflows create the expected records.

---

# 22. Milestone 11 — Basic Analytics + Reports

## Objective

Turn the accumulated activity/access data into useful management information.

## MVP analytics

Start with simple server-side aggregates:

```text
total content views
most viewed content
active users
access frequency
session counts
average session duration where reliable
recent activity
version usage
```

## Reports

At minimum:

```text
User Activity Report
Content Usage Report
Access Report
Version History Report
Audit Report
```

## Design principle

Do not build a separate analytics engine for the MVP.

Use PostgreSQL queries/aggregations through service/query layers.

---

# 23. Milestone 12 — React Frontend

Only begin the full frontend after the backend workflows are stable enough to consume.

## Suggested structure

```text
frontend/
├── src/
│   ├── api/
│   ├── auth/
│   ├── components/
│   ├── layouts/
│   ├── pages/
│   ├── routes/
│   ├── features/
│   │   ├── users/
│   │   ├── content/
│   │   ├── programs/
│   │   ├── access/
│   │   ├── viewer/
│   │   ├── analytics/
│   │   └── audit/
│   └── App.jsx
```

## Frontend responsibilities

React handles:

```text
presentation
navigation
form handling
API communication
loading/error states
permission-aware UI
viewer UI
dashboards
```

React does NOT own:

```text
authorization
tenant isolation
security decisions
business-rule enforcement
```

---

# 24. Frontend Page Order

Build pages in this order.

## Authentication

```text
Login
```

## Administration

```text
Dashboard
Users
Roles / Permissions
Organization configuration
```

## Content

```text
Content list
Content creation
Content details
Version history
Version publishing
```

## Programs

```text
Program list
Program creation
Program details
Content assignment
```

## Access

```text
Access management
```

## Secure viewer

```text
Content viewer
```

## Accountability

```text
Activity
Audit
Analytics
Reports
```

This mirrors the backend dependency chain.

---

# 25. Milestone 13 — Security Hardening

Before calling the MVP complete, perform a dedicated security pass.

## Authentication

Verify:

```text
password hashing
session security
CSRF
session timeout
inactive-user rejection
safe authentication errors
```

## Authorization

Attempt:

```text
User → admin endpoint
Trainer → content management endpoint
Management → content mutation endpoint
cross-organization access
direct object ID manipulation
```

Every attempt should produce the correct result.

## Tenant isolation

Create:

```text
Organization A
Organization B
```

Then deliberately attempt:

```text
A user → B user
A user → B content
A user → B program
A user → B access
A user → B activity
```

All must be denied.

## Storage

Attempt to access protected files without authorization.

There must be no public raw-file route.

## Audit

Attempt to mutate historical audit records.

The API must not permit it.

---

# 26. Milestone 14 — Integration Testing

Create an end-to-end test scenario.

## Scenario

```text
1. Create Organization A
2. Create Administrator
3. Create Content Manager
4. Create Trainer
5. Create Management user
6. Login as Administrator
7. Create content
8. Upload Version 1
9. Publish Version 1
10. Create Training Program
11. Assign content
12. Grant Trainer access
13. Login as Trainer
14. Open protected content
15. Generate content access
16. Generate watermark
17. Record activity
18. Login as Management
19. View analytics
20. View audit report
```

Then repeat with Organization B and verify isolation.

---

# 27. Suggested Test Pyramid

We will not rely only on manual testing.

## Unit tests

Test:

```text
business rules
permissions
version rules
tenant validation
watermark generation
service methods
```

## API tests

Test:

```text
authentication
authorization
CRUD
validation
HTTP status codes
tenant isolation
```

## Integration tests

Test complete flows:

```text
content → version → program → access → delivery
```

## Manual verification

Use the browser for:

```text
login
navigation
content management
viewer
dashboard
reports
```

---

# 28. API Implementation Discipline

Every endpoint should answer:

```text
Who can call this?
Which organization does it operate in?
What validation is required?
What business service executes it?
What data may be returned?
What events must be recorded?
What happens on failure?
```

For every endpoint we should document:

```text
Method
Path
Authentication
Permission
Tenant scope
Request
Response
Validation
Errors
Side effects
Audit/activity behavior
```

---

# 29. Database Migration Discipline

After every model change:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py check
```

Then run tests.

Never make schema changes only manually inside PostgreSQL.

Django migrations remain the source-controlled schema history.

---

# 30. Development Checkpoint Discipline

At the end of every milestone:

```bash
git status
git diff
python manage.py check
python manage.py test
```

Then create a Git checkpoint.

Example:

```text
M0-foundation
M1-identity
M2-auth
M3-rbac
M4-content
...
```

This makes it easy to recover from mistakes.

---

# 31. Environment Strategy

## Local development

```text
VS Code
   ↓
Django
   ↓
Docker PostgreSQL
   ↓
Local private file storage
```

## Future deployment

Potentially:

```text
React
   ↓
Nginx / HTTPS
   ↓
Django
   ├── PostgreSQL
   └── S3-compatible storage
```

Deployment complexity should not delay the MVP.

---

# 32. What We Will NOT Build Before the MVP Works

Do not get distracted by:

```text
AI
DRM
mobile
offline sync
SSO
LDAP
cloud integrations
microservices
Redis
Celery
event buses
complex deployment automation
advanced observability
```

These are future architectural directions, not MVP blockers.

---

# 33. Definition of Done for a Milestone

A milestone is complete only when:

```text
[ ] Code implemented
[ ] Business rules respected
[ ] Tenant isolation considered
[ ] Authorization implemented
[ ] Validation implemented
[ ] Error handling implemented
[ ] Tests written
[ ] Tests passing
[ ] Django checks passing
[ ] Migrations applied
[ ] Manual verification completed where applicable
[ ] Git checkpoint created
[ ] No unrelated files changed
[ ] We understand what was built
```

The last point matters most for the MCA project.

---

# 34. Definition of Done for the MVP

The MVP is ready for submission/demo when:

## Functional

```text
[ ] Organization exists
[ ] Users can authenticate
[ ] Roles and permissions work
[ ] Admin can manage users
[ ] Content can be created
[ ] Content can be uploaded
[ ] Versions can be created
[ ] Versions can be published
[ ] Programs can be created
[ ] Content can be assigned
[ ] Access can be granted/revoked
[ ] Authorized users can view content
[ ] Unauthorized users cannot view content
[ ] Watermark is generated
[ ] Activity is recorded
[ ] Security events are recorded
[ ] Audit records are recorded
[ ] Analytics work
[ ] Reports work
```

## Security

```text
[ ] Tenant isolation tested
[ ] Server-side authorization tested
[ ] Session security tested
[ ] CSRF protection tested
[ ] Private storage verified
[ ] Raw source files not publicly exposed
[ ] Audit history protected
```

## Quality

```text
[ ] Tests passing
[ ] No obvious console/server errors
[ ] Database migrations clean
[ ] Environment secrets excluded
[ ] README updated
[ ] Setup instructions verified
```

## Demo

```text
[ ] Clean demo organization
[ ] Demo users
[ ] Demo content
[ ] Published version
[ ] Program
[ ] Assignment/access
[ ] Viewer
[ ] Watermark
[ ] Activity
[ ] Audit
[ ] Analytics
```

---

# 35. MCA Demonstration Story

The strongest demonstration is not a collection of disconnected CRUD screens.

Tell the story through the original problem.

## Step 1 — Show the problem

Explain:

```text
Traditional approach:
Organization
   ↓
File sharing
   ↓
Trainer receives source file
   ↓
File can be copied/shared
   ↓
Limited visibility
```

## Step 2 — Show AEGIS

```text
Organization
   ↓
AEGIS
   ↓
Controlled content
   ↓
Version
   ↓
Program
   ↓
Access
   ↓
Secure viewer
   ↓
Watermark
   ↓
Activity
   ↓
Audit
```

## Step 3 — Demonstrate security

Use two organizations.

Show:

```text
Organization A trainer
       X
Organization B content
```

Then show that the backend rejects the attempt.

## Step 4 — Demonstrate versioning

Show:

```text
V1 published
   ↓
V2 created
   ↓
V2 published
```

Then show historical V1 still exists but is not silently overwritten.

## Step 5 — Demonstrate accountability

Open content and show:

```text
Content Access
Activity
Security/Audit
```

## Step 6 — Demonstrate management value

Show:

```text
Analytics
Reports
Audit
```

This connects the technical implementation back to the original project objective.

---

# 36. Timeline to 1 November 2026

Current date for this plan:

**8 October 2026**

Available time is approximately three and a half weeks.

We therefore prioritize the **core vertical slice first**.

## 8–10 October

```text
M0 Development Foundation
M1 Organization + Custom Identity
```

Target:

```text
Django
+
PostgreSQL
+
Organization
+
Custom User
```

---

## 11–13 October

```text
M2 Authentication
M3 RBAC
```

Target:

```text
Login
Logout
Session
Roles
Permissions
```

---

## 14–17 October

```text
M4 Content Repository
M5 Content Versioning
```

Target:

```text
Create content
Upload
Version
Publish
Archive
```

---

## 18–20 October

```text
M6 Training Programs
M7 Training Access
```

Target:

```text
Program
Assignment
Trainer access
Authorization
```

---

## 21–24 October

```text
M8 Secure Delivery
M9 Watermarking
```

Target:

```text
Authorized viewer
Private source
Watermark
Content access tracking
```

This is the most important technical demonstration.

---

## 25–27 October

```text
M10 Activity
M10 Security
M10 Audit
M11 Analytics
M11 Reports
```

Target:

```text
Accountability
Usage visibility
Management reporting
```

---

## 28–29 October

```text
M12 React Frontend integration
```

Target:

```text
Complete usable UI
```

---

## 30 October

```text
M13 Security Hardening
M14 Integration Testing
```

Target:

```text
Cross-tenant testing
Authorization testing
End-to-end testing
Bug fixes
```

---

## 31 October

```text
Demo data
README
Architecture diagrams
Screenshots
API documentation
Final test run
Final backup
Presentation preparation
```

---

## 1 November

```text
SUBMISSION / DEMONSTRATION
```

No major new feature should be started on 1 November.

---

# 37. Risk-Control Strategy

Because the deadline is close, we use a priority hierarchy.

## P0 — Must work

```text
Authentication
Organization isolation
RBAC
Content
Versioning
Program
Assignment
Access
Secure delivery
Watermark
Activity
Audit
```

## P1 — Should work

```text
Analytics
Reports
Polished React UI
Advanced filtering/search
```

## P2 — Nice to have

```text
advanced dashboards
complex charts
extra content formats
advanced reporting
```

If time becomes tight, cut P2 first.

Never sacrifice tenant isolation or authorization just to make the UI prettier.

---

# 38. Practical Working Method — How We Will Build It Together

For every milestone, we will work in this exact pattern.

## Step A — You ask

Example:

> Bro, let's start Milestone 1.

## Step B — We inspect

We first inspect the relevant existing files.

## Step C — I explain

Before coding, I explain:

```text
What are we building?
Why is it needed?
How does it fit the architecture?
Which files will change?
```

## Step D — We implement

I provide the exact code and commands needed.

You apply/run them in VS Code.

## Step E — We verify

We run:

```bash
python manage.py check
python manage.py test
```

and any milestone-specific commands.

## Step F — We inspect the result

You share errors/output when needed.

We fix them before moving on.

## Step G — We checkpoint

Once stable:

```text
Milestone complete
```

Then move forward.

---

# 39. First Implementation Session

Do not start by creating all Django apps.

Our first actual development session should be:

```text
1. Inspect current repository
2. Verify Docker/PostgreSQL
3. Verify Django
4. Inspect current settings
5. Inspect current URLs
6. Inspect requirements
7. Confirm existing migrations
8. Establish baseline
9. Create Git checkpoint
10. Begin M0
```

Then:

```text
M0
 ↓
M1
```

Only after the custom user foundation is correct do we add dependent business entities.

---

# 40. First Concrete Coding Target

The first meaningful AEGIS database structure will be:

```text
organizations
      │
      ▼
users
```

Then:

```text
users
  │
  └── roles
        │
        └── permissions
```

Then:

```text
content
   │
   └── content_versions
```

Then:

```text
training_programs
        │
        ▼
content_assignments
        │
        ▼
training_access
```

Then:

```text
content_access
      │
 ┌────┼────┐
 ▼    ▼    ▼
activity security audit
```

This is the implementation spine of AEGIS.

---

# 41. Final Development Principle

The most important principle for this project is:

> **Do not build features merely because they can be built. Build each feature because it implements an approved business/domain rule and fits the architecture.**

The final MVP should therefore be:

```text
Small enough to finish
        +
Secure enough to demonstrate
        +
Structured enough to maintain
        +
Complete enough to prove the idea
        +
Understandable enough for the developer to explain
```

That developer is you.

We are not outsourcing the thinking to an AI coding agent.

We will build AEGIS deliberately, one layer at a time, in VS Code.

---

# 42. Current Status

```text
Product Design                 ✅
PRD                            ✅
SRS                            ✅
Domain Model                   ✅
Business Rules                 ✅
ADRs                           ✅
Functional Architecture        ✅
Data Architecture              ✅
System Architecture            ✅
API Specification              ✅

Implementation                 ⬅ NOW
```

## Immediate next step

Start with:

```text
M0 — Development Foundation
```

Then proceed to:

```text
M1 — Organization + Custom Identity
```

Do not implement later milestones until M0/M1 are stable.

---

# Appendix A — Quick Command Checklist

## Backend

```bash
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py test
python manage.py runserver
```

## Frontend

```bash
npm install
npm run dev
```

Use the commands appropriate to the repository's actual package/setup.

---

# Appendix B — Core Security Checklist

For every protected request:

```text
[ ] Authenticated?
[ ] Active user?
[ ] Organization resolved from identity?
[ ] Resource belongs to organization?
[ ] Required permission?
[ ] Required business access?
[ ] Resource/version valid?
[ ] Protected data exposed only through approved delivery path?
[ ] Activity/security/audit event required?
```

If any answer is no:

```text
DENY
```

---

# Appendix C — Things to Ask Before Adding a New Feature

Before implementing anything new, ask:

1. Is it in the approved MVP scope?
2. Which functional module owns it?
3. Which domain entity represents it?
4. Which business rule requires it?
5. Which organization owns it?
6. Who is authorized to use it?
7. What data does it create/change?
8. Does it require an audit/security event?
9. Does it expose protected content?
10. Does it affect existing architecture?
11. Does it require a new dependency?
12. Can the feature wait until after submission?

If the answer is unclear, stop and clarify before coding.

---

**End of AEGIS MVP Implementation & Development Guide**
