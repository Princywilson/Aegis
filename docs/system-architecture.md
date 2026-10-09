# AEGIS

# Phase 4 — System Architecture

**Project:** AEGIS — Enterprise Knowledge Protection and Delivery Platform

**Document:** System Architecture / System Design

**Phase:** Phase 4 — System Architecture

**Status:** Baseline

**Technology Direction:** React + Python Django + PostgreSQL + Object Storage

---

# 1. Purpose

This document defines the technical architecture of AEGIS.

The purpose of the System Architecture is to answer:

> **How does the entire AEGIS system work technically?**
> 

Phase 1 defined the business/domain concepts.

Phase 2 defined the functional modules and their responsibilities.

Phase 3 defined the data architecture and database structure.

Phase 4 now defines how these pieces operate together as one complete system.

This document covers:

- System components
- Component responsibilities
- Application architecture
- Communication between components
- Authentication
- Authorization
- Tenant isolation
- Secure content delivery
- Content storage
- Activity tracking
- Audit logging
- Security boundaries
- Deployment architecture
- Infrastructure
- Scalability
- Reliability
- Monitoring
- Future architectural evolution

It does not redefine:

- Product requirements
- Domain entities
- Functional module requirements
- Database tables and columns
- Detailed API contracts
- UI/UX design

Those are defined in their respective project phases.

---

# 2. Architectural Goals

The AEGIS architecture is designed around the following goals.

## 2.1 Security First

The primary architectural concern is protecting proprietary organizational training content.

The architecture must prevent ordinary users from directly obtaining protected source files merely because they are authorized to view the content.

The project proposal identifies the need for secure content delivery, access monitoring, role-based authentication, dynamic watermarking and activity tracking.

---

## 2.2 Multi-Tenant SaaS

AEGIS is designed as a platform that can eventually serve multiple organizations.

The organization is therefore treated as the fundamental tenant boundary.

Conceptually:

```
                    AEGIS
                      │
       ┌──────────────┼──────────────┐
       │              │              │
       ▼              ▼              ▼
 Organization A  Organization B  Organization C
       │              │              │
       ▼              ▼              ▼
    Resources      Resources      Resources
```

One organization's users, content, programs and activity must not become accessible to another organization.

---

## 2.3 Controlled Content Delivery

Training content should normally be consumed through AEGIS rather than distributed as unrestricted presentation files.

```
Traditional Model

Organization
     │
     ▼
Presentation File
     │
     ▼
Trainer
     │
     ▼
Uncontrolled Copying

AEGIS Model

Organization
     │
     ▼
Protected Content
     │
     ▼
AEGIS Secure Delivery
     │
     ▼
Authorized Trainer
     │
     ▼
Tracked Activity
```

This directly addresses the original problem identified for AEGIS.

---

## 2.4 Separation of Responsibilities

The architecture should separate:

```
Presentation
     ↓
Frontend

Application Logic
     ↓
Django Backend

Business Data
     ↓
PostgreSQL

Large Protected Files
     ↓
Object Storage

Observability / Accountability
     ↓
Activity + Audit + Logs
```

This prevents individual components from becoming responsible for unrelated concerns.

---

## 2.5 Scalability

The architecture should support the MCA MVP while allowing the system to evolve into a production SaaS platform.

The initial architecture should therefore avoid unnecessary distributed-system complexity while keeping the major boundaries clear.

---

# 3. High-Level System Architecture

The high-level AEGIS architecture is:

```
                         ┌─────────────────────────┐
                         │         Users           │
                         │                         │
                         │  Administrator          │
                         │  Trainer                │
                         └────────────┬────────────┘
                                      │
                                      │ HTTPS
                                      ▼
                         ┌─────────────────────────┐
                         │       Web Browser       │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │      React Frontend     │
                         │                         │
                         │ UI / Routing / State    │
                         │ API Communication       │
                         └────────────┬────────────┘
                                      │
                                      │ HTTPS / API
                                      ▼
                 ┌──────────────────────────────────────────┐
                 │              Django Backend              │
                 │                                          │
                 │ Authentication                           │
                 │ Authorization                            │
                 │ Tenant Context                           │
                 │ Business Logic                           │
                 │ Content Management                       │
                 │ Version Management                       │
                 │ Training Management                      │
                 │ Secure Content Delivery                  │
                 │ Activity Tracking                        │
                 │ Audit                                    │
                 └──────────────┬───────────────┬───────────┘
                                │               │
                       Database │               │ File Access
                                │               │
                                ▼               ▼
                  ┌──────────────────┐   ┌──────────────────┐
                  │   PostgreSQL     │   │ Object Storage  │
                  │                  │   │                  │
                  │ Business Data    │   │ Protected Files │
                  │ Tenant Data      │   │ Content Versions│
                  │ Access Data      │   │                 │
                  │ Activity/Audit   │   │                 │
                  └──────────────────┘   └──────────────────┘

                                │
                                ▼
                     ┌────────────────────┐
                     │ Logging /          │
                     │ Monitoring         │
                     │                    │
                     │ Application Logs   │
                     │ Security Events    │
                     │ System Metrics     │
                     └────────────────────┘
```

The important architectural principle is:

> **The browser never communicates directly with the protected database or unrestricted object storage.**
> 

---

# 4. Architectural Style

AEGIS will initially follow a **layered web application architecture with a modular Django backend**.

Conceptually:

```
┌───────────────────────────────────────────┐
│              Presentation Layer           │
│                                           │
│              React Frontend               │
└──────────────────────┬────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────┐
│                 API Layer                 │
│                                           │
│       Django API / Request Handling       │
└──────────────────────┬────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────┐
│             Application Layer             │
│                                           │
│ Authentication                            │
│ Authorization                             │
│ Content Management                        │
│ Training Management                       │
│ Access Management                         │
│ Activity / Audit                          │
└──────────────────────┬────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────┐
│              Domain / Service Layer       │
│                                           │
│ Business Rules                            │
│ Access Decisions                          │
│ Content Lifecycle                         │
│ Version Rules                             │
│ Tenant Rules                              │
└──────────────────────┬────────────────────┘
                       │
             ┌─────────┴──────────┐
             ▼                    ▼
┌──────────────────────┐  ┌──────────────────────┐
│    Data Access       │  │   Storage Service    │
│                      │  │                      │
│    PostgreSQL        │  │    Object Storage    │
└──────────────────────┘  └──────────────────────┘
```

The architecture is **modular**, but the MVP does not require microservices.

---

# 5. Major System Components

AEGIS consists of the following major technical components.

```
1. Client / Browser
2. React Frontend
3. Django Application
4. Authentication Component
5. Authorization Component
6. Tenant Context / Isolation Component
7. Content Management Component
8. Content Versioning Component
9. Secure Content Delivery Component
10. Training Access Component
11. Activity Tracking Component
12. Audit Component
13. PostgreSQL Database
14. Object Storage
15. Logging / Monitoring Infrastructure
16. Deployment Infrastructure
```

---

# 6. Component Responsibilities

## 6.1 Web Browser

The browser is the client environment used by administrators and trainers.

### Responsibilities

- Render the AEGIS interface
- Collect user input
- Display authorized information
- Communicate with the backend
- Display protected training content
- Maintain client-side session state where appropriate

### Security Boundary

The browser is considered an **untrusted environment**.

Therefore:

> No security-critical decision may rely solely on the browser.
> 

The browser can control presentation and user experience, but the backend remains responsible for security enforcement.

---

# 7. React Frontend

React is the presentation layer of AEGIS.

The frontend communicates with the Django backend through authenticated HTTPS requests.

### Responsibilities

- Application UI
- Navigation
- Forms
- Dashboards
- Content management interfaces
- Training interfaces
- Content viewing interface
- User management interface
- Activity/audit views
- Client-side state management
- Displaying authorization-dependent UI

### Important Boundary

Frontend permission checks are primarily for user experience.

They are **not the actual security boundary**.

For example:

```
React

"Hide Delete button"

       ≠

Backend

"User is not authorized to delete"
```

The backend must always enforce the second condition.

---

# 8. Django Backend

Django is the core application layer of AEGIS.

The project proposal identifies Python Django as the backend technology.

The Django backend acts as the central trust boundary of the application.

### Responsibilities

- Request processing
- Authentication
- Authorization
- Tenant identification
- Business-rule enforcement
- Content management
- Version management
- Training-program management
- Access management
- Secure content delivery
- Activity tracking
- Audit generation
- Database interaction
- Object-storage interaction
- Security-event processing

Conceptually:

```
                   Django
                     │
       ┌─────────────┼─────────────┐
       │             │             │
       ▼             ▼             ▼
 Authentication  Authorization  Business Logic
       │             │             │
       └─────────────┼─────────────┘
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
    Database      Storage       Audit/Activity
```

---

# 9. Backend Modular Structure

Although AEGIS is initially a single deployable application, the Django backend should be internally modular.

Conceptually:

```
AEGIS Backend
│
├── Authentication
│
├── Organization
│
├── Users & Roles
│
├── Content
│
├── Content Versioning
│
├── Training Programs
│
├── Assignments
│
├── Training Access
│
├── Secure Content Delivery
│
├── Activity Tracking
│
├── Audit
│
└── Analytics
```

This provides clear module boundaries without introducing the operational overhead of microservices.

---

# 10. Authentication Architecture

Authentication establishes:

> **Who is this user?**
> 

The initial architecture uses Django's authentication capabilities as the foundation.

The authentication flow is conceptually:

```
User
 │
 │ Credentials
 ▼
React Frontend
 │
 │ HTTPS
 ▼
Django Authentication
 │
 ├── Validate identity
 │
 ├── Establish authenticated session
 │
 └── Create security context
          │
          ▼
       Authenticated User
```

Unauthenticated users must not be able to access protected AEGIS resources.

---

# 11. Authentication Security Boundary

The authentication system establishes the initial trust boundary.

```
UNAUTHENTICATED
       │
       │ Login
       ▼
AUTHENTICATED
       │
       ▼
Organization Context
       │
       ▼
Authorization
       │
       ▼
Protected Resource
```

Authentication alone does not grant access to organizational content.

This distinction is fundamental.

```
Authentication
    =
"Who are you?"

Authorization
    =
"What are you allowed to do?"
```

---

# 12. Authorization Architecture

Authorization determines whether an authenticated user can perform a requested action.

The authorization decision must be performed server-side.

Conceptually:

```
Request
   │
   ▼
Authenticated?
   │
   ├── No ──→ Deny
   │
   ▼
Organization Context Valid?
   │
   ├── No ──→ Deny
   │
   ▼
Permission Valid?
   │
   ├── No ──→ Deny
   │
   ▼
Resource Access Valid?
   │
   ├── No ──→ Deny
   │
   ▼
Allow Operation
```

---

# 13. Tenant Context

Every organization-owned request must execute within an organization context.

Conceptually:

```
Authenticated User
        │
        ▼
Organization Membership
        │
        ▼
Current Organization Context
        │
        ▼
Resource Query / Operation
```

The backend must ensure that requested resources belong to the user's authorized organization.

---

# 14. Tenant Isolation

The initial architecture uses logical tenant isolation.

Conceptually:

```
                   AEGIS
                     │
             Shared Application
                     │
             Shared PostgreSQL
                     │
       ┌─────────────┼─────────────┐
       │             │             │
       ▼             ▼             ▼
     Org A         Org B         Org C
       │             │             │
       ▼             ▼             ▼
    Data A         Data B        Data C
```

A request associated with Organization A must not retrieve Organization B's resources.

Tenant isolation must therefore be enforced consistently by the backend.

---

# 15. Database Architecture

PostgreSQL is the primary relational data store for AEGIS.

The database stores structured business information such as:

```
Organization information
User information
Roles / permissions
Content metadata
Content version metadata
Training programs
Assignments
Access information
Activity records
Audit records
Security-related information
```

The database does **not** serve as the primary location for large training files.

Those are stored in object storage.

---

# 16. Object Storage Architecture

Training content files are stored separately from relational business data.

Conceptually:

```
                   Django
                     │
             ┌───────┴───────┐
             │               │
             ▼               ▼
       PostgreSQL       Object Storage
             │               │
             │               ├── Content V1
             │               ├── Content V2
             │               └── Content V3
             │
             └── Metadata / References
```

The database maintains the business context and metadata associated with the stored content.

---

# 17. Object Storage Security

Object storage must not become an alternate path around AEGIS authorization.

Therefore:

```
Browser
   │
   │  X
   └──────────────→ Object Storage
```

The browser should not receive unrestricted permanent storage access.

Instead:

```
Browser
   │
   │ Authorized Request
   ▼
Django
   │
   │ Validate:
   │ - Authentication
   │ - Organization
   │ - Permission
   │ - Content Access
   │ - Version
   ▼
Secure Content Delivery
   │
   ▼
Protected Content
```

Any temporary delivery mechanism must still be generated only after authorization.

---

# 18. Secure Content Delivery Architecture

Secure content delivery is one of the most important components of AEGIS.

The goal is:

> **Allow an authorized trainer to consume protected training material without treating the original source file as an ordinary downloadable resource.**
> 

Conceptually:

```
Trainer
   │
   ▼
React Content Viewer
   │
   ▼
Django
   │
   ├── Authenticate
   ├── Identify Organization
   ├── Check Permission
   ├── Check Training Access
   ├── Identify Content
   ├── Identify Version
   └── Record Access
          │
          ▼
   Secure Delivery Layer
          │
          ▼
   Object Storage
          │
          ▼
   Protected Content
```

---

# 19. Content Delivery Security Principle

The system should distinguish between:

```
Source File
    ↓
Protected Storage

and

Displayed Content
    ↓
Controlled Presentation
```

The source file should remain protected inside the server/storage boundary.

The user should receive only what is necessary for the authorized training experience.

---

# 20. Content Delivery and Watermarking

Dynamic watermarking forms an additional content-protection layer.

Conceptually:

```
Content Version
      │
      ▼
Secure Delivery
      │
      ▼
Access Context
      │
      ├── User
      ├── Organization
      └── Session / Access Context
      │
      ▼
Dynamic Watermark
      │
      ▼
Displayed Training Content
```

The watermark should help associate displayed content with the authorized access context.

Dynamic watermarking is explicitly identified as part of the proposed AEGIS solution.

---

# 21. Watermark Security Boundary

Watermarking is a protection and accountability mechanism.

It should **not** be treated as complete DRM.

```
Dynamic Watermarking
        │
        ├── Deterrence
        ├── Accountability
        └── Traceability

        ≠

Full DRM
```

Advanced DRM-inspired capabilities remain future scope.

---

# 22. Content Version Architecture

Content and Content Version remain separate concepts.

```
Content
   │
   ├── Version 1
   ├── Version 2
   └── Version 3
```

The application determines which version is currently approved for delivery.

Published versions should be treated as immutable historical records.

If content changes:

```
Existing Version
       │
       ▼
Historical Version

New Content Change
       │
       ▼
New Version
```

The architecture must therefore preserve historical access information.

---

# 23. Training Access Architecture

Training access acts as the authorization layer between users and protected training resources.

Conceptually:

```
User
 │
 ▼
Organization Membership
 │
 ▼
Role / Permission
 │
 ▼
Training Access
 │
 ▼
Training Program
 │
 ▼
Content Assignment
 │
 ▼
Content
 │
 ▼
Content Version
```

Only when the complete authorization chain is valid should protected content be delivered.

---

# 24. Activity Tracking Architecture

Activity tracking records relevant user interactions with the system.

Conceptually:

```
User Action
    │
    ▼
Django Backend
    │
    ├── Process Action
    │
    └── Generate Activity Event
              │
              ▼
        Activity Storage
```

Examples include:

- Content access
- Content viewing
- Training-related interactions
- Access attempts
- Other significant trainer interactions

The project proposal explicitly identifies access logging and trainer activity tracking as core capabilities.

---

# 25. Audit Architecture

Audit is separate from ordinary activity tracking.

```
Activity
   =
Normal system/user interaction

Audit
   =
Important business/security event
```

The architecture should generate audit records for significant actions such as:

```
Login
Content creation
Content modification
Version creation
Version publication
Access grant
Access revocation
Permission changes
Protected content access
Security events
```

Audit information should be treated as historical evidence.

---

# 26. Activity and Audit Flow

```
                         User Action
                              │
                              ▼
                         Django API
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
              Business Action      Security Check
                    │                   │
                    ▼                   ▼
                 Activity            Audit Event
                    │                   │
                    └─────────┬─────────┘
                              ▼
                         PostgreSQL
```

The system should not depend solely on frontend-generated activity information for security-sensitive events.

---

# 27. Security Event Architecture

Security-sensitive events should be identifiable independently from ordinary user activity.

Examples:

```
Failed authentication
Unauthorized access attempt
Permission denial
Invalid resource access
Suspicious access behavior
Security-related session event
```

Conceptually:

```
Security Event
      │
      ├── Record
      ├── Audit
      └── Monitoring / Alerting
```

The exact security-event taxonomy can evolve as the system matures.

Security events use one model with explicit scope. Events are tenant-scoped when an organization has been resolved and platform-scoped when tenant resolution has not occurred; the latter use a null `organization_id`. Platform-level events must not be visible through organization-level monitoring. Activity events remain tenant-scoped and require an organization.

Authentication event metadata must be minimal and sanitized, and must never include passwords, session tokens, or other secrets. Use `INFO` for `LOGIN_SUCCESS` and `LOGOUT`, and `MEDIUM` for `LOGIN_FAILURE`, including rate-limit triggers. Login limits use shared PostgreSQL-backed atomic counters: five failed account attempts or twenty failed source-IP attempts in a rolling 15-minute window cause a 15-minute temporary block. Successful login clears only the account counter. Rate-limit responses remain generic. Do not trust forwarded-IP headers unless their proxy is explicitly trusted.

---

# 28. End-to-End Authentication and Content Access Flow

The complete trainer access flow is:

```
Trainer
   │
   ▼
React Frontend
   │
   │ Login
   ▼
Django Authentication
   │
   ▼
Authenticated Session
   │
   ▼
Organization Context
   │
   ▼
Authorization
   │
   ▼
Training Access Validation
   │
   ▼
Content Assignment Validation
   │
   ▼
Content Validation
   │
   ▼
Current / Authorized Version
   │
   ▼
Secure Content Delivery
   │
   ├── Watermark
   │
   └── Access Record
   │
   ▼
Protected Content Viewer
   │
   ▼
Activity Tracking
   │
   ▼
Audit / Monitoring
```

This is the central technical flow of AEGIS.

---

# 29. Administrator Content Management Flow

An administrator managing content follows a different flow.

```
Administrator
      │
      ▼
React Frontend
      │
      ▼
Django Authentication
      │
      ▼
Organization Context
      │
      ▼
Permission Validation
      │
      ▼
Content Management
      │
      ├───────────────┐
      ▼               ▼
PostgreSQL       Object Storage
      │               │
      └───────┬───────┘
              ▼
        Version Created
              │
              ▼
         Audit Event
```

The administrator's UI does not bypass the same authorization boundary used elsewhere in the system.

---

# 30. Communication Architecture

The major communication paths are:

```
Browser
   │
   │ HTTPS
   ▼
React
   │
   │ HTTPS / API
   ▼
Django
   │
   ├──────────────→ PostgreSQL
   │
   ├──────────────→ Object Storage
   │
   └──────────────→ Logging / Monitoring
```

There should be no direct browser-to-database communication.

There should also be no uncontrolled browser-to-storage communication.

---

# 31. API Communication

React communicates with Django through defined application APIs.

Conceptually:

```
React
  │
  ├── Authentication API
  ├── Organization API
  ├── User/Role API
  ├── Content API
  ├── Version API
  ├── Training Program API
  ├── Access API
  ├── Activity API
  └── Audit API
          │
          ▼
       Django
```

Detailed API endpoints, request structures and response formats belong to **Phase 5 — API Design**.

---

# 32. Request Processing Pipeline

A protected request should conceptually pass through:

```
HTTP Request
     │
     ▼
Web/API Layer
     │
     ▼
Authentication
     │
     ▼
Tenant Context
     │
     ▼
Authorization
     │
     ▼
Business Rules
     │
     ▼
Application Service
     │
     ├──────────────┐
     ▼              ▼
PostgreSQL     Object Storage
     │              │
     └──────┬───────┘
            ▼
       Response
            │
            ▼
        React UI
```

This pipeline establishes a consistent security boundary for the application.

---

# 33. Security Architecture

Security in AEGIS should be treated as a cross-cutting architectural concern.

```
                 ┌──────────────────────────┐
                 │       Security Layer      │
                 │                          │
                 │ Authentication           │
                 │ Authorization            │
                 │ Tenant Isolation         │
                 │ Secure Sessions          │
                 │ Content Protection       │
                 │ Watermarking             │
                 │ Audit                    │
                 │ Security Events          │
                 │ Secure Storage           │
                 └────────────┬─────────────┘
                              │
                              ▼
                    AEGIS Application
```

---

# 34. Security Boundaries

The major security boundaries are:

## Boundary 1 — Internet → Application

```
Internet
   │
 HTTPS
   ▼
AEGIS Application
```

TLS/HTTPS protects communication between clients and the application.

---

## Boundary 2 — User → Protected Resource

```
User
 │
 ▼
Authentication
 │
 ▼
Authorization
 │
 ▼
Protected Resource
```

---

## Boundary 3 — Application → Database

```
Django
   │
   ▼
PostgreSQL
```

The database should not be publicly exposed as a client-accessible service.

---

## Boundary 4 — Application → Object Storage

```
Django
   │
   ▼
Object Storage
```

Protected content must remain behind application-controlled access.

---

## Boundary 5 — Organization → Organization

```
Organization A
      X
Organization B
```

Cross-tenant access must be prevented.

---

# 35. Trust Zones

AEGIS can be conceptually divided into trust zones.

```
┌───────────────────────────────────────────────┐
│                 UNTRUSTED ZONE                │
│                                               │
│ Browser / Client                              │
└──────────────────────┬────────────────────────┘
                       │
                    HTTPS
                       │
                       ▼
┌───────────────────────────────────────────────┐
│               APPLICATION ZONE                 │
│                                               │
│ React / Django                                │
│                                               │
│ Authentication                                │
│ Authorization                                 │
│ Business Logic                                │
└──────────────┬────────────────┬───────────────┘
               │                │
               ▼                ▼
┌─────────────────────┐  ┌─────────────────────┐
│   DATA ZONE         │  │  CONTENT ZONE       │
│                     │  │                     │
│ PostgreSQL          │  │ Object Storage      │
│                     │  │ Protected Files     │
└─────────────────────┘  └─────────────────────┘
```

---

# 36. Server-Side Authorization

The backend is the definitive security boundary.

Every protected operation must validate authorization independently.

For example:

```
GET /content/123
```

must not simply mean:

> "The user is logged in."
> 

It must mean:

```
User authenticated
        AND
User belongs to correct organization
        AND
User has required permission
        AND
User has access to the training context
        AND
Content belongs to the organization
        AND
Requested version is valid
```

Only then should access be granted.

---

# 37. Data Protection

AEGIS should protect data at multiple levels.

## In Transit

```
Browser
   │
 HTTPS
   ▼
Django
```

---

## At Rest

Sensitive business data and protected content should be stored using secure infrastructure and appropriate encryption mechanisms.

```
PostgreSQL
     +
Object Storage
     +
Secure Infrastructure
```

---

## During Access

Protected content should only be delivered after authorization.

```
Stored Content
      │
      ▼
Authorization
      │
      ▼
Controlled Delivery
```

---

# 38. Logging Architecture

Logging provides technical visibility into system behavior.

Logs are different from business audit records.

```
Application Logs
    =
Technical system information

Activity
    =
User/system interaction

Audit
    =
Business/security accountability
```

Conceptually:

```
Django
 │
 ├── Application Logs
 ├── Error Logs
 ├── Security Logs
 └── Operational Logs
          │
          ▼
   Logging Infrastructure
```

---

# 39. Monitoring

The production architecture should eventually monitor:

```
Application health
Database health
Storage health
API performance
Authentication failures
Authorization failures
Error rates
Request volume
Resource utilization
Content-delivery failures
```

Monitoring should support early detection of system and security problems.

---

# 40. Error Handling Architecture

Errors should be handled at the appropriate architectural layer.

```
Database Error
      │
      ▼
Application Error Handling
      │
      ▼
Safe API Response
      │
      ▼
User-Friendly Frontend Message
```

Internal technical details must not unnecessarily leak to the client.

For example, an authorization failure should not reveal internal database information.

---

# 41. Deployment Architecture — MVP

The initial MCA project does not require a highly distributed deployment.

A simple deployment can be:

```
                  Internet
                     │
                     ▼
               ┌───────────┐
               │ Web Entry │
               └─────┬─────┘
                     │
                     ▼
             ┌───────────────┐
             │ Django App    │
             │ + API         │
             └───────┬───────┘
                     │
            ┌────────┴────────┐
            ▼                 ▼
      PostgreSQL        Object Storage
```

React may be deployed separately as a frontend application or served through the chosen deployment infrastructure.

The project proposal identifies free deployment platforms for the initial direction, with Docker/Nginx as future deployment infrastructure.

---

# 42. Deployment Architecture — Production Evolution

As AEGIS grows, the architecture can evolve toward:

```
                         Internet
                            │
                            ▼
                     Load Balancer
                            │
                  ┌─────────┴─────────┐
                  ▼                   ▼
             Django App 1        Django App 2
                  │                   │
                  └─────────┬─────────┘
                            │
                 ┌──────────┼──────────┐
                 ▼          ▼          ▼
            PostgreSQL  Object      Cache
                        Storage
                            │
                            ▼
                    Logging / Monitoring
```

The application layer can therefore scale horizontally without fundamentally changing the domain architecture.

---

# 43. Containerization

Docker may be introduced as the deployment environment as the system matures.

Conceptually:

```
Docker
 │
 ├── Frontend Container
 │
 └── Django Application Container
```

Infrastructure services such as PostgreSQL and object storage may be managed separately depending on the deployment environment.

Docker/Nginx are identified as future deployment infrastructure in the original project proposal.

---

# 44. Scalability Strategy

AEGIS should initially favor **vertical simplicity** and later introduce horizontal scaling where required.

## Initial Stage

```
Single Application
       +
PostgreSQL
       +
Object Storage
```

## Growth Stage

```
Multiple Django Instances
       +
Shared PostgreSQL
       +
Shared Object Storage
       +
Caching
       +
Load Balancing
```

This avoids premature infrastructure complexity.

---

# 45. Horizontal Application Scaling

Django application instances should ideally remain stateless with respect to persistent business data.

```
                 Load Balancer
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
       Django 1    Django 2    Django 3
          │           │           │
          └───────────┼───────────┘
                      ▼
                PostgreSQL
                      │
                      ▼
                Object Storage
```

Persistent information should reside in shared infrastructure rather than only inside one application instance.

---

# 46. Database Scalability

PostgreSQL is the central structured-data store.

As usage grows, the architecture can evolve through:

```
Index optimization
      ↓
Query optimization
      ↓
Connection management
      ↓
Caching
      ↓
Read scaling where required
      ↓
Database infrastructure scaling
```

The application should not prematurely introduce database complexity that the MVP does not require.

---

# 47. Object Storage Scalability

Object storage provides an independent scaling boundary for training content.

```
Application Data
      │
      ▼
PostgreSQL

Large Files
      │
      ▼
Object Storage
```

As the amount of training content increases, file storage can scale independently from relational business data.

---

# 48. Caching — Future Architectural Capability

Caching is not required as a primary MVP dependency.

However, it may later be introduced for data that is safe to cache.

Potential candidates include:

```
Frequently accessed metadata
Permission information
Organization configuration
Read-heavy dashboards
Temporary session-related data
```

Protected source content must not be casually placed into an insecure cache.

---

# 49. Background Processing — Future Capability

Some operations may eventually be better handled asynchronously.

Examples:

```
Large content processing
Watermark generation
Analytics aggregation
Report generation
Notification processing
Security analysis
```

Future architecture:

```
Django
   │
   ▼
Task Queue
   │
   ├── Content Processing
   ├── Analytics
   ├── Reports
   └── Notifications
```

This is an architectural extension rather than an MVP requirement.

---

# 50. Reliability Architecture

AEGIS should separate critical business data from disposable application state.

### Critical

```
PostgreSQL
Object Storage
Audit Records
Content Versions
```

### Reconstructable / Temporary

```
Application cache
Temporary processing state
Client-side UI state
```

This separation simplifies backup and recovery planning.

---

# 51. Backup and Recovery

The production system should eventually provide:

```
Database Backups
        +
Object Storage Protection
        +
Audit Preservation
        +
Recovery Procedures
```

The recovery strategy must ensure that business data and the corresponding protected content remain consistent.

For example:

```
Content Metadata
       +
Content Version
       +
Actual Stored File
```

must not become permanently disconnected.

---

# 52. Security and Audit Consistency

Security-sensitive operations should produce appropriate accountability records.

For example:

```
Access Request
     │
     ▼
Authorization Check
     │
 ┌───┴────┐
 ▼        ▼
Allow    Deny
 │        │
 ▼        ▼
Activity  Security Event
 │        │
 └───┬────┘
     ▼
   Audit
```

This allows AEGIS to support later investigation and analytics.

---

# 53. End-to-End System Flow

The complete AEGIS system can be represented as:

```
                         ┌───────────────┐
                         │     User      │
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │   Browser     │
                         └───────┬───────┘
                                 │ HTTPS
                                 ▼
                         ┌───────────────┐
                         │    React      │
                         └───────┬───────┘
                                 │ API
                                 ▼
                ┌────────────────────────────────┐
                │            Django              │
                │                                │
                │ Authentication                 │
                │ Authorization                  │
                │ Tenant Isolation               │
                │ Business Logic                 │
                │ Content Management              │
                │ Version Management              │
                │ Training Access                 │
                │ Secure Delivery                │
                │ Activity                        │
                │ Audit                           │
                └────────────┬───────────┬───────┘
                             │           │
                             ▼           ▼
                     ┌────────────┐  ┌──────────────┐
                     │ PostgreSQL │  │Object Storage│
                     └────────────┘  └──────────────┘
                             │           │
                             └─────┬─────┘
                                   ▼
                         ┌──────────────────┐
                         │ Logging /        │
                         │ Monitoring       │
                         └──────────────────┘
```

---

# 54. Complete Trainer Content Access Sequence

```
1. Trainer opens AEGIS
          │
          ▼
2. React loads
          │
          ▼
3. Trainer authenticates
          │
          ▼
4. Django validates identity
          │
          ▼
5. Authenticated session established
          │
          ▼
6. Organization context established
          │
          ▼
7. Trainer requests training content
          │
          ▼
8. Django validates authorization
          │
          ▼
9. Training access is checked
          │
          ▼
10. Content assignment is checked
          │
          ▼
11. Current/authorized content version identified
          │
          ▼
12. Access event recorded
          │
          ▼
13. Protected content retrieved
          │
          ▼
14. Dynamic watermark applied
          │
          ▼
15. Content delivered to viewer
          │
          ▼
16. Trainer activity tracked
          │
          ▼
17. Significant events recorded in audit
```

This sequence represents the principal security-sensitive flow of AEGIS.

---

# 55. Complete Administrator Content Lifecycle

```
Administrator
      │
      ▼
Authenticate
      │
      ▼
Organization Context
      │
      ▼
Permission Check
      │
      ▼
Create Content
      │
      ▼
Upload Content Version
      │
      ├───────────────┐
      ▼               ▼
PostgreSQL       Object Storage
      │               │
      └───────┬───────┘
              ▼
       Version Lifecycle
              │
       ┌──────┴───────┐
       ▼              ▼
     Publish        Archive
       │
       ▼
Available for Authorized Delivery
       │
       ▼
Activity / Audit
```

---

# 56. Architecture and Business Rules

The System Architecture must implement the business rules established earlier.

The relationship is:

```
Business Rules
      │
      ▼
Functional Modules
      │
      ▼
Data Architecture
      │
      ▼
System Architecture
      │
      ▼
Technical Implementation
```

Examples:

### Tenant Isolation

Business rule:

```
Organization A cannot access Organization B resources.
```

Architecture response:

```
Authentication
      +
Organization Context
      +
Server-Side Authorization
      +
Tenant-Aware Data Access
```

---

### Protected Content

Business rule:

```
Original content must not be unnecessarily exposed.
```

Architecture response:

```
Private Object Storage
      +
Backend Authorization
      +
Controlled Content Delivery
```

---

### Immutable Versions

Business rule:

```
Published versions remain historically identifiable.
```

Architecture response:

```
Versioned Storage
      +
Version Metadata
      +
Controlled Lifecycle
```

---

### Auditability

Business rule:

```
Important actions must be traceable.
```

Architecture response:

```
Application Events
      +
Activity Tracking
      +
Audit Records
```

---

# 57. Architectural Principles

The Phase 4 architecture follows these principles.

## Principle 1 — Backend is the Security Boundary

Never trust frontend-only authorization.

---

## Principle 2 — Organization is the Tenant Boundary

Every organization-owned operation must respect organization isolation.

---

## Principle 3 — Database Stores Business Data

PostgreSQL stores structured business information.

---

## Principle 4 — Object Storage Stores Large Content

Training files are separated from relational business data.

---

## Principle 5 — Protected Content is Not Normally Distributed as Raw Files

AEGIS provides controlled content delivery.

---

## Principle 6 — Published Content Versions are Immutable

Changes create new versions.

---

## Principle 7 — Activity and Audit are First-Class Capabilities

They are architectural concerns rather than optional afterthoughts.

---

## Principle 8 — Security Must Be Applied Across Layers

Security is not a single feature.

```
Authentication
+
Authorization
+
Tenant Isolation
+
Secure Storage
+
Controlled Delivery
+
Watermarking
+
Audit
```

---

## Principle 9 — Start Simple, Scale Later

The MVP should remain a modular application rather than prematurely becoming a distributed microservice system.

---

# 58. Why AEGIS Does Not Start with Microservices

AEGIS does not initially require separate services for:

```
Authentication Service
Content Service
Training Service
Audit Service
Analytics Service
```

Although these boundaries exist conceptually, separating them into independently deployed services would introduce:

- network complexity
- distributed transactions
- deployment overhead
- monitoring complexity
- authentication complexity
- additional infrastructure

For the MCA MVP, a **modular monolithic Django backend** is more appropriate.

Conceptually:

```
             AEGIS Backend
                  │
      ┌───────────┼────────────┐
      │           │            │
   Content     Training      Audit
      │           │            │
      └───────────┼────────────┘
                  │
              Django App
```

The internal module boundaries allow future extraction into services if scale eventually requires it.

---

# 59. Future Service Evolution

If AEGIS grows significantly, individual capabilities may eventually become independent services.

Potential evolution:

```
                         API Gateway
                              │
          ┌───────────┬───────┼────────┬──────────┐
          ▼           ▼       ▼        ▼          ▼
      Identity     Content  Training  Audit    Analytics
       Service     Service   Service  Service   Service
          │           │        │        │          │
          └───────────┴────────┼────────┴──────────┘
                               ▼
                       Shared Infrastructure
```

This is future architecture, not an MVP requirement.

---

# 60. Technology Stack

The current architectural technology direction is:

| Layer | Technology |
| --- | --- |
| Frontend | React |
| Backend | Python Django |
| Database | PostgreSQL |
| Content Storage | Object Storage |
| Communication | HTTPS / API |
| Authentication | Django Authentication |
| Deployment | Container-ready architecture |
| Reverse Proxy | Nginx where required |
| Monitoring | Application/System Monitoring |

The original project proposal identifies Django as the backend, React/HTML/CSS/JavaScript as frontend options, PostgreSQL among the proposed database choices, Django Authentication and Docker/Nginx as future deployment infrastructure.

For the current AEGIS architecture, the selected direction is:

```
React
   +
Django
   +
PostgreSQL
   +
Object Storage
```

---

# 61. Environment Architecture

AEGIS should conceptually maintain separate environments.

```
Development
     │
     ▼
Testing
     │
     ▼
Staging
     │
     ▼
Production
```

Each environment should have its own:

- configuration
- credentials
- database
- storage configuration
- logging configuration

Production credentials must not be embedded in source code.

---

# 62. Configuration Management

Environment-specific settings should be externally configured.

Conceptually:

```
Application
     │
     ├── Database Configuration
     ├── Storage Configuration
     ├── Authentication Configuration
     ├── Security Configuration
     └── Environment Configuration
```

Sensitive credentials should be managed through secure configuration mechanisms rather than hardcoded.

---

# 63. Architectural Security Controls

The minimum architectural security controls include:

```
HTTPS
Authentication
Server-side Authorization
Tenant Isolation
Private Object Storage
Protected Database
Secure Sessions
Input Validation
Permission Checks
Access Logging
Audit Logging
Security Event Logging
Dynamic Watermarking
Secure Configuration
```

These controls collectively support the project's central objective of protecting proprietary training content.

---

# 64. Architectural Risks

Several risks must be recognized.

## Risk 1 — Browser Capture

No browser-based system can guarantee that a determined user cannot capture displayed content.

Therefore:

```
Watermarking
+
Access Tracking
+
Controlled Delivery
```

should be treated as deterrence and accountability mechanisms rather than absolute prevention.

---

## Risk 2 — Unauthorized Storage Access

If object-storage URLs are exposed permanently, users may bypass application authorization.

Therefore:

```
Private Storage
+
Application-Controlled Access
```

is required.

---

## Risk 3 — Tenant Isolation Failure

An incorrectly scoped database query could expose another organization's data.

Therefore tenant context must be systematically enforced.

---

## Risk 4 — Frontend-Only Authorization

Hiding UI elements is insufficient.

All protected operations must be authorized by Django.

---

## Risk 5 — Audit Data Loss

Audit information may be needed for security investigations.

Therefore audit data should have appropriate retention and protection.

---

# 65. Architecture Decision Records — Phase 4

The ADR register established earlier now continues as part of System Architecture.

The current architectural decisions are:

| ADR | Decision | Status |
| --- | --- | --- |
| ADR-001 | Django as backend framework | Accepted |
| ADR-002 | Organization-centric multi-tenancy | Accepted |
| ADR-003 | Shared database + logical tenant isolation | Accepted |
| ADR-004 | PostgreSQL as primary database | Accepted |
| ADR-005 | Object storage for content files | Accepted |
| ADR-006 | Secure application-based content delivery | Accepted |
| ADR-007 | Immutable content versions | Accepted |
| ADR-008 | Server-side authorization | Accepted |
| ADR-009 | Auditability as first-class capability | Accepted |
| ADR-010 | Dynamic watermarking | Accepted |
| ADR-011 | Modular monolithic backend for MVP | Accepted |
| ADR-012 | React frontend + Django backend separation | Accepted |

The ADR register should continue to grow only when an architectural decision materially constrains the implementation.

---

# 66. Architectural Boundary with Phase 5

Phase 4 establishes **how the system is structured**.

Phase 5 will establish **how components expose functionality to one another**.

```
PHASE 4
System Architecture

React
   │
   │
Django
   │
   ├── PostgreSQL
   └── Object Storage

             ↓

PHASE 5
API Design

React
   │
   ├── POST /...
   ├── GET /...
   ├── PUT /...
   └── DELETE /...
   │
   ▼
Django APIs
```

Detailed API endpoint definitions should therefore be deferred to Phase 5.

---

# 67. Architectural Boundary with Phase 6

Phase 4 also does not define detailed screen designs.

It defines the technical architecture that supports them.

```
Phase 4

React
   ↓
API
   ↓
Django
   ↓
Data / Storage

Phase 6

Login Screen
Dashboard
Content Management
Training Viewer
Activity Dashboard
Audit Dashboard
etc.
```

The exact UI/UX belongs to Phase 6.

---

# 68. Architectural Boundary with Phase 7

Development converts the architecture into working software.

```
Phase 4
System Architecture
       │
       ▼
Phase 5
API Design
       │
       ▼
Phase 6
UI/UX
       │
       ▼
Phase 7
Development
```

Implementation should follow the architectural boundaries rather than allowing the codebase to redefine them accidentally.

---

# 69. Final AEGIS Architecture

The final conceptual architecture is:

```
                              AEGIS
                                │
                                ▼
                        ┌──────────────┐
                        │    Users     │
                        │              │
                        │ Admin        │
                        │ Trainer      │
                        └──────┬───────┘
                               │
                               ▼
                        ┌──────────────┐
                        │   Browser    │
                        └──────┬───────┘
                               │ HTTPS
                               ▼
                        ┌──────────────┐
                        │ React        │
                        │ Frontend     │
                        └──────┬───────┘
                               │ API
                               ▼
                 ┌───────────────────────────────┐
                 │       Django Backend          │
                 │                               │
                 │ Authentication                │
                 │ Authorization                 │
                 │ Tenant Isolation              │
                 │ Organization Management       │
                 │ User / Role Management        │
                 │ Content Management             │
                 │ Version Management             │
                 │ Training Management            │
                 │ Access Management              │
                 │ Secure Content Delivery        │
                 │ Watermarking                   │
                 │ Activity Tracking              │
                 │ Audit                          │
                 └───────────────┬───────────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
              ┌──────────┐ ┌───────────┐ ┌──────────────┐
              │PostgreSQL│ │  Object   │ │   Logging /  │
              │          │ │  Storage  │ │  Monitoring  │
              │ Business │ │ Protected │ │              │
              │ Data     │ │ Content   │ │ Logs / Events│
              └──────────┘ └───────────┘ └──────────────┘
```

---

# 70. Final End-to-End Security Architecture

The most important AEGIS architecture can be summarized as:

```
                         USER
                           │
                           ▼
                        BROWSER
                           │
                         HTTPS
                           │
                           ▼
                    REACT FRONTEND
                           │
                           ▼
                    DJANGO BACKEND
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
       Authentication  Tenant       Authorization
                         Context
              │            │            │
              └────────────┼────────────┘
                           │
                           ▼
                   Business Rules
                           │
                           ▼
                  Training Access
                           │
                           ▼
                     Content Access
                           │
                           ▼
                    Content Version
                           │
                           ▼
                  Secure Delivery
                           │
                    ┌──────┴──────┐
                    ▼             ▼
               Watermark      Access Log
                    │             │
                    └──────┬──────┘
                           ▼
                   Protected Viewer
                           │
                           ▼
                       ACTIVITY
                           │
                           ▼
                         AUDIT
```

---

# 71. Architectural Conclusion

The AEGIS system architecture establishes a **secure, modular, organization-centric web platform** in which:

```
React
   ↓
provides the user interface

Django
   ↓
provides the application and security boundary

PostgreSQL
   ↓
stores structured business data

Object Storage
   ↓
stores protected training files

Activity / Audit
   ↓
provide accountability and visibility
```

The most important architectural principle is:

> **Users interact with AEGIS through the application, while AEGIS controls the authentication, authorization, tenant isolation, content access, content delivery and accountability surrounding every protected training resource.**
> 

The architecture intentionally starts as a **modular monolithic application** suitable for the MCA project while retaining clear boundaries that allow AEGIS to evolve into a scalable SaaS platform.

---

# 72. Phase 4 Completion

With this System Architecture established:

```
PHASE 0 — PRODUCT DESIGN
        ✅

PHASE 1 — DOMAIN DESIGN
        ✅ PRD
        ✅ SRS
        ✅ Domain Model
        ✅ Business Rules
        ✅ ADR Register

PHASE 2 — FUNCTIONAL ARCHITECTURE
        ✅

PHASE 3 — DATABASE DESIGN
        ✅

PHASE 4 — SYSTEM ARCHITECTURE
        ✅ System Architecture
        ✅ Component Architecture
        ✅ Communication Architecture
        ✅ Authentication Architecture
        ✅ Authorization Architecture
        ✅ Tenant Isolation
        ✅ Content Delivery Architecture
        ✅ Storage Architecture
        ✅ Activity / Audit Architecture
        ✅ Security Boundaries
        ✅ Deployment Architecture
        ✅ Scalability Strategy
        ✅ Reliability Considerations
        ✅ Architectural Risks
        ✅ ADR Continuation

                ↓

PHASE 5 — API DESIGN
        NEXT
```

**Phase 4 therefore establishes the technical blueprint of AEGIS without prematurely entering API endpoint design or UI/UX design.**