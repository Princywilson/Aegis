# AEGIS — Controlled AI Feature Scope Expansion and Implementation

## 1. Role and Objective

You are the existing development agent responsible for the AEGIS (Enterprise Knowledge Protection and Delivery Platform) codebase. You developed the current AEGIS MVP, so you must build upon the actual implementation, established development patterns, and documented architectural decisions.

We are now initiating a **controlled scope expansion** of the completed AEGIS MVP to introduce three related capabilities:

1. Context-Aware Content Access Policies.
2. Content Exposure Risk Investigation.
3. Permission-Aware RAG Enterprise Knowledge Assistant.

The objective is to enhance AEGIS with meaningful, demonstrable AI capabilities and a defensible technical contribution while preserving the existing platform's architecture, functionality, security controls, and domain-neutral design.

This is an extension of the existing platform, NOT a rewrite, replacement, or architectural redesign.

**Primary directive:** Understand the existing system before proposing or implementing changes. Reuse existing components wherever appropriate. Do not assume that a feature, model, API, service, or integration is absent until the codebase has been inspected.

---

## 2. Mandatory Project Instructions and Sources of Truth

Before making any changes, inspect and follow the following resources in the order described below.

### 2.1 `Agent/` — Mandatory Development Rules

Read and follow all applicable instructions under the `Agent/` directory.

These rules govern AEGIS development, enhancements, implementation practices, testing, documentation, and change management.

Do not bypass, reinterpret, or replace these instructions with your own preferred workflow.

If the directory contains an implementation guide, follow its prescribed development approach for every new feature and enhancement.

If instructions are distributed across multiple files, identify and read all relevant files, including any applicable nested instructions.

### 2.2 `docs/` — Authoritative Project Documentation

Inspect the project documentation under `docs/` before deciding the scope or design.

Read the relevant existing documents covering, at minimum, the following areas wherever they exist:

- Product requirements and product scope.
- Software requirements and functional/non-functional requirements.
- Domain model and domain terminology.
- Business rules.
- Architecture Decision Records (ADRs).
- Functional architecture and module responsibilities.
- Database design and data relationships.
- System architecture and security architecture.
- API specifications and API conventions.
- UI/UX specifications.
- Implementation guides and development conventions.
- Testing, deployment, configuration, and operational documentation.

Use the actual document names and structure present in the repository. Do not assume every item above exists as a separate file.

Treat these documents and the current implementation as the primary sources of truth. When something is unclear, investigate the relevant documentation and code before asking for clarification.

Do not silently resolve contradictory requirements by inventing a new business rule or changing an accepted architectural decision.

If the new scope conflicts with an existing requirement, business rule, ADR, or security constraint, document the conflict and request clarification where a decision is necessary.

### 2.3 Reference Repository Diagram

Reference: https://gitdiagram.com/princywilson/aegis

Use this diagram as supplementary architectural context if accessible.

The diagram is not a replacement for inspecting the actual source code, `Agent/`, or `docs/`. If the diagram is unavailable, outdated, or inconsistent with the implementation, proceed using the repository and authoritative project documentation.

### 2.4 Existing Source Code

Inspect the existing application before proposing changes.

Understand the actual implementation of:

- Frontend and backend structure.
- Existing modules, services, models, APIs, and UI components.
- Authentication and session management.
- Organization/tenant isolation.
- Roles, permissions, and content access enforcement.
- Content management, storage, and content versioning.
- Activity tracking, audit records, and security events.
- Existing background processing, integrations, and configuration.
- Existing tests, fixtures, and development conventions.

Do not create duplicate functionality where a suitable implementation already exists.

---

## 3. Non-Negotiable Development Rules

### Rule 1 — Preserve the Existing Architecture

**Do not modify or redesign the existing architecture without prior explanation and explicit approval.**

Continue using the established stack:

- Frontend: React.
- Backend: Python Django.
- Primary database: PostgreSQL.

Follow the actual frameworks, patterns, application boundaries, dependency management, and service organization already implemented in the repository.

Do not independently introduce:

- A new architectural style or service decomposition.
- Microservices or a separate AI backend.
- A new database or data-storage platform.
- A new message broker, vector database, search engine, or orchestration framework.
- A replacement authentication or authorization system.
- A new permission model.
- A new AI provider, external service, or infrastructure dependency.

These are not blanket prohibitions against every additional dependency. They mean that any proposed addition must be justified against the current architecture and approved before implementation if it materially changes the design, infrastructure, security posture, or operational requirements.

If a proposed feature cannot be implemented safely within the current architecture, stop before implementing the architectural change. Present the options, reasons, impacts, risks, and recommendation for approval.

### Rule 2 — Preserve Existing Functionality

- Do not rewrite completed modules merely to accommodate the new features.
- Do not remove, rename, or change existing public APIs, models, routes, permissions, or behaviors without approval.
- Do not introduce breaking database migrations or API changes without documenting their necessity and obtaining approval.
- Prefer small, isolated, backward-compatible changes.
- Reuse existing services, models, permissions, and UI components where appropriate.
- Do not modify unrelated files.
- Preserve existing behavior unless a documented requirement explicitly authorizes a change.

### Rule 3 — Follow Existing Implementation Patterns

Follow the implementation guide and established repository conventions for:

- File and module organization.
- Naming and domain terminology.
- Backend services and data access.
- API request and response formats.
- Validation and error handling.
- Frontend component structure and state management.
- Authentication and authorization.
- Logging and auditability.
- Configuration and environment variables.
- Database migrations.
- Automated tests and test fixtures.

Do not introduce unnecessary abstractions, dependencies, or duplicate layers.

### Rule 4 — Security First

All new capabilities must preserve AEGIS's security guarantees.

In particular:

- Enforce organization/tenant isolation in every applicable data access path.
- Enforce server-side authorization for every protected operation.
- Never trust frontend-only permission checks.
- Do not expose unauthorized content through APIs, search results, AI prompts, generated answers, citations, logs, error messages, caches, or background jobs.
- Never allow an AI model to independently grant, expand, or override a user's permissions.
- Do not expose credentials, API keys, tokens, private content, or sensitive configuration.
- Validate inputs and handle errors safely.
- Apply least-privilege principles.
- Maintain appropriate audit trails for security-relevant actions.
- Keep access revocation effective for subsequent protected operations, including AI retrieval and content delivery.
- Follow existing session, access-control, and content-delivery rules.

Treat AI-generated output as untrusted input. Do not execute generated content or treat it as an instruction that overrides application security policies.

### Rule 5 — Maintain Domain-Neutral Terminology

AEGIS must remain an industry-independent enterprise knowledge protection and delivery platform.

Use the existing domain terminology consistently, including Organization, User, Role, Permission, Content, Content Version, Program, Assignment, Workspace, Activity, Audit, and Notification where those concepts are relevant to the actual implementation.

Do not introduce industry-specific concepts or labels associated with training, education, healthcare, finance, safety, or another industry unless explicitly required by an approved product requirement.

Do not blindly replace precise existing concepts with generic synonyms. Follow the established domain model and choose terminology based on the actual business meaning.

### Rule 6 — Documentation Is Part of the Implementation

Every approved feature implementation must update all relevant documentation under `docs/`.

Documentation must describe the actual delivered behavior, not merely the intended design.

Keep requirements, business rules, architecture, APIs, data models, security considerations, testing guidance, and implementation documentation consistent.

Do not silently overwrite accepted decisions. If an ADR must change, explain the reason and follow the repository's ADR process.

### Rule 7 — No Unsupported AI Claims

Do not label a feature as AI-powered simply because it uses rules, thresholds, keyword matching, or ordinary database queries.

Clearly distinguish between:

- Deterministic authorization and policy enforcement.
- Rule-based detection.
- Statistical anomaly detection.
- Machine-learning-based anomaly detection.
- Retrieval-Augmented Generation (RAG).
- Ordinary search and retrieval.

Use the technique that is justified by the requirements, available data, and evaluation results. Do not claim model accuracy, AI effectiveness, or successful detection without evidence.

---

## 4. New Scope: Capability A — Context-Aware Content Access Policies

### 4.1 Objective

Extend the existing access-protection capabilities to identify contextual signals that may indicate unusual or potentially risky content-access behavior.

The existing authorization system remains the authority for access decisions. Contextual analysis supplements existing security controls; it does not replace them.

### 4.2 Initial investigation

Before designing this capability, inspect the existing:

- Role and permission enforcement.
- Content access policies and access-control services.
- Activity records and security events.
- Authentication and session-related events, where available.
- Content sensitivity or classification fields, if implemented.
- Existing access monitoring and audit functionality.

Identify what information is already collected, which features can be derived from it, and which data gaps would prevent reliable detection.

Do not invent fields, event types, or business rules without documenting their necessity.

### 4.3 Expected behavior

Subject to the existing implementation and approved requirements, the feature may:

- Identify unusual access frequency or bursts of requests.
- Identify repeated access denials or other suspicious request patterns.
- Identify unusually broad access to different resources within a time window.
- Compare observed activity with an appropriate historical or statistical baseline.
- Consider contextual signals supported by available, authorized data.
- Produce explainable indicators that describe why an event or pattern was flagged.

Not every signal must become a detection rule. Establish the final set based on feasibility, data availability, meaningfulness, and evaluation.

### 4.4 Detection strategy

Start by evaluating the simplest defensible approach.

1. Establish the available event data and its quality.
2. Define candidate behavioral features and baseline requirements.
3. Establish a transparent baseline using rules or statistical methods where appropriate.
4. Evaluate whether a machine-learning method adds measurable value.
5. Propose any additional model or dependency only when justified and approved.

If an unsupervised method such as Isolation Forest is considered, explain its suitability, data requirements, limitations, and evaluation strategy before selecting it.

Do not introduce machine learning merely to satisfy the word "AI."

### 4.5 Security and behavior constraints

- Existing permission checks remain authoritative.
- A detected anomaly is not proof of malicious intent.
- False positives must be anticipated and measured where feasible.
- Detection must not expose another organization's activity.
- Detection results must not reveal protected content to unauthorized users.
- Do not automatically block, suspend, or change a user's access solely because a model flags an anomaly unless a separate, explicitly approved policy authorizes that action.
- Preserve the distinction between activity records, audit records, and security events.

**Approved v1 implementation note:** Detection is deterministic and advisory. The current `ACCESS_BURST` rule uses at least four granted Content Access records across at least three distinct Content items in a rolling 24-hour window; `REPEATED_DENIALS` uses at least three normal `ACCESS_DENIED` Security Events for Content in a rolling 24-hour window. Current severities are LOW and MEDIUM respectively. These values preserve existing implementation behavior; they are not a validated risk score or formally approved business policy. The implementation reuses existing records and does not add a signal table or alter authorization.

---

## 5. New Scope: Capability B — Content Exposure Risk Investigation

### 5.1 Objective

Provide an evidence-based workflow for authorized administrators to review potentially risky content-access activity using existing activity tracking, audit records, security events, and the approved detection capability.

The objective is to help administrators understand what happened, when it happened, which resources may be involved, and why the activity was flagged.

Do not represent a suspected exposure as a confirmed breach without supporting evidence.

### 5.2 Initial investigation

Inspect existing:

- Activity and audit data models.
- Security-event representation.
- Content and content-version relationships.
- User and organization relationships.
- Existing monitoring or administration interfaces.
- Audit immutability and retention rules.
- Existing authorization and access-revocation mechanisms.

Determine which investigation capabilities can be implemented by reusing existing records and which require a formally approved extension.

### 5.3 Expected behavior

Design an investigation workflow that may include:

- A list of detected or reported security concerns.
- Risk indicators or severity levels with documented definitions.
- A timeline of relevant, authorized activity.
- References to affected resources and related events.
- Clear explanations of the signals that triggered an alert.
- An investigation status and authorized administrative actions.
- Investigation notes or resolution details where appropriate.
- An audit trail of investigation-related changes.

The precise workflow, status transitions, severity definitions, and permissions must be derived from documented requirements or presented for approval. Do not invent business rules silently.

### 5.4 Evidence and auditability

- Link findings to the underlying records whenever possible.
- Preserve original event records and their historical meaning.
- Do not rewrite historical audit events to reflect current conclusions.
- Distinguish observed facts, model-generated assessments, and administrator conclusions.
- Record relevant administrative actions through the existing audit mechanism.
- Apply organization isolation and authorization to both alerts and their underlying evidence.
- Avoid including unnecessary sensitive content in alert summaries.

**Approved v1 implementation boundary:** Investigation records reuse the existing `RiskInvestigation` model and `AuditRecord` system. Evidence is stored as bounded references to supported Security Events or Audit Records, validated against current organization and source permissions on attachment, and re-resolved under current permissions when read. Meaningful investigation mutations and their audit entries are atomic; audit metadata does not contain raw notes, summaries, or titles. The React workflow provides organization-scoped list/detail/create/edit and the existing status lifecycle. These implementation details do not change the future design requirements above or make a risk signal an authorization decision.

### 5.5 AI's role

AI may help identify patterns, correlate relevant signals, or summarize available evidence if justified by the requirements.

Any generated summary must remain grounded in authorized records. It must not fabricate events, attribute intent without evidence, or present speculative conclusions as established facts.

Provide references to the supporting records so that an administrator can independently verify the findings.

---

## 6. New Scope: Capability C — Permission-Aware RAG Enterprise Knowledge Assistant

### 6.1 Objective

Introduce a Retrieval-Augmented Generation capability that allows authorized users to ask natural-language questions about enterprise content and receive answers grounded in relevant content they are permitted to access.

This feature must integrate with AEGIS's existing content governance and access-control mechanisms.

The key contribution is not simply adding a chatbot. It is enabling useful knowledge retrieval and grounded answers while preserving organization isolation, content permissions, and access revocation.

**Approved implementation boundary:** The current v1 is a permission-aware, retrieval-only metadata search. It matches authorized Content titles and descriptions and returns source metadata; it does not extract document bodies, perform semantic retrieval, or generate answers. Do not call this implementation a completed generative RAG assistant. Document-body retrieval and generation require separate design and approval.

### 6.2 Initial investigation

Inspect the existing implementation of:

- Content upload and content processing.
- Supported content formats.
- Content versions and version lifecycle.
- Object storage and content-delivery mechanisms.
- User, organization, role, and permission relationships.
- Existing search or indexing functionality, if any.
- Existing APIs and frontend patterns.
- Configuration, dependency management, and deployment requirements.

Determine whether existing components can support document extraction, chunking, indexing, retrieval, and source references.

Do not assume a vector database, embedding model, LLM provider, or RAG framework is already installed.

### 6.3 Proposed processing flow

Design a permission-aware retrieval pipeline consistent with the current architecture:

1. Identify content that is eligible for indexing under the existing content lifecycle and access rules.
2. Extract supported text from eligible content using approved processing components.
3. Divide extracted content into appropriate chunks while preserving source and version references.
4. Create the selected search or retrieval representation using an approved approach.
5. Associate indexed material with the correct organization, content, content version, and source metadata.
6. At query time, authenticate the user and establish their current authorization context.
7. Restrict retrieval to content the user is currently permitted to access.
8. Retrieve relevant passages from that authorized result set.
9. Generate an answer grounded in those passages.
10. Return source references that identify the supporting content and relevant passage or section where feasible.
11. Apply safe response handling and ensure no unauthorized content is returned.

This is a logical workflow, not permission to introduce a new architecture. Adapt it to the existing codebase and approved design.

### 6.4 Mandatory permission-aware retrieval

**Authorization must be enforced before protected content reaches the generation model.**

Do not retrieve unrestricted cross-tenant or cross-user content and rely on the LLM to decide what it may reveal.

Specifically:

- Apply organization isolation to indexing, retrieval, caches, and source references.
- Apply current user permissions to the candidate retrieval set.
- Prevent unauthorized passages from entering the model context.
- Validate source access before returning citations or document links.
- Ensure revocation and permission changes are reflected in subsequent retrieval requests.
- Prevent indirect leakage through generated answers, metadata, snippets, errors, and logs.
- Treat retrieved document text as untrusted data, not as system instructions.
- Defend against prompt injection in indexed content and user queries using appropriate controls.
- Keep provider credentials in approved environment-based configuration.
- Follow applicable content retention and deletion requirements.
- Do not send protected content to an external AI provider unless the data flow, provider, privacy implications, and configuration have been explicitly reviewed and approved.

If permissions cannot be enforced reliably with the existing architecture, stop and report the specific gap before implementing an unsafe workaround.

**Approved v1 implementation boundary:** The initial release is live metadata retrieval only. It reuses organization-scoped Content, current ContentVersion, Program, assignment, grant, and RBAC query rules; validates current permissions on each request; and derives citation Program names only from Programs visible to the caller. It performs case-insensitive substring matching over Content title and description, returns at most five metadata citations, and stores no chunks or index. No protected content is sent to a model because no model is called. This is not a completed generative RAG assistant; semantic retrieval and generation remain future work requiring separate design and approval.

### 6.5 Answer quality and transparency

Where supported by the selected retrieval and generation approach:

- Provide answers grounded in retrieved passages.
- Include source references that allow users to verify important claims.
- Avoid inventing information when retrieved material is insufficient.
- State when the available content does not adequately answer the question.
- Distinguish source-derived statements from generated interpretation where useful.
- Handle empty retrieval results, extraction failures, timeouts, and provider failures gracefully.
- Avoid exposing internal prompts, secrets, or unauthorized source information.

### 6.6 Content and version lifecycle

Investigate how indexing must interact with:

- New content.
- New content versions.
- Updated content.
- Content deactivation or deletion.
- Permission changes.
- Organization membership changes.
- Access revocation.

Define how stale or superseded indexed content will be handled. Do not allow retrieval to bypass existing content lifecycle or versioning rules.

---

## 7. Cross-Capability Integration

The three capabilities must form a coherent extension without creating unnecessary coupling.

### 7.1 Existing security controls remain authoritative

The existing authentication, permission enforcement, content-delivery controls, and tenant-isolation mechanisms remain the security foundation.

AI components must operate within those boundaries.

### 7.2 Reuse existing activity and audit records

Reuse the existing event and audit infrastructure wherever possible.

Do not create competing activity logs, audit systems, or security-event models without an explicit architectural justification and approval.

### 7.3 Separation of responsibilities

Keep the responsibilities distinct:

- Access-control services decide whether an operation is authorized.
- Detection services identify potentially unusual activity.
- Investigation services organize findings and supporting evidence.
- Retrieval services select content the current user is authorized to access.
- Generation services produce grounded answers from authorized retrieved content.
- Audit services record applicable security-relevant actions.

Use the existing module boundaries and implementation patterns rather than forcing these responsibilities into newly invented architectural layers.

### 7.4 Failure handling

Define safe behavior for:

- AI provider unavailability.
- Retrieval and indexing failures.
- Incomplete or malformed source content.
- Detection model failures.
- Missing or stale evidence.
- Permission changes during processing.
- Background processing failures, if applicable.

AI failures must not weaken existing authorization, leak protected content, or cause the application to misrepresent an unverified result as confirmed.

---

## 8. Data, Database, and API Change Discipline

Before introducing any model, field, table, endpoint, or migration:

1. Check whether the required concept already exists.
2. Determine whether the existing schema can support it.
3. Explain why a change is necessary.
4. Identify the impact on current functionality and existing data.
5. Follow the approved database and API design conventions.
6. Document security, tenant-isolation, indexing, and performance implications.
7. Obtain approval for material architectural changes.

Any approved schema changes must have appropriate migrations and tests.

Avoid unnecessary duplication of content, event, user, organization, and permission data.

For new APIs, follow the existing routing, serialization, validation, authentication, authorization, error-handling, and response-format conventions.

Do not silently change existing API contracts.

---

## 9. Testing and Evaluation Requirements

Testing is mandatory, not optional.

### 9.1 Regression testing

Run the existing relevant test suite and ensure that the completed MVP's behavior remains intact.

Add tests using the project's established testing framework and conventions.

### 9.2 Security testing

Include appropriate tests for:

- Cross-organization data access.
- Unauthorized access to alerts and investigation evidence.
- Unauthorized content retrieval through RAG.
- Citation and source-link authorization.
- Permission revocation and membership changes.
- Stale indexed content and content-version changes.
- Malicious or instruction-like text in retrieved documents.
- Invalid requests and unsafe error handling.
- AI provider failures and partial processing failures.

Test both positive and negative authorization cases.

### 9.3 Context-aware detection evaluation

Where feasible, evaluate:

- Detection precision and recall using a suitable labelled dataset.
- False-positive rate.
- Detection latency.
- Coverage of the implemented detection scenarios.

If real labelled data is unavailable, use clearly documented synthetic or controlled test events. Do not present synthetic results as evidence of real-world effectiveness.

If a metric cannot be measured meaningfully, document why.

### 9.4 Investigation workflow evaluation

Verify that:

- Alerts link to relevant supporting records.
- Evidence is restricted to authorized users in the correct organization.
- Status changes and administrative actions are recorded appropriately.
- Findings distinguish observed events from inferred risk.
- Historical audit records remain intact.

### 9.5 RAG evaluation

Evaluate, as appropriate:

- Retrieval relevance.
- Answer grounding and source correctness.
- Citation validity.
- Handling of insufficient source material.
- Resistance to unauthorized retrieval.
- Tenant-isolation enforcement.
- Behavior after permission changes and content-version updates.
- Failure handling and response latency.

Do not claim that the assistant is secure or accurate merely because a few manual queries work.

---

## 10. AI Dependencies, Providers, and Configuration

Before selecting an AI provider, embedding model, vector index, retrieval framework, or other dependency:

1. Inspect the current dependency list and installed infrastructure.
2. Determine whether an existing component can fulfil the requirement.
3. Compare suitable approaches against security, maintainability, cost, privacy, deployment, and performance constraints.
4. Identify whether content or metadata will leave the application environment.
5. Document the proposed approach and its implications.
6. Request approval before introducing dependencies or infrastructure that materially affect the existing architecture.

Do not hardcode secrets, provider credentials, endpoints that vary by environment, or private configuration.

Follow the existing environment-configuration and deployment conventions.

Document any required environment variables, setup steps, failure behavior, and operational prerequisites.

Do not make a paid external service mandatory without approval and an explicit configuration strategy.

---

## 11. Required Development Workflow

Follow the development approach prescribed by `Agent/` and the implementation guide.

The following gates are mandatory.

### Phase 1 — Repository and Documentation Review

- Read the relevant `Agent/` instructions.
- Review the applicable documents under `docs/`.
- Inspect the source code and existing tests.
- Map existing modules and security boundaries.
- Identify reusable functionality and existing gaps.

**Deliverable:** A concise assessment of the current implementation, relevant documents, constraints, and proposed scope.

Do not modify code in this phase.

### Phase 2 — Scope and Gap Analysis

Prepare a feature-by-feature analysis for all three capabilities.

For each capability, identify:

- Existing functionality to reuse.
- Missing functionality.
- Relevant domain entities and business rules.
- Expected user workflows.
- Security and authorization requirements.
- Proposed API and UI changes.
- Data and indexing implications.
- AI and external-dependency requirements.
- Testing and evaluation criteria.
- Risks, unresolved decisions, and dependencies.

Clearly distinguish requirements already established by the project documents from new proposals.

### Phase 3 — Design and Approval Gate

Prepare the proposed changes to the relevant requirements, business rules, architecture documents, ADRs, database design, API specification, and UI/UX documentation.

Identify any conflicts with existing accepted decisions.

**Do not proceed to implementation until the scope and design are reviewed and explicitly approved.**

If the existing architecture is insufficient for a requirement, present the smallest viable options and request approval before changing it.

### Phase 4 — Incremental Implementation

After approval:

- Follow the established implementation guide.
- Implement in small, logical increments.
- Preserve backward compatibility wherever possible.
- Reuse existing components.
- Add tests alongside the relevant implementation.
- Update the relevant documentation as changes are completed.
- Keep changes limited to the approved scope.
- Report any newly discovered architectural or security blocker before proceeding beyond the approved design.

Do not implement all three capabilities as one large, unreviewable change.

### Phase 5 — Verification and Completion

- Run relevant automated tests.
- Run regression tests.
- Verify tenant isolation and authorization.
- Evaluate AI behavior against the documented criteria.
- Verify error handling and configuration.
- Review the final changes for unrelated modifications and regressions.
- Ensure documentation reflects the actual implementation.

Do not claim completion for a feature that has only been designed, partially implemented, or manually demonstrated without the required verification.

---

## 12. Documentation Updates

Update all applicable documents under `docs/` according to the repository's existing structure.

Depending on the established documentation, this may include:

- Product scope and requirements.
- Functional and non-functional requirements.
- Domain model.
- Business rules.
- Architecture Decision Records.
- Functional architecture.
- Database design.
- System architecture.
- API specifications.
- UI/UX specifications.
- Security design and threat considerations.
- Implementation and configuration guides.
- Testing and evaluation documentation.
- Deployment and operational documentation.

Do not create duplicate documents when an existing document should be extended.

Maintain traceability between requirements, business rules, design decisions, implementation, and tests.

Document what changed, why it changed, which files or modules are affected, and which decisions remain open.

Do not mark future enhancements or proposed features as completed until they have actually been implemented and verified.

---

## 13. Final Expected Deliverables

At the end of the approved implementation, provide:

1. **Scope and gap analysis** — what already existed and what was added.
2. **Approved design summary** — how the enhancement fits within the existing architecture.
3. **Implementation summary** — the actual files, modules, APIs, models, and UI components changed.
4. **AI methodology** — the techniques used for anomaly detection and RAG, including why they were selected.
5. **Security assessment** — how authorization, tenant isolation, source access, and sensitive data are protected.
6. **Database and API changes** — migrations and contract changes, if any.
7. **Documentation updates** — the documents modified and their purpose.
8. **Testing results** — tests executed, results, limitations, and unresolved failures.
9. **AI evaluation results** — measured results where meaningful, with the dataset and limitations described.
10. **Configuration and setup instructions** — any approved dependencies, environment variables, and operational steps.
11. **Known limitations and future work** — clearly separated from completed capabilities.
12. **Demonstration plan** — a practical sequence showing the existing MVP, new capabilities, security enforcement, and AI outputs.

Also provide a clear before-and-after summary demonstrating how the enhancement addresses the identified problem beyond the original MVP.

---

## 14. Initial Execution Instructions

**Start with Phase 1 only. Do not immediately begin coding.**

First, inspect `Agent/`, the relevant project documents under `docs/`, the existing source code, and the available tests.

Then provide:

1. A summary of the existing architecture and relevant implementation.
2. A summary of the applicable development rules and constraints discovered in `Agent/`.
3. The relevant requirements and accepted architectural decisions found in `docs/`.
4. An assessment of how the three proposed capabilities map to the current implementation.
5. A list of reusable components and genuine gaps.
6. A preliminary feature scope and dependencies.
7. Any conflicts, ambiguities, security concerns, or architectural changes requiring approval.
8. A recommended incremental implementation order and verification plan.

Do not modify source code, database schemas, migrations, APIs, configuration, dependencies, or architecture during this initial assessment.

After presenting the assessment, **stop and wait for explicit approval** before proceeding to Phase 2 and the subsequent design and implementation gates.

If a required file, instruction, or decision is unavailable, report the specific gap rather than inventing its contents.

The final objective is to extend the completed AEGIS MVP with valuable, demonstrable, security-first AI capabilities while preserving the existing architecture, accepted decisions, domain-neutral terminology, and all working functionality.