## AEGIS: Enterprise Knowledge Protection and Delivery Platform

**Project:** MCA Project

**Project Title:** AEGIS – Enterprise Knowledge Protection and Delivery Platform

**Prepared By:** Princy W [2436MCA0001]

**Date:** Septemper 2026

**Technology Direction:** Python Django, Web-based Frontend, PostgreSQL-compatible relational database

**Phase 1:** Business Rules 

**Purpose:** Define enforceable business/domain rules derived from the PRD, SRS and Domain Model.

- Business Rules
    
    ## BR-001 — Organization is the Tenant Boundary
    
    Every organization is an independent tenant within AEGIS.
    
    - Organization-owned data must belong to exactly one organization.
    - Users operate within an organization context.
    - Content, training programs, access grants, activity records and audit records must not cross organization boundaries.
    - A user belonging to one organization must not be able to access another organization’s resources.
    
    **Principle:** Tenant isolation is a fundamental business rule, not merely a database implementation detail.

    ---
    
    ## BR-002 — Users Must Belong to an Organization
    
    A user must belong to an organization before accessing organization-owned resources.
    
    - A user cannot access organizational content without organizational membership.
    - User identity and organization membership must be validated before granting access.
    
    ---
    
    ## BR-003 — Access is Role/Permission Controlled
    
    Users may perform actions only when their assigned role/permissions allow those actions.
    
    Examples:
    
    - Administrators can manage organizational resources according to their permissions.
    - Trainers can access content granted to them.
    - A trainer cannot perform administrative content-management actions unless explicitly authorized.
    
    ---
    
    ## BR-004 — Authentication is Required for Protected Resources
    
    A user must be authenticated before accessing protected AEGIS resources.
    
    Unauthenticated users must not be able to access protected training content or organizational resources.
    
    ---
    
    # Content Rules
    
    ## BR-005 — Content Belongs to an Organization
    
    Every content item must belong to exactly one organization.
    
    Content ownership determines the organization that controls:
    
    - content lifecycle
    - versions
    - assignments
    - access
    - auditability
    
    ---
    
    ## BR-006 — Content is Delivered Through AEGIS
    
    The primary purpose of AEGIS is controlled content delivery.
    
    Authorized trainers should access training material through the secure platform rather than receiving the original presentation files directly.
    
    This directly supports the project’s core objective of protecting proprietary training material.
    
    ---
    
    ## BR-007 — Original Content Must Not Be Exposed Unnecessarily
    
    The system must not expose the underlying original content file to users merely because they have permission to view/use the content.
    
    Content delivery must occur through the controlled AEGIS delivery mechanism.
    
    ---
    
    ## BR-008 — Content Has a Lifecycle
    
    Content must have a controlled lifecycle.
    
    Conceptually:
    
    ```
    Draft → Published → Archived
    ```
    
    Only content in an appropriate state may be made available for training delivery.
    
    ---
    
    ## BR-009 — Published Content is Controlled
    
    A published content version represents an approved version for delivery.
    
    A trainer must not modify published content.
    
    Changes to published material must result in a new content version rather than silently modifying the existing published version.
    
    ---
    
    # Versioning Rules
    
    ## BR-010 — Content Version History Must Be Preserved
    
    Every meaningful content revision must be represented as a distinct version.
    
    Historical versions must remain identifiable.
    
    ---
    
    ## BR-011 — New Versions Must Not Destroy Historical Versions
    
    Creating a new version must not overwrite or delete the historical version’s identity or audit history.
    
    For example:
    
    ```
    Content
     ├── Version 1
     ├── Version 2
     └── Version 3 ← Current
    ```
    
    The existence of Version 3 must not make Version 1 or Version 2 disappear from historical records.
    
    ---
    
    ## BR-012 — One Version is the Current Delivery Version
    
    A content item may have multiple historical versions, but the system must identify which version is currently approved/active for delivery.
    
    ---
    
    ## BR-013 — Version Changes Must Be Auditable
    
    Important version lifecycle actions must generate an auditable record.
    
    Examples:
    
    - version created
    - version published
    - version archived
    - version activated/deactivated
    
    ---
    
    # Training Program Rules
    
    ## BR-014 — Training Programs Group Content
    
    A Training Program provides the business context in which multiple content items can be organized and delivered.
    
    ```
    Training Program
          │
          ├── Content Assignment
          ├── Content Assignment
          └── Content Assignment
    ```
    
    ---
    
    ## BR-015 — Content Assignment Does Not Automatically Grant User Access
    
    Assigning content to a Training Program does not by itself mean that every trainer can access that content.
    
    Content availability and user access remain separate concepts.
    
    This preserves the distinction established in the Domain Model:
    
    ```
    Content
       ↓
    Content Assignment
       ↓
    Training Program
    
    > **No access grant → No content access.**
    > 
    
    ---
    
    ## BR-017 — Access Must Belong to the Correct Organization
    
    An access grant must not provide cross-organization access.
    
    A trainer from Organization A cannot use an access grant belonging to Organization B.
    
    ---
    
    ## BR-018 — Access is Subject to Authorization
    
    Having an authenticated account does not automatically provide access to all content.
    
    The system must evaluate:
    
    ```
    Authentication
          ↓
    Organization membership
          ↓
    Permission
          ↓
    Training/content access
          ↓
    Content delivery
    ```
    
    ---
    
    ## BR-019 — Access Can Be Revoked
    
    Previously granted access must be revocable.
    
    Once access is revoked, the user must no longer be permitted to initiate new access to that protected resource.
    
    ---
    
    ## BR-020 — Access Activity Must Be Traceable
    
    Access to protected content must generate activity information sufficient to determine:
    
    - who accessed it
    - what content was accessed
    - which version was accessed
    - when it was accessed
    - relevant access/session context
    
    ---
    
    # Trainer Rules
    
    ## BR-021 — Trainer Access is Controlled
    
    A trainer can access only the training resources authorized for that trainer.
    
    Being registered as a trainer does not itself imply unrestricted access to organizational content.
    
    ---
    
    ## BR-022 — Trainers Cannot Modify Organizational Content
    
    Trainers are consumers/deliverers of authorized training content, not owners of the organization’s proprietary source content.
    
    Unless explicitly granted an appropriate permission, trainers cannot:
    
    - modify content
    - publish content
    - archive content
    - create organizational content versions
    - alter content assignments
    
    ---
    
    ## BR-023 — Trainer Activity is Trackable
    
    Significant trainer interactions with protected content must be recorded for activity tracking and accountability.
    
    This supports the project’s stated requirement for trainer activity tracking and analytics.
    
    ---
    
    # Watermark Rules
    
    ## BR-024 — Protected Content May Be Dynamically Watermarked
    
    Protected training content may be presented with a dynamic watermark associated with the accessing user/session.
    
    The watermark is intended to establish accountability and discourage unauthorized distribution.
    
    ---
    
    ## BR-025 — Watermark Information Must Reflect the Access Context
    
    Where watermarking is applied, the watermark should contain information that helps associate the displayed content with its authorized access context.
    
    The exact watermark fields are an implementation/design decision to be finalized later.
    
    ---
    
    # Audit Rules
    
    ## BR-026 — Security-Relevant Actions Must Be Auditable
    
    Security-sensitive and important business actions must produce audit records.
    
    Examples:
    
    ```
    Login
    Content access
    Content creation
    Content modification
    Version creation
    Version publication
    Access grant
    Access revocation
    Permission changes
    Security events
    ```
    
    ---
    
    ## BR-027 — Audit Records Must Be Historical
    
    Audit records must represent what happened at the time of the event.
    
    Normal business operations must not silently rewrite historical audit information.
    
    ---
    
    ## BR-028 — Activity and Audit are Different Concepts
    
    AEGIS must distinguish between:
    
    **Activity**
    
    > What users did during normal interaction with the system.
    > 
    
    and
    
    **Audit**
    
    > Evidence of important business/security events that must be retained for accountability.
    > 
    
    This distinction is important as the platform grows.
    
    ---
    
    # Security Rules
    
    ## BR-029 — Authorization Must Be Enforced Server-Side
    
    Security decisions must not depend solely on frontend controls.
    
    The backend must enforce:
    
    - organization boundaries
    - authentication
    - permissions
    - content access
    - version access
    - protected resource access
    
    ---
    
    ## BR-030 — Access Denial Must Not Reveal Protected Content
    
    When access is denied, the system must not expose the protected resource merely through error responses, URLs, metadata or alternate access paths.
    
    ---
    
    ## BR-031 — Sessions Must Be Controlled
    
    Authenticated access must be associated with a valid authentication session.
    
    Session-related security events may be recorded for accountability.
    
    ---
    
    # Data Integrity Rules
    
    ## BR-032 — Required Domain Relationships Must Be Valid
    
    Domain entities must not reference resources that do not exist or belong to an incompatible organization.
    
    ---
    
    ## BR-033 — Historical Records Must Remain Consistent
    
    Deleting or changing a current business object must not unintentionally destroy information required for:
    
    - auditing
    - historical version tracking
    - activity tracking
    - security investigation
    
    ---
    
    ## BR-034 — Business Rules Must Apply Regardless of Client
    
    The same authorization and business rules must apply whether the request originates from:
    
    - web UI
    - future mobile application
    - API
    - other future clients
    
    This prevents security rules from becoming UI-dependent.
    
    ---
    
    # MVP Boundary Rules
    
    ## BR-035 — MVP Focuses on Secure Content Delivery
    
    The MVP focuses on:
    
    ```
    Organization
    Users / Roles / Permissions
    Content
    Content Versions
    Training Programs
    Content Assignments
    Training Access
    Content Access
    Activity Tracking
    Audit Records
    Security Events
    Dynamic Watermarking
    Authentication Sessions
    ```
    
    ---
    
    ## BR-036 — Future Capabilities Do Not Become MVP Dependencies
    
    The following remain future enhancements rather than mandatory MVP business rules:
    
    - AI-based trainer performance analysis
    - DRM-inspired advanced content protection
    - live training analytics
    - mobile application
    - offline encrypted content viewer
    - external application integrations
    
    These are explicitly identified as future enhancements in the project proposal.
    
    ---

            ## BR-037 — Security Events Have Explicit Scope and Severity

            Security events are stored in one security-event model and have either tenant scope or platform scope.

            - A resolved organization is recorded as `organization_id` for tenant-scoped events.
            - `organization_id` may be null only for platform-level events that occur before organization resolution, such as an authentication attempt using an unknown organization slug.
            - An unresolved organization attempt must never be assigned to a default or guessed tenant.
            - Organization-level users must not access platform-level events or events belonging to another organization.
            - Activity events remain tenant-owned and must always have an organization.
            - Authentication failures must remain generic to clients regardless of whether organization or user resolution succeeded.
            - Security event severity must be one of `INFO`, `LOW`, `MEDIUM`, or `HIGH`.
            - Authentication events use the documented severity mapping in Data Architecture.

            Event metadata must be minimal and sanitized. Passwords, session tokens, and other authentication secrets must never be recorded.

            ---

            ## BR-038 — Authentication Attempts are Rate-Limited

            Apply independent rolling-window limits by normalized organization-scoped account identifier and source IP:

            - Five failed attempts for an account within 15 minutes cause a 15-minute temporary account block.
            - Twenty failed attempts from a source IP within 15 minutes cause a 15-minute temporary IP block.
            - A successful login clears that account's failure counter but does not clear the IP counter.
            - Rate-limit responses remain generic and must not disclose whether an organization or account exists.
            - Record rate-limit triggers as `LOGIN_FAILURE` Security Events with `MEDIUM` severity and sanitized metadata.
            - Use shared, atomic storage; process-local counters are not sufficient.
            - Do not trust arbitrary client-supplied forwarded-IP headers. Use the direct request source unless an explicitly trusted proxy is configured.
            - Do not log passwords, session tokens, or raw account identifiers in counter storage.

            The independent IP limit, generic responses, and security monitoring reduce account-lockout abuse. Progressive delays or additional controls require a separate documented decision.