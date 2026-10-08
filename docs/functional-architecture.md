## AEGIS: Enterprise Knowledge Protection and Delivery Platform

**Project:** MCA Project

**Project Title:** AEGIS – Enterprise Knowledge Protection and Delivery Platform

**Prepared By:** Princy W [2436MCA0001]

**Date:** Septemper 2026

**Technology Direction:** Python Django, Web-based Frontend, PostgreSQL-compatible relational database

**Phase 2:** Functional Architecture

**Purpose:** Transform the approved requirements and domain model into implementation-oriented functional modules.

---

# 1. Purpose

Phase 2 defines **how the AEGIS business/domain capabilities are organized into functional modules**.

Phase 1 established:

```
PRD
  ↓
SRS
  ↓
Domain Model
  ↓
Business Rules
  ↓
Architectural Decisions
```

Phase 2 now transforms those foundations into:

```
Functional Modules
      ↓
Responsibilities
      ↓
Actors
      ↓
Workflows
      ↓
Inputs / Outputs
      ↓
Permissions
      ↓
Business Rules
      ↓
Dependencies
```

The objective is to reach a point where the system is sufficiently decomposed to proceed into **Phase 3 — Data Architecture** without ambiguity about what the system actually needs to do.

---

# 2. What Phase 2 Does Not Define

Phase 2 does **not** yet define:

- Database tables
- Database columns
- Primary/foreign keys
- Django models
- API endpoints
- API request/response schemas
- Deployment architecture
- Infrastructure
- Cloud provider
- Exact object-storage provider
- UI wireframes
- Frontend component architecture

Those belong to later phases.

The distinction is:

```
Phase 1
What must exist?
        ↓
Phase 2
What must the system do?
        ↓
Phase 3
How should the data be structured?
        ↓
Phase 4
How should the whole system technically operate?
        ↓
Phase 5
How should systems/clients communicate?
        ↓
Phase 6
How should users interact with it?
```

---

# 3. Functional Architecture Principles

The AEGIS functional architecture follows these principles.

## FA-P01 — Organization is the Functional Tenant Boundary

All organization-owned functionality operates within an organization context.

```
AEGIS
 │
 ├── Organization A
 │     ├── Users
 │     ├── Content
 │     ├── Programs
 │     ├── Access
 │     └── Activity
 │
 └── Organization B
       ├── Users
       ├── Content
       ├── Programs
       ├── Access
       └── Activity
```

Cross-organization access is prohibited.

This follows the accepted organization-centric multi-tenant decision.

---

## FA-P02 — Authorization is Cross-Cutting

Authorization is not isolated to one screen/module.

Every protected module must evaluate:

```
Authenticated User
        ↓
Organization Context
        ↓
Role / Permission
        ↓
Resource Access
        ↓
Requested Action
```

This follows the established rule that authorization must ultimately be enforced server-side.

---

## FA-P03 — Content Protection is Cross-Cutting

Content protection surrounds the complete content lifecycle:

```
Upload
   ↓
Management
   ↓
Versioning
   ↓
Publication
   ↓
Authorization
   ↓
Secure Delivery
   ↓
Watermarking
   ↓
Activity Tracking
   ↓
Audit
```

Therefore secure delivery is not simply a “viewer feature”; it is connected to several functional modules.

---

## FA-P04 — Activity and Audit are First-Class Capabilities

User activity and security/audit events must be captured as part of relevant workflows rather than added later.

The project direction explicitly includes activity monitoring, access logging and audit logs.

---

## FA-P05 — Modules Communicate Through Business Capabilities

A module should own a clearly defined responsibility.

For example:

```
Content Management
        ↓
creates/manages content

Version Management
        ↓
manages content revisions

Access Management
        ↓
determines who may access content

Secure Delivery
        ↓
delivers authorized content

Activity Tracking
        ↓
records usage

Audit
        ↓
records important accountability events
```

---

# 4. AEGIS Functional Module Map

The complete functional architecture is:

```
                                  AEGIS
                                    │
        ┌───────────────────────────┼────────────────────────────┐
        │                           │                            │
        ▼                           ▼                            ▼
 Authentication & Identity   Organization Management     User & Access Management
        │                           │                            │
        └───────────────────────────┼────────────────────────────┘
                                    │
                                    ▼
                         Knowledge / Content Management
                                    │
                         ┌──────────┴──────────┐
                         ▼                     ▼
                 Content Versioning      Training Programs
                                               │
                                               ▼
                                      Content Assignment
                                               │
                                               ▼
                                      Training Access
                                               │
                                               ▼
                                     Secure Content Delivery
                                               │
                               ┌───────────────┼──────────────┐
                               ▼               ▼              ▼
                           Watermarking     Activity       Security Events
                               │               │              │
                               └───────────────┼──────────────┘
                                               ▼
                                        Audit & Compliance
                                               │
                                               ▼
                                        Analytics & Reporting
```

This is the **functional decomposition** of AEGIS.

---

# 5. Module Catalogue

AEGIS will be divided into the following functional modules.

| ID | Functional Module | Primary Purpose |
| --- | --- | --- |
| FM-01 | Authentication & Identity | Establish and manage authenticated user identity |
| FM-02 | Organization Management | Manage organization/tenant context |
| FM-03 | User & Role Management | Manage users, roles and permissions |
| FM-04 | Knowledge & Content Management | Manage organizational knowledge/content |
| FM-05 | Content Version Management | Manage content revisions and lifecycle |
| FM-06 | Training Program Management | Organize content into training contexts |
| FM-07 | Content Assignment & Access Management | Control who can access what |
| FM-08 | Secure Content Delivery | Deliver protected content through AEGIS |
| FM-09 | Content Protection & Watermarking | Apply protection/accountability mechanisms |
| FM-10 | Activity & Access Tracking | Capture user/content usage |
| FM-11 | Security & Audit Management | Maintain accountability and security records |
| FM-12 | Analytics & Reporting | Convert activity/audit data into insights |
| FM-13 | Administration & Configuration | Manage organization-level operational settings |

Some modules are tightly related and may eventually be implemented as Django applications/subsystems differently. **The functional boundaries are more important at this stage than the eventual code-folder structure.**

---

# 6. FM-01 — Authentication & Identity

## 6.1 Responsibility

Establish the identity of users interacting with AEGIS.

The module is responsible for:

- Login
- Logout
- Authentication
- Session establishment
- Session management
- Session timeout
- Authentication-related security events
- Identity context required by other modules

Session timeout is explicitly part of the established security direction.

---

## 6.2 Actors

Primary:

- Administrator
- Content Manager
- Trainer
- Management

System:

- Authentication subsystem

---

## 6.3 Inputs

Examples:

```
Username / Email
Password
Authentication request
Logout request
Session activity
```

---

## 6.4 Outputs

Examples:

```
Authenticated session
Authentication success
Authentication failure
Logout confirmation
Access-denied response
Session-expiry event
```

---

## 6.5 Main Workflow

```
User
 ↓
Login
 ↓
Validate Credentials
 ↓
Authenticate Identity
 ↓
Resolve Organization
 ↓
Resolve Roles / Permissions
 ↓
Create Session
 ↓
Access AEGIS
```

---

## 6.6 Failure Workflow

```
Login
 ↓
Credential Validation
 ↓
Invalid
 ↓
Authentication Failure
 ↓
Security Event / Audit
```

---

## 6.7 Dependencies

- User & Role Management
- Organization Management
- Security & Audit

---

# 7. FM-02 — Organization Management

## 7.1 Responsibility

Manage the organization/tenant context within AEGIS.

The organization is the primary functional boundary for SaaS operation.

---

## 7.2 Actors

- Administrator

Future:

- Platform Administrator

---

## 7.3 Core Capabilities

- Organization creation
- Organization profile management
- Organization activation/deactivation
- Organization-level configuration
- Organization context resolution

---

## 7.4 Inputs

```
Organization information
Configuration changes
Activation/deactivation request
```

---

## 7.5 Outputs

```
Organization profile
Organization status
Organization configuration
```

---

## 7.6 Business Constraints

- Organization-owned resources must remain within the organization.
- Users must belong to an organization before accessing its protected resources.
- Organization boundaries must be respected across all modules.

These principles derive directly from the accepted tenant model and business rules.

---

## 7.7 Dependencies

- Authentication & Identity
- User & Role Management
- Administration & Configuration

---

# 8. FM-03 — User & Role Management

## 8.1 Responsibility

Manage users and their authorization within an organization.

---

## 8.2 Actors

- Administrator
- Authorized organization administrator

---

## 8.3 Core Capabilities

### User Management

- Create user
- View user
- Update user
- Activate/deactivate user
- Manage user organization membership
- Manage user role assignments

### Role Management

- Create/manage roles where permitted
- Assign roles
- Remove roles
- Associate permissions with roles

---

# 9. Initial Role Model

The functional architecture recognizes the following roles:

```
Administrator
Content Manager
Trainer
Management
```

The project material explicitly identifies these four operational roles.

### Administrator

Broad organizational/system management responsibilities.

### Content Manager

Responsible primarily for knowledge/content operations.

### Trainer

Consumes authorized training content for training delivery.

### Management

Primarily consumes reporting, analytics and governance information.

---

# 10. Permission Model

The functional permission model is capability-oriented.

Examples:

```
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

The final permission catalogue should be frozen during detailed functional/security design rather than prematurely converted into database records.

---

# 11. FM-04 — Knowledge & Content Management

## 11.1 Responsibility

Provide the central repository for organizational knowledge assets.

The system’s original problem is the uncontrolled distribution of proprietary presentations and training resources. AEGIS therefore centralizes those resources under controlled management.

---

## 11.2 Actors

Primary:

- Administrator
- Content Manager

Secondary:

- Authorized users for viewing metadata

---

## 11.3 Core Capabilities

- Create content
- Upload content
- View content metadata
- Update content metadata
- Categorize/organize content
- Search content
- Filter content
- Archive content
- View content status
- View current version

---

## 11.4 Inputs

```
Content metadata
Training resource
Content category
Description
Tags/classification where applicable
```

---

## 11.5 Outputs

```
Content item
Content metadata
Content status
Current version reference
Content listing/search results
```

---

## 11.6 Content Lifecycle

Conceptually:

```
Draft
  ↓
Published
  ↓
Archived
```

The exact lifecycle may be expanded later if approval/review workflows are introduced.

---

## 11.7 Dependencies

- Organization Management
- User & Role Management
- Content Version Management
- Secure Content Delivery
- Audit

---

# 12. FM-05 — Content Version Management

## 12.1 Responsibility

Manage revisions of content without destroying historical versions.

---

## 12.2 Actors

- Administrator
- Content Manager

---

## 12.3 Core Capabilities

- Create new version
- View version history
- Identify current version
- Publish version
- Archive version
- Preserve historical versions
- Track version-related events

---

## 12.4 Main Workflow

```
Existing Content
       ↓
Create New Version
       ↓
Upload Revised Resource
       ↓
Validate
       ↓
Version Created
       ↓
Publish
       ↓
New Current Version
```

---

## 12.5 Historical Version Workflow

```
Content
 ├── V1 ── Historical
 ├── V2 ── Historical
 └── V3 ── Current
```

Historical versions must remain identifiable.

This follows the accepted immutable-version decision.

---

## 12.6 Dependencies

- Content Management
- Secure Delivery
- Audit
- Activity Tracking

---

# 13. FM-06 — Training Program Management

## 13.1 Responsibility

Provide a business context for grouping and delivering related training content.

---

## 13.2 Actors

- Administrator
- Content Manager

Potentially:

- Management

---

## 13.3 Core Capabilities

- Create training program
- Update training program
- Activate/deactivate program
- View program
- Associate content
- Remove content association
- View program contents

---

## 13.4 Example

```
Training Program
"Safety Induction"
       │
       ├── Introduction
       ├── Hazard Identification
       ├── PPE
       └── Emergency Procedures
```

---

## 13.5 Dependencies

- Organization Management
- Content Management
- Content Assignment & Access Management

---

# 14. FM-07 — Content Assignment & Access Management

This module is intentionally separated from Content Management.

The important functional distinction is:

```
Content exists
      ≠
User can access content
```

---

## 14.1 Responsibility

Determine which users/trainers are authorized to access particular training resources.

---

## 14.2 Actors

- Administrator
- Content Manager where authorized
- Trainer as access recipient

---

## 14.3 Core Capabilities

- Grant access
- View access
- Revoke access
- Associate access with training context
- Validate access
- Identify access status

---

## 14.4 Access Decision

Every protected content request conceptually passes through:

```
Request
  ↓
Authenticated?
  ↓ Yes
Organization valid?
  ↓ Yes
Role/Permission valid?
  ↓ Yes
Training/content access exists?
  ↓ Yes
Content/version available?
  ↓ Yes
ALLOW
```

Otherwise:

```
DENY
  ↓
Do not expose protected content
  ↓
Record relevant event
```

This directly follows the established business rules for authorization and protected-content denial.

---

# 15. FM-08 — Secure Content Delivery

## 15.1 Responsibility

Deliver authorized content to users without treating direct source-file distribution as the normal access mechanism.

Secure browser-based viewing is one of the core capabilities identified for AEGIS.

---

## 15.2 Actors

- Trainer
- Authorized User
- Management where viewing permission exists

---

## 15.3 Core Capabilities

- Request content
- Validate authorization
- Resolve current/authorized version
- Establish secure viewing context
- Deliver content to viewer
- Maintain session controls
- Prevent unnecessary source-file exposure
- Record access

---

## 15.4 Main Workflow

```
Trainer
   ↓
Select Training Content
   ↓
Request Access
   ↓
Authenticate
   ↓
Authorize
   ↓
Resolve Authorized Version
   ↓
Create Secure Viewing Context
   ↓
Apply Protection
   ↓
Render in Secure Viewer
   ↓
Track Activity
```

---

## 15.5 Critical Security Boundary

The secure viewer is not merely a UI component.

The functional flow is:

```
User
 ↓
Frontend
 ↓
Backend Authorization
 ↓
Protected Delivery Mechanism
 ↓
Secure Viewer
```

The backend remains the security boundary.

---

## 15.6 Dependencies

- Authentication
- Organization
- User/Roles
- Access Management
- Content
- Version Management
- Watermarking
- Activity Tracking
- Security/Audit

---

# 16. FM-09 — Content Protection & Dynamic Watermarking

## 16.1 Responsibility

Provide protection and accountability mechanisms around secure content delivery.

Dynamic watermarking is explicitly part of the approved project direction.

---

## 16.2 Actors

Primarily:

- System

Indirectly:

- Trainer
- Authorized User

---

## 16.3 Core Capabilities

- Generate viewing-specific watermark information
- Associate watermark with user/access context
- Render watermark with protected content
- Maintain protection configuration

---

## 16.4 Conceptual Flow

```
Authorized User
       ↓
Secure Content Request
       ↓
User / Session Context
       ↓
Generate Watermark Context
       ↓
Secure Viewer
       ↓
Protected Presentation
```

---

## 16.5 Important Boundary

Dynamic watermarking is a **protection and deterrence mechanism**.

It is not currently treated as full DRM.

Advanced DRM-inspired protection remains future scope.

---

# 17. FM-10 — Activity & Access Tracking

## 17.1 Responsibility

Track how users interact with protected AEGIS resources.

---

## 17.2 Actors

System-generated:

- AEGIS

Consumers:

- Administrator
- Management
- Authorized users with activity-view permissions

---

## 17.3 Examples of Trackable Activities

```
Content opened
Content accessed
Content viewed
Version accessed
Access attempt
Training-related interaction
Session-related activity
```

The exact event taxonomy should be finalized before implementation.

---

## 17.4 Main Flow

```
User Action
    ↓
Business Operation
    ↓
Activity Event
    ↓
Activity Recording
    ↓
Analytics / Reporting
```

---

## 17.5 Dependencies

Nearly every operational module may generate activity.

Especially:

- Authentication
- Content
- Version Management
- Access Management
- Secure Delivery

---

# 18. FM-11 — Security & Audit Management

## 18.1 Responsibility

Maintain the accountability trail for important business and security events.

---

## 18.2 Actors

- Administrator
- Management
- Compliance/Audit stakeholders in future
- System

---

## 18.3 Core Capabilities

- Record audit events
- View audit history
- Search/filter audit records
- Investigate security events
- Track administrative changes
- Track important content lifecycle actions
- Track access-control changes

---

## 18.4 Important Audit Events

Examples:

```
Login
Failed Login
Logout
Content Created
Content Updated
Content Archived
Version Created
Version Published
Access Granted
Access Revoked
Content Access
Permission Changed
User Deactivated
Security Event
```

---

## 18.5 Activity vs Audit

The functional architecture preserves the Phase 1 distinction:

```
Activity
"What happened during normal usage?"

Audit
"What important business/security event
must be retained for accountability?"
```

Auditability is explicitly treated as a first-class capability.

---

# 19. FM-12 — Analytics & Reporting

## 19.1 Responsibility

Transform accumulated activity, access and audit information into useful organizational insights.

The original project direction explicitly identifies analytics dashboards, reports and usage insights.

---

## 19.2 Actors

- Administrator
- Management

Potential future:

- Compliance
- Quality Assurance
- Auditors

---

## 19.3 Functional Areas

### Content Analytics

Examples:

- Most accessed content
- Least accessed content
- Content usage frequency
- Version usage

### Trainer Activity Analytics

Examples:

- Trainer access frequency
- Content usage
- Training-resource utilization
- Activity trends

### Security Analytics

Examples:

- Failed access attempts
- Repeated denied requests
- Suspicious activity indicators

### Organizational Analytics

Examples:

- Overall content usage
- Active users
- Content adoption
- Usage trends

---

## 19.4 Reporting

Reports may include:

```
Content Usage Report
Trainer Activity Report
Access Report
Audit Report
Security Activity Report
Version Usage Report
```

---

## 19.5 Dependencies

- Activity Tracking
- Audit
- Content
- User Management
- Access Management

---

# 20. FM-13 — Administration & Configuration

## 20.1 Responsibility

Provide organization-level operational configuration.

---

## 20.2 Actors

- Administrator

---

## 20.3 Potential Capabilities

- Organization settings
- Security settings
- Session configuration
- Watermark configuration
- Content-related settings
- Role/permission configuration
- Other organization-level preferences

---

## 20.4 Important Boundary

Configuration should not become a dumping ground for unrelated business functionality.

Each configurable capability should remain owned by its functional module.

---

# 21. Actor-to-Module Matrix

| Module | Administrator | Content Manager | Trainer | Management |
| --- | --- | --- | --- | --- |
| Authentication | ✓ | ✓ | ✓ | ✓ |
| Organization Management | ✓ | — | — | — |
| User Management | ✓ | Limited* | — | — |
| Role Management | ✓ | — | — | — |
| Content Management | ✓ | ✓ | View | View |
| Version Management | ✓ | ✓ | View | View |
| Training Program | ✓ | ✓ | View | View |
| Access Management | ✓ | Authorized | — | View |
| Secure Delivery | ✓* | ✓* | ✓ | ✓* |
| Watermarking | Configure | — | Consume | — |
| Activity Tracking | View | Authorized | Own activity | View |
| Audit | ✓ | Authorized | — | ✓ |
| Analytics | ✓ | Authorized | Limited | ✓ |
| Reports | ✓ | Authorized | Limited | ✓ |
| Configuration | ✓ | Limited | — | — |
- = permission-dependent, not automatic.

The matrix is functional rather than a final RBAC implementation.

---

# 22. Core End-to-End Workflows

## WF-01 — User Login

```
User
 ↓
Enter Credentials
 ↓
Authentication
 ↓
Validate Identity
 ↓
Resolve Organization
 ↓
Resolve Role/Permissions
 ↓
Create Session
 ↓
Dashboard
```

---

# 23. WF-02 — Create Content

```
Administrator / Content Manager
          ↓
Create Content
          ↓
Enter Metadata
          ↓
Upload Resource
          ↓
Validate
          ↓
Create Content
          ↓
Create Initial Version
          ↓
Audit Event
```

---

# 24. WF-03 — Publish Content

```
Content Manager / Administrator
          ↓
Select Version
          ↓
Validate Version
          ↓
Publish
          ↓
Set as Current Approved Version
          ↓
Audit
```

---

# 25. WF-04 — Create New Content Version

```
Existing Content
      ↓
Create Version
      ↓
Upload Revised Resource
      ↓
Validate
      ↓
New Version
      ↓
Publish when approved
      ↓
Previous Version
remains historical
```

---

# 26. WF-05 — Create Training Program

```
Administrator / Content Manager
          ↓
Create Training Program
          ↓
Define Program Information
          ↓
Associate Content
          ↓
Save
          ↓
Program Available
```

---

# 27. WF-06 — Grant Trainer Access

```
Authorized Administrator
          ↓
Select Trainer
          ↓
Select Training Context
          ↓
Select Content
          ↓
Grant Access
          ↓
Audit Access Grant
```

---

# 28. WF-07 — Trainer Accesses Content

```
Trainer
 ↓
Login
 ↓
Select Authorized Program/Content
 ↓
Request Content
 ↓
Authentication Check
 ↓
Organization Check
 ↓
Permission Check
 ↓
Access Grant Check
 ↓
Content Status Check
 ↓
Version Resolution
 ↓
Secure Viewer
 ↓
Dynamic Watermark
 ↓
Activity Recorded
```

---

# 29. WF-08 — Unauthorized Access

```
User
 ↓
Request Protected Content
 ↓
Authorization
 ↓
DENIED
 ↓
Protected Resource NOT exposed
 ↓
Relevant security/activity event recorded
 ↓
User receives safe denial response
```

This is directly aligned with the Phase 1 rule that denial must not reveal protected content.

---

# 30. WF-09 — Revoke Access

```
Administrator
 ↓
Select Existing Access
 ↓
Revoke
 ↓
Access becomes inactive
 ↓
New access request
       ↓
DENIED
 ↓
Audit Event
```

---

# 31. WF-10 — Content Archive

```
Authorized Manager
       ↓
Select Content
       ↓
Archive
       ↓
Validate Active Access/State
       ↓
Content Archived
       ↓
Audit Event
```

Archived content must not be treated as normally deliverable content.

---

# 32. WF-11 — Activity to Analytics

```
User Activity
      ↓
Activity Event
      ↓
Activity Storage
      ↓
Aggregation
      ↓
Analytics
      ↓
Dashboard / Report
```

---

# 33. WF-12 — Audit Investigation

```
Administrator / Management
          ↓
Open Audit
          ↓
Filter/Search
          ↓
Identify Event
          ↓
Inspect Actor
          ↓
Inspect Resource
          ↓
Inspect Time / Context
          ↓
Investigate
```

---

# 34. Module Dependency Architecture

The major dependencies can be represented as:

```
                  Authentication
                        │
                        ▼
                Organization Context
                        │
                        ▼
                User / Role / Access
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
       Content      Programs       Permissions
          │             │             │
          ▼             ▼             │
      Versions      Assignments       │
          │             │             │
          └──────┬──────┴─────────────┘
                 ▼
           Secure Delivery
                 │
          ┌──────┴──────┐
          ▼             ▼
     Watermarking    Activity
          │             │
          └──────┬──────┘
                 ▼
               Audit
                 │
                 ▼
           Analytics
                 │
                 ▼
              Reports
```

---

# 35. Cross-Cutting Functional Capabilities

Certain capabilities do not belong exclusively to one module.

## Authentication

Applies to every protected operation.

## Authorization

Applies to every protected operation.

## Tenant Isolation

Applies to every organization-owned operation.

## Audit

Applies to significant operations.

## Activity Tracking

Applies to relevant user/system activities.

## Security

Applies particularly to content and access flows.

Therefore:

```
                ┌───────────────────────────┐
                │ Authentication            │
                │ Authorization             │
                │ Tenant Isolation          │
                │ Audit                     │
                │ Activity Tracking         │
                │ Security                  │
                └─────────────┬─────────────┘
                              │
       ┌──────────────────────┼──────────────────────┐
       ▼                      ▼                      ▼
   Content                 Programs               Access
       │                      │                      │
       └──────────────────────┼──────────────────────┘
                              ▼
                       Secure Delivery
```

---

# 36. Functional Ownership

A useful rule for implementation is:

> **Each business capability should have one primary functional owner.**
> 

| Capability | Owning Module |
| --- | --- |
| Identity | Authentication |
| Organization | Organization Management |
| Users | User Management |
| Roles/Permissions | User & Role Management |
| Knowledge Resources | Content Management |
| Revisions | Version Management |
| Training Context | Training Program |
| User Authorization to Content | Access Management |
| Protected Presentation | Secure Delivery |
| Watermark | Content Protection |
| User Usage | Activity Tracking |
| Accountability | Audit |
| Insights | Analytics |
| Reports | Reporting |
| Configuration | Administration |

This prevents duplicated responsibilities.

---

# 37. Functional Security Model

The secure-content path is the most important functional path in AEGIS.

```
                    CONTENT REQUEST
                          │
                          ▼
                   Authentication
                          │
                    authenticated?
                     /          \
                   No            Yes
                   │              │
                 DENY             ▼
                         Organization Validation
                                  │
                           valid organization?
                            /             \
                          No               Yes
                          │                 │
                        DENY                ▼
                              Permission Validation
                                       │
                                authorized?
                                /        \
                              No          Yes
                              │            │
                            DENY           ▼
                                  Access Validation
                                       │
                                  access exists?
                                   /          \
                                 No            Yes
                                 │              │
                               DENY             ▼
                                      Content/Version Check
                                               │
                                               ▼
                                       Secure Delivery
                                               │
                                               ▼
                                         Watermarking
                                               │
                                               ▼
                                           Activity
                                               │
                                               ▼
                                             Audit
```

This is the central functional security workflow of AEGIS.

---

# 38. Content Lifecycle Architecture

The complete functional lifecycle is:

```
             CONTENT CREATION
                    │
                    ▼
                  Draft
                    │
                    ▼
             Version Creation
                    │
                    ▼
                Validation
                    │
                    ▼
                Publication
                    │
                    ▼
             Approved Version
                    │
                    ▼
             Controlled Access
                    │
                    ▼
             Secure Delivery
                    │
                    ▼
                 Usage
                    │
                    ▼
          Activity + Audit
                    │
                    ▼
            New Version Created
                    │
                    ▼
             Previous Version
                Historical
```

---

# 39. Functional Boundary: Content vs Delivery

This distinction is particularly important.

### Content Management answers:

> What knowledge does the organization own?
> 

### Version Management answers:

> Which revision exists and which is approved?
> 

### Access Management answers:

> Who is allowed to access it?
> 

### Secure Delivery answers:

> How is authorized content delivered safely?
> 

### Activity Tracking answers:

> How was it used?
> 

### Audit answers:

> What important event occurred?
> 

### Analytics answers:

> What can the organization learn from the collected information?
> 

This separation is one of the most important architectural outcomes of Phase 2.

---

# 40. Functional Boundary: Activity vs Audit vs Analytics

```
USER ACTION
    │
    ├──────────────► Activity
    │
    └──────────────► Audit
                         │
                         ▼
                    Analytics
                         │
                         ▼
                      Reports
```

They are not interchangeable.

### Activity

Raw operational usage.

### Audit

Accountability/security history.

### Analytics

Processed information derived from operational data.

### Reports

Human-readable presentation of information.

---

# 41. MVP Functional Scope

The MVP should include:

```
✓ Authentication
✓ Organization/Tenant Management
✓ User Management
✓ Role & Permission Management
✓ Content Repository
✓ Content Upload/Management
✓ Content Versioning
✓ Training Programs
✓ Content Assignment
✓ Controlled Trainer Access
✓ Secure Browser-Based Delivery
✓ Dynamic Watermarking
✓ Activity Tracking
✓ Access Logging
✓ Audit Logs
✓ Basic Analytics
✓ Basic Reports
✓ Administrative Configuration
```

This is consistent with the established project scope, which includes user/role management, content repository, browser-based presentation viewing, version control, dynamic watermarking, access logging, activity monitoring, analytics, reports and audit logs.

---

# 42. Explicitly Outside MVP

The following should remain outside the MVP functional architecture:

```
AI Trainer Performance Analysis
AI Content Recommendations
AI-Generated Training Insights
Advanced DRM
Offline Encrypted Viewer
Mobile Application
QR-Based Authentication
Live Training Analytics
LDAP / Active Directory / SSO
LMS Integration
Cloud Storage Integrations
Digital Content Fingerprinting
AI Anomaly Detection
Automated Lifecycle Policies
Workflow Automation Engine
Plugin Marketplace
```

These have appeared as future directions in the project material and should not become accidental MVP dependencies.

---

# 43. Future Extensibility Model

The architecture should allow future capabilities to consume existing AEGIS events rather than redesigning the core.

For example:

```
                    AEGIS Activity
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
          Analytics      AI       Anomaly Detection
              │           │           │
              ▼           ▼           ▼
           Reports    Insights     Security Alerts
```

Similarly:

```
Secure Delivery
       │
       ├── Current Browser Viewer
       │
       ├── Future Mobile Viewer
       │
       ├── Future Offline Viewer
       │
       └── Future Advanced DRM
```

This allows future capabilities to extend the platform without becoming MVP dependencies.

---

# 44. Functional Architecture Summary

The complete AEGIS functional architecture is:

```
                              AEGIS
                                │
             ┌──────────────────┴──────────────────┐
             │                                     │
             ▼                                     ▼
    Authentication & Identity             Organization Management
             │                                     │
             └──────────────────┬──────────────────┘
                                ▼
                     User & Role Management
                                │
                         Permissions / RBAC
                                │
             ┌──────────────────┴──────────────────┐
             │                                     │
             ▼                                     ▼
     Content Management                    Training Programs
             │                                     │
             ▼                                     ▼
      Version Management                 Content Assignment
             │                                     │
             └──────────────────┬──────────────────┘
                                ▼
                       Access Management
                                │
                                ▼
                     Secure Content Delivery
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
              Watermarking              Activity
                    │                       │
                    └───────────┬───────────┘
                                ▼
                          Security / Audit
                                │
                                ▼
                         Analytics Engine
                                │
                                ▼
                            Reporting
```

---

# 45. Phase 2 Completion Criteria

Phase 2 will be considered complete when we can answer all of these questions:

### Module Definition

- What modules exist?
- What does each module own?
- What does each module explicitly not own?

### Actors

- Who interacts with each module?
- Which roles can perform which actions?

### Workflows

- How does each major business operation flow?
- What happens on success?
- What happens on failure?

### Inputs / Outputs

- What does each module receive?
- What does it produce?

### Authorization

- Who is allowed to perform each operation?
- What organization boundary applies?

### Dependencies

- Which module depends on which other module?

### Business Rules

- Which Phase 1 rules apply to each module?

### Security

- Where are authentication and authorization enforced?
- Where is protected content exposed?
- What gets audited?

### MVP Boundary

- What belongs in MVP?
- What is explicitly future scope?

Once these are answered, the system becomes sufficiently decomposed for **Data Architecture**.

---

# 46. Traceability from Phase 1 to Phase 2

The Phase 2 architecture is directly derived from the previous phase:

| Phase 1 Concept | Phase 2 Functional Owner |
| --- | --- |
| Organization | Organization Management |
| User | User Management |
| Role | Role Management |
| Permission | Authorization / User & Role Management |
| Content | Content Management |
| Content Version | Version Management |
| Training Program | Training Program Management |
| Content Assignment | Assignment & Access Management |
| Training Access | Access Management |
| Content Access | Secure Delivery + Activity |
| Activity Record | Activity Tracking |
| Security Event | Security & Audit |
| Audit Record | Audit Management |
| Watermark | Content Protection |
| Authentication Session | Authentication & Identity |

This gives us a clean transformation from the Domain Model into Functional Architecture.

---

# 47. Final Architectural Principle

The core functional chain of AEGIS is:

```
ORGANIZATION
     ↓
IDENTITY
     ↓
ROLE / PERMISSION
     ↓
KNOWLEDGE CONTENT
     ↓
VERSION
     ↓
TRAINING CONTEXT
     ↓
ACCESS CONTROL
     ↓
SECURE DELIVERY
     ↓
PROTECTION
     ↓
ACTIVITY
     ↓
AUDIT
     ↓
ANALYTICS
     ↓
REPORTING
```

This chain represents the **functional backbone of AEGIS**.

The product is therefore not simply:

> “A website where trainers view presentations.”
> 

It is functionally:

> **A multi-tenant enterprise knowledge platform that manages organizational knowledge, controls access to approved versions, securely delivers protected content, records how it is used, maintains accountability, and converts usage information into organizational insight.**
> 

---

# 48. Phase 2 → Phase 3 Boundary

With Phase 2 completed, the next question becomes:

> **“What data must exist to support all these functional capabilities?”**
> 

That is Phase 3.

```
PHASE 1
Requirements & Domain Design
        │
        ▼
PHASE 2
Functional Architecture
        │
        ├── Modules
        ├── Responsibilities
        ├── Actors
        ├── Workflows
        ├── Permissions
        ├── Inputs / Outputs
        ├── Dependencies
        └── Functional Boundaries
        │
        ▼
PHASE 3
Data Architecture
        │
        ├── ER Model
        ├── Entities
        ├── Attributes
        ├── Relationships
        ├── Constraints
        ├── Tenant Isolation
        ├── Indexing
        └── Database Design
```

Therefore, **we should not start designing database tables yet inside Phase 2**.

The functional architecture is now the bridge between the **business/domain model** and the **data/system architecture**.

---

# 49. Phase 2 Baseline

The Phase 2 baseline is therefore:

```
AEGIS
│
├── 01 Authentication & Identity
├── 02 Organization Management
├── 03 User & Role Management
├── 04 Knowledge & Content Management
├── 05 Content Version Management
├── 06 Training Program Management
├── 07 Content Assignment & Access Management
├── 08 Secure Content Delivery
├── 09 Content Protection & Watermarking
├── 10 Activity & Access Tracking
├── 11 Security & Audit Management
├── 12 Analytics & Reporting
└── 13 Administration & Configuration
```

### Status

**Phase 2 — Functional Architecture: BASELINE ESTABLISHED**

This becomes the functional foundation for the next architectural phase.

---

# 50. Important Design Decision Going Forward

One thing I would **not** do from this point onward is blindly convert every module above into a Django app.

For example:

```
Functional Module
       ≠
Django App
       ≠
Database Table
       ≠
API
       ≠
UI Screen
```

Those are different architectural views.

The same functional module may eventually be implemented using several Django models, services, repositories, APIs and UI components.

That separation will help us keep AEGIS scalable instead of designing the system around the framework too early.