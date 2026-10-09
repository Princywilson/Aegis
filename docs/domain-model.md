## AEGIS: Enterprise Knowledge Protection and Delivery Platform

**Project:** MCA Project

**Project Title:** AEGIS – Enterprise Knowledge Protection and Delivery Platform

**Prepared By:** Princy W [2436MCA0001]

**Date:** August 2026

**Technology Direction:** Python Django, Web-based Frontend, PostgreSQL-compatible relational database

---

## 1. Purpose

The Domain Model defines the major business entities that exist within AEGIS and the relationships between them.

It describes the system from a **business/domain perspective**, not from a database perspective.

---

# 2. AEGIS Domain Overview

At the highest level, AEGIS is organized around the following domain:

```
Organization
    │
    ├── Users
    │     ├── Roles
    │     └── Permissions
    │
    ├── Content
    │     └── Content Versions
    │
    ├── Training Programs
    │     └── Content Assignments
    │
    ├── Training / Delivery Context
    │     └── Trainer Access
    │
    ├── Activity
    │     ├── Content Access
    │     ├── Trainer Activity
    │     └── Security Events
    │
    └── Audit
          └── Audit Records
```

The central relationship is:

```
Organization
      │
      ├──────── Users ──────── Roles
      │
      ├──────── Content ─────── Content Versions
      │
      └──────── Training Programs
                    │
                    └──── Content
                              │
                              └──── Controlled User Access
                                           │
                                           └──── Activity / Audit
```

---

# 3. Core Domain Entities

## 3.1 Organization

### Purpose

Represents an organization using AEGIS to manage and protect its proprietary training content.

The organization is the **top-level business boundary** of AEGIS.

### Responsibilities

An Organization:

- Owns training content
- Owns training programs
- Manages its users
- Defines access and authorization within its organization
- Controls how its proprietary content is delivered
- Has its own activity and audit history

### Relationship

```
Organization
    ├── has many Users
    ├── has many Roles
    ├── owns many Content items
    ├── owns many Training Programs
    ├── has many Activity Records
    └── has many Audit Records
```

### Domain significance

The Organization establishes the foundation for **multi-tenancy**.

Conceptually:

```
AEGIS
 │
 ├── Organization A
 │     ├── Users
 │     ├── Content
 │     └── Training Programs
 │
 ├── Organization B
 │     ├── Users
 │     ├── Content
 │     └── Training Programs
 │
 └── Organization C
       ├── Users
       ├── Content
       └── Training Programs
```

Organizations should therefore be treated as isolated business domains even if the eventual MVP uses a shared database infrastructure.

---

# 4. User

## Purpose

Represents a person who interacts with AEGIS.

Users belong to an Organization and perform actions according to their assigned roles and permissions.

### Typical users

The domain currently identifies two primary operational categories:

- Administrator
- Content Consumer

The model should remain flexible enough to support additional roles later.

### Responsibilities

A User can:

- Authenticate into AEGIS
- Access authorized resources
- Manage or consume content according to permissions
- Participate in training delivery
- Generate activity records through system interactions

### Relationship

```
Organization
      │
      └── Users
             │
             └── Roles
```

A user belongs to an organization and receives one or more roles according to the authorization model.

---

# 5. Role

## Purpose

Represents a collection of responsibilities and access privileges assigned to users.

Roles provide the foundation for **role-based access control (RBAC)**.

### Initial conceptual roles

```
Administrator
Content Consumer
```

The actual role structure can be expanded later without changing the fundamental domain.

### Administrator

Responsible for organization-level management, including areas such as:

- Managing content
- Managing content versions
- Managing users
- Managing training programs
- Controlling access
- Reviewing activity
- Reviewing audit information

### Content Consumer

A user authorized to access and consume organizational content according to assigned permissions and access grants.

This is a role assigned to a `User`, not a separate user type or entity. Renaming it does not change its existing permissions.

### Relationship

```
User
  │
  └── assigned Role(s)
             │
             └── determines Permissions
```

---

# 6. Permission

## Purpose

Represents a specific authorization that determines what an actor is allowed to do within AEGIS.

Examples include:

- Manage users
- Upload content
- Manage content
- Publish content
- View content
- Access training programs
- View activity
- View audit information

Permissions are conceptually separated from Roles so that authorization can evolve without redesigning the core domain.

```
Role
  │
  └── grants Permissions
```

The exact permission matrix belongs to the functional/security design phase.

---

# 7. Content

## Purpose

Represents a training resource owned and managed by an organization.

This is one of the **central domain entities of AEGIS**.

The primary purpose of AEGIS is not simply to store files; it is to enable organizations to **securely manage and deliver proprietary training content without unnecessarily exposing the original source material**.

This directly reflects the project's identified problem of presentation files being vulnerable to copying, sharing and misuse.

### Examples

Content may conceptually represent:

- Training presentations
- Training learning materials
- Supporting training resources

### Responsibilities

Content represents:

- Ownership
- Content identity
- Content lifecycle
- Current version
- Access eligibility
- Relationship with training programs

### Relationship

```
Organization
      │
      └── owns Content
                 │
                 └── has Content Versions
```

---

# 8. Content Version

## Purpose

Represents a specific version of a Content item.

Content itself represents the logical training resource, while Content Version represents a particular state of that resource.

This distinction is important because training material may evolve over time.

### Example

```
Content
"Working at Height Training"
       │
       ├── Version 1
       ├── Version 2
       └── Version 3
```

A newer version does not create an entirely new logical training resource.

Instead:

```
Content
   │
   ├── Version 1
   ├── Version 2
   └── Version 3 ← Current Version
```

### Responsibilities

A Content Version represents:

- A specific revision of content
- The version used for delivery
- Historical content state
- Version lifecycle
- The relationship between a training resource and its historical revisions

### Importance

Versioning supports:

- Content consistency
- Historical tracking
- Controlled updates
- Auditability
- Future rollback/reference capabilities

Content version history is explicitly part of the project's objective and proposed functionality.

---

# 9. Training Program

## Purpose

Represents a structured training offering managed within an organization.

A Training Program provides the business context in which training content is used.

For example:

```
Training Program
"Safety Induction"
        │
        ├── Content A
        ├── Content B
        └── Content C
```

### Responsibilities

A Training Program:

- Groups related training content
- Provides context for training delivery
- Determines which content is relevant to a particular training activity
- Provides a higher-level business object around individual content items

### Relationship

```
Organization
      │
      └── owns Training Programs
                 │
                 └── uses Content
```

---

# 10. Content Assignment

## Purpose

Represents the business relationship that determines which content is associated with a particular Training Program or authorized training context.

This is important because:

> A Content item existing inside an organization does not automatically mean that every Content Consumer can access it.
> 

Conceptually:

```
Training Program
       │
       └── Content Assignment
                 │
                 └── Content
```

The assignment relationship provides a controlled way of determining which content belongs to or is used within a particular training context.

---

# 11. Training Access

## Purpose

Represents the controlled authorization for a user to access training content within a particular context.

This is a key AEGIS concept.

The system is not merely:

```
User → Content
```

Instead, access exists within a controlled organizational/training context.

Conceptually:

```
User
 │
 └── authorized access
          │
          └── Training Program
                    │
                    └── Content
```

This allows AEGIS to answer questions such as:

- Who is allowed to access this content?
- What training context is the content being accessed for?
- What content was available to the Content Consumer?
- When did the Content Consumer access it?
- What activity occurred during access?

This controlled-access model is central to the project's objective of protecting proprietary training resources.

---

# 12. Content Access

## Purpose

Represents an instance of a user accessing protected training content.

It is distinct from authorization.

### Authorization

```
"Content Consumer A is allowed to access Content X."
```

### Access

```
"Content Consumer A accessed Content X at this point in time."
```

This distinction is essential for security and auditing.

### Relationship

```
User
 │
 └── Content Access
          │
          └── Content / Content Version
```

Content Access contributes to the activity history of AEGIS.

---

# 13. Activity Record

## Purpose

Represents an observable action performed by a user or generated by the system.

Activity tracking is a core part of AEGIS because the platform needs visibility into how protected training content is being used.

### Examples

Conceptually, activity may include:

- Content accessed
- Content viewed
- Training material opened
- Training-related interaction
- Access attempts
- Other tracked Content Consumer activities

### Relationship

```
User
 │
 └── Activity Records
          │
          ├── Content-related activity
          ├── Training-related activity
          └── Security-related activity
```

The project proposal specifically identifies access logging and Content Consumer activity tracking as part of the proposed solution.

---

# 14. Audit Record

## Purpose

Represents a security/accountability record of important actions performed within AEGIS.

Activity and audit are related but conceptually different.

### Activity

Answers:

> **“What did the user do?”**
> 

### Audit

Answers:

> **“What important system/business/security event occurred, who caused it, and when?”**
> 

For example:

```
Activity:
Content Consumer viewed training content.

Audit:
Content access occurred for a protected resource.
```

Audit records therefore provide an accountability trail for significant system operations.

### Relationship

```
Organization
      │
      └── Audit Records
                │
                ├── Actor
                ├── Action
                ├── Resource
                └── Time
```

Audit reporting is explicitly identified in the project proposal.

---

# 15. Security Event

## Purpose

Represents an event relevant to the security and protection of organizational content.

This is conceptually related to Activity and Audit but focuses specifically on security-sensitive occurrences.

Examples may include:

- Unauthorized access attempt
- Access denial
- Suspicious access behavior
- Authentication/security events

The detailed security-event taxonomy can be refined during the System Design and Security Design phases.

---

# 16. Watermark

## Purpose

Represents the conceptual security mechanism used to associate protected content with its authorized viewing context.

AEGIS is intended to use **dynamic watermarking** as part of its content-protection strategy.

Conceptually:

```
Content Version
      │
      └── Secure Presentation
                │
                └── Dynamic Watermark
```

The Watermark is a **domain concept**, not necessarily a permanent business object.

Whether watermark information ultimately requires persistent storage is a later DB/System Design decision.

---

# 17. Authentication Session

## Purpose

Represents a user's authenticated interaction with AEGIS.

It establishes the security context under which activities and access events occur.

Conceptually:

```
User
 │
 └── Authentication Session
          │
          └── Activity / Access
```

The session concept is useful because activity and access should be attributable to an authenticated actor.

The exact authentication implementation remains part of the technical design.

---

# 18. Domain Relationship Model

The major domain relationships can now be represented as:

```
                           ┌──────────────┐
                           │ Organization │
                           └──────┬───────┘
                                  │
                 ┌────────────────┼─────────────────┐
                 │                │                 │
                 ▼                ▼                 ▼
              Users             Content       Training Programs
                 │                │                 │
                 │                ▼                 │
                 │        Content Versions          │
                 │                │                 │
                 │                └────────┐        │
                 │                         │        │
                 ▼                         ▼        ▼
               Roles                Content Access
                 │                         │
                 ▼                         │
             Permissions                   │
                                           ▼
                                    Activity Records
                                           │
                                           ▼
                                     Audit Records
```

---

# 19. End-to-End Domain Flow

The complete business relationship can be viewed as:

```
Organization
      │
      ├── creates/manages Users
      │
      ├── assigns Roles
      │       │
      │       └── grants Permissions
      │
      ├── creates Content
      │       │
      │       └── creates Content Versions
      │
      └── creates Training Programs
              │
              └── associates Content
                        │
                        ▼
                 Controlled Access
                        │
                        ▼
                      User
                        │
                        ▼
                Training Delivery
                        │
                        ├── Activity
                        │
                        ├── Access Records
                        │
                        └── Security Events
                                │
                                ▼
                           Audit Records
```

This represents the core business lifecycle of AEGIS.

---

# 20. Core vs Supporting Domain Entities

To prevent the domain model from becoming unnecessarily complicated, the entities can be grouped conceptually.

## Core Domain

These are central to the actual value proposition of AEGIS:

```
Organization
User
Role
Content
Content Version
Training Program
Content Assignment
Training Access
Activity Record
Audit Record
```

## Supporting Domain

These support the core domain:

```
Permission
Content Access
Security Event
Authentication Session
Watermark
```

Some supporting concepts may eventually become implementation-level concepts rather than standalone persisted business entities.

---

# 21. MVP Domain Boundary

For the MCA MVP, the domain should remain focused.

### MVP should primarily establish:

```
Organization
      │
      ├── Users
      │     └── Roles / Permissions
      │
      ├── Content
      │     └── Content Versions
      │
      ├── Training Programs
      │     └── Content Assignments
      │
      └── Activity / Audit
```

The security layer then surrounds the content-delivery process:

```
                 ┌─────────────────────────┐
                 │      Security Layer      │
                 │                         │
                 │ Authentication          │
                 │ Authorization           │
                 │ Controlled Access       │
                 │ Watermarking             │
                 │ Activity Tracking       │
                 │ Audit                   │
                 └───────────┬─────────────┘
                             │
                             ▼
                    Protected Content
                             │
                             ▼
                 Content Consumer/User
```

This keeps the MCA implementation achievable while preserving the architecture required for future expansion.

---

# 22. Explicitly Outside the Current Core Domain

The following concepts should **not** be introduced as core MVP domain entities yet.

They remain future possibilities identified in the project direction:

### AI Content Consumer Performance Analysis

```
Future:
Content Consumer Activity
      │
      ▼
AI Analysis
      │
      ▼
Performance Insights
```

### DRM-inspired Protection

A future security layer may provide stronger digital rights management capabilities.

### Live Training Analytics

Future real-time analytics can build on the Activity domain.

### Mobile Application

This is a future client/channel rather than a new core business entity.

### Offline Encrypted Viewer

This is a future content-delivery/security capability.

### External Integrations

Future integrations may connect AEGIS with other applications.

These future enhancements are consistent with the project proposal, which identifies AI-based Content Consumer analytics, DRM-inspired protection, live training analytics, mobile support, offline encrypted viewing and application integrations as future scope.

---

# 23. Important Domain Distinctions

Several concepts must remain separate even if they later appear closely related in implementation.

### Content ≠ Content Version

```
Content
= logical training resource

Content Version
= specific revision of that resource
```

### Permission ≠ Access

```
Permission
= what a user is allowed to do

Access
= an actual occurrence of accessing a resource
```

### Activity ≠ Audit

```
Activity
= user/system activity

Audit
= accountability/security record
```

### User ≠ Content Consumer

```
User
= authenticated person

Content Consumer
= a business role/capability performed by a user
```

This means `Content Consumer` is a role assigned to a `User`, not a separate fundamental identity or entity.

### Training Program ≠ Content

```
Training Program
= business/training context

Content
= training resource
```

A program uses content; it does not become the content itself.

---

# 24. Final Conceptual Domain Model

The resulting AEGIS domain can be summarized as:

```
                              AEGIS
                                │
                        ┌───────▼────────┐
                        │   Organization │
                        └───────┬────────┘
                                │
              ┌─────────────────┼──────────────────┐
              │                 │                  │
              ▼                 ▼                  ▼
           Users             Content          Training Programs
              │                 │                  │
              ▼                 ▼                  │
        Roles / Access    Content Versions         │
              │                 │                  │
              │                 └────────┬─────────┘
              │                          │
              └──────────────┐           ▼
                             │      Content Assignment
                             │           │
                             ▼           ▼
                          Authorized Training Access
                                      │
                                      ▼
                                     User
                                      │
                                      ▼
                               Training Delivery
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
               Content Access      Activity        Security Events
                    │                 │                 │
                    └─────────────────┼─────────────────┘
                                      ▼
                                Audit Records
```

---

# 25. Domain Model Decision

The AEGIS domain is therefore centered around one fundamental business relationship:

> **An organization owns protected training content and training programs, authorized users access that content according to their roles and permissions, and AEGIS records the resulting activity and audit trail.**
> 

The most important domain chain is:

```
Organization
      ↓
User / Role
      ↓
Training Program
      ↓
Content
      ↓
Content Version
      ↓
Controlled Access
      ↓
Training Activity
      ↓
Audit
```

This is the **baseline domain model for AEGIS**.

It gives us the correct conceptual foundation for the next phases without prematurely turning the domain into database tables or Django models.

# 26. Boundary Between Domain Model and Next Phase

The following progression should now be maintained:

```
PHASE 0 — PRODUCT DESIGN
        │
        └── PRD
             ↓
PHASE 1 — DOMAIN DESIGN
        │
        └── Domain Model  ← CURRENT
             ↓
PHASE 2 — FUNCTIONAL MODULES
        │
        └── Define system modules/features
             ↓
PHASE 3 — DB DESIGN
        │
        └── Convert domain concepts into
            entities/tables/relationships
             ↓
PHASE 4 — SYSTEM DESIGN
        │
        └── Architecture + components + flows
             ↓
PHASE 5 — API DESIGN
             ↓
PHASE 6 — UI/UX
             ↓
PHASE 7 — DEVELOPMENT
```

Therefore, **we should not design the database yet**.

The Domain Model is now answering the exact question:

> **“What things exist in AEGIS, and how do they relate?”**
> 

while leaving:

> **“How do we technically implement them?”**
> 

for the phases that follow.