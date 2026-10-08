## AEGIS: Enterprise Knowledge Protection and Delivery Platform

**Project:** MCA Project

**Project Title:** AEGIS – Enterprise Knowledge Protection and Delivery Platform

**Prepared By:** Princy W [2436MCA0001]

**Date:** Septemper 2026

**Technology Direction:** Python Django, Web-based Frontend, PostgreSQL-compatible relational database

**Phase 1:** ADRs

**Purpose:** Define enforceable business/domain rules derived from the PRD, SRS and Domain Model.

- ADRs
    
    Architecture Decision Records - Any ARD should be added to these instead of New ARDs
    
    # ADR-001 — Django as Backend Framework
    
    **Status:** Accepted
    
    ### Context
    
    AEGIS requires a secure web-based backend supporting authentication, authorization, content management, access control, auditing and future API integration.
    
    ### Decision
    
    Use **Python Django** as the primary backend framework.
    
    The project proposal explicitly identifies Python Django as the backend technology.
    
    ### Rationale
    
    Django provides a strong foundation for:
    
    - authentication
    - authorization
    - ORM/data access
    - security controls
    - administrative functionality
    - web application development
    - future API integration
    
    ### Consequences
    
    **Positive**
    
    - Mature framework
    - Strong security foundation
    - Python ecosystem
    - Good fit for the project
    - Supports future API architecture
    
    **Trade-off**
    
    - Architecture becomes Django-centric.
    
    ---
    
    # ADR-002 — Organization-Centric Multi-Tenant Architecture
    
    **Status:** Accepted
    
    ### Context
    
    AEGIS is intended to evolve into a SaaS product serving multiple organizations.
    
    Organizations must be isolated from each other while sharing the same application platform.
    
    ### Decision
    
    Use an **organization-centric multi-tenant architecture**.
    
    ```
    AEGIS
     │
     ├── Organization A
     │     ├── Users
     │     ├── Content
     │     ├── Programs
     │     └── Activity
     │
     ├── Organization B
     │     ├── Users
     │     ├── Content
     │     ├── Programs
     │     └── Activity
     │
     └── Organization C
    ```
    
    The **Organization is the tenant boundary**.
    
    ### Rationale
    
    This provides a scalable foundation without prematurely creating a separate database for every organization.
    
    ### Consequences
    
    All organization-owned entities must carry or derive an organization context.
    
    Tenant isolation becomes a fundamental architectural concern.
    
    ---
    
    # ADR-003 — Shared Database with Logical Tenant Isolation
    
    **Status:** Accepted
    
    ### Context
    
    The initial MVP should remain operationally simple while supporting SaaS scalability.
    
    A database-per-tenant architecture would introduce unnecessary operational complexity at the MVP stage.
    
    ### Decision
    
    Use a **shared database architecture with logical organization-level isolation** for the initial system.
    
    Conceptually:
    
    ```
    Shared PostgreSQL Database
    │
    ├── Organization
    ├── User
    ├── Content
    ├── ContentVersion
    ├── TrainingProgram
    ├── Access
    ├── Activity
    └── Audit
    ```
    
    Each organization-owned record is associated with its organization.
    
    ### Rationale
    
    - simpler MVP deployment
    - lower operational overhead
    - easier development
    - suitable for initial scale
    - allows future migration/evolution if tenant isolation requirements change
    
    ### Consequence
    
    Tenant isolation must be enforced consistently at the application/data-access level.
    
    ---
    
    # ADR-004 — PostgreSQL as Primary Database
    
    **Status:** Proposed / To Be Confirmed in Phase 3
    
    ### Context
    
    The project proposal currently lists:
    
    > PostgreSQL / MySQL / Supabase
    > 
    
    as database possibilities.
    
    However, our architecture direction requires a clear primary relational database.
    
    ### Decision
    
    **PostgreSQL is the preferred primary database for AEGIS.**
    
    I am intentionally marking this **Proposed**, rather than pretending we had already formally frozen it.
    
    ### Rationale
    
    PostgreSQL is well suited to:
    
    - relational domain modeling
    - transactional integrity
    - complex relationships
    - indexing
    - audit data
    - JSON where needed
    - future SaaS scale
    
    ### Consequence
    
    The final database architecture, schema, indexes and tenant-isolation mechanisms will be formally designed in **Phase 3 — Data Architecture**.
    
    ---
    
    # ADR-005 — Object Storage for Training Content
    
    **Status:** Proposed
    
    ### Context
    
    AEGIS handles proprietary training files.
    
    These files should not be treated as ordinary relational database records.
    
    ### Decision
    
    Store content files in **object storage**, while keeping metadata and business relationships in the relational database.
    
    ```
    PostgreSQL
        │
        ├── Content metadata
        ├── Version metadata
        ├── ownership
        ├── lifecycle
        └── access information
    
    Object Storage
        │
        ├── Version 1 file
        ├── Version 2 file
        └── Version 3 file
    ```
    
    ### Rationale
    
    Separating file storage from business data supports:
    
    - scalability
    - efficient large-file storage
    - controlled file access
    - independent storage lifecycle
    - future CDN/storage integrations
    
    ### Consequence
    
    The application must never expose unrestricted object-storage URLs for protected content.
    
    The exact provider/storage implementation will be decided during System Architecture.
    
    ---
    
    # ADR-006 — Secure Content Delivery Instead of Direct File Distribution
    
    **Status:** Accepted
    
    ### Context
    
    The fundamental problem identified for AEGIS is that organizations currently distribute training presentations to trainers, creating risks of copying, reuse and unauthorized distribution.
    
    ### Decision
    
    AEGIS will provide controlled access to training content through the application rather than treating downloadable source files as the normal delivery mechanism.
    
    ### Rationale
    
    This directly addresses the core product problem:
    
    ```
    Traditional
    Organization
        ↓
    Presentation File
        ↓
    Trainer
        ↓
    Uncontrolled Copying / Distribution
    ```
    
    versus:
    
    ```
    AEGIS
    Organization
        ↓
    Protected Content
        ↓
    Controlled Web Delivery
        ↓
    Authorized Trainer
        ↓
    Auditable Activity
    ```
    
    ### Consequence
    
    Content delivery becomes a security-sensitive subsystem rather than a simple file-download feature.
    
    ---
    
    # ADR-007 — Immutable Content Versions
    
    **Status:** Accepted
    
    ### Context
    
    Organizations need content consistency and historical traceability.
    
    Changing a published file in place could make it impossible to determine what trainers previously accessed.
    
    ### Decision
    
    Treat published content versions as **immutable historical records**.
    
    A modification results in a new version.
    
    ```
    Content
     ├── V1 — Historical
     ├── V2 — Historical
     └── V3 — Current
    ```
    
    ### Rationale
    
    Provides:
    
    - historical traceability
    - auditability
    - reproducibility
    - safer content management
    
    ### Consequence
    
    The system must maintain explicit version relationships and lifecycle state.
    
    ---
    
    # ADR-008 — Server-Side Authorization
    
    **Status:** Accepted
    
    ### Context
    
    AEGIS protects proprietary organizational content.
    
    Frontend-only authorization cannot be considered a security boundary.
    
    ### Decision
    
    All access-control decisions must ultimately be enforced by the backend.
    
    ### Rationale
    
    A malicious user can bypass frontend controls.
    
    Therefore:
    
    ```
    Frontend
        ↓
    User Experience
    
    Backend
        ↓
    Security Boundary
    ```
    
    ### Consequence
    
    Every protected operation must validate authorization independently of the UI.
    
    ---
    
    # ADR-009 — Auditability as a First-Class Capability
    
    **Status:** Accepted
    
    ### Context
    
    AEGIS is not only a content management system. A major product objective is accountability and visibility into content usage.
    
    The project proposal explicitly includes access logging, trainer activity tracking and audit reports.
    
    ### Decision
    
    Auditing and activity tracking will be treated as first-class architectural capabilities rather than optional logging added later.
    
    ### Rationale
    
    This enables:
    
    - accountability
    - security investigation
    - usage analysis
    - compliance-oriented reporting
    - future analytics
    
    ### Consequence
    
    Audit/event architecture must be considered when designing major modules.
    
    ---
    
    # ADR-010 — Dynamic Watermarking as a Content-Protection Layer
    
    **Status:** Accepted
    
    ### Context
    
    The product needs mechanisms to discourage unauthorized distribution of protected training content.
    
    ### Decision
    
    Use dynamic watermarking as an additional protection/accountability layer during protected content delivery.
    
    ### Rationale
    
    The project proposal explicitly identifies dynamic watermarking as part of the proposed solution.
    
    ### Important Boundary
    
    Watermarking is **not considered DRM**.
    
    It is a deterrence and accountability mechanism.
    
    Advanced DRM-inspired protection remains future scope.
    
    ---
    
    # ADR Register
    
    | ADR | Decision | Status |
    | --- | --- | --- |
    | ADR-001 | Django backend | ✅ Accepted |
    | ADR-002 | Organization-centric multi-tenancy | ✅ Accepted |
    | ADR-003 | Shared DB + logical tenant isolation | ✅ Accepted |
    | ADR-004 | PostgreSQL primary database | 🟡 Proposed |
    | ADR-005 | Object storage for content files | 🟡 Proposed |
    | ADR-006 | Secure application-based content delivery | ✅ Accepted |
    | ADR-007 | Immutable content versions | ✅ Accepted |
    | ADR-008 | Server-side authorization | ✅ Accepted |
    | ADR-009 | Auditability as first-class capability | ✅ Accepted |
    | ADR-010 | Dynamic watermarking | ✅ Accepted |
    
    ---