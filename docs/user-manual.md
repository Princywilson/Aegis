# AEGIS User Manual

This manual describes the AEGIS application as it currently exists in the repository. It covers the React web interface and calls out backend capabilities that currently require API-level access. It does not describe proposed or future features as if they were available.

For installation, local environment setup, and step-by-step manual verification, use [implementation-setup.md](implementation-setup.md). The implementation and known gaps are tracked in [implementation-status.md](implementation-status.md).

## 1. What AEGIS does

AEGIS is an organization-scoped knowledge governance and delivery application. It allows authorized users to manage content and versions, group content into programs, control user access through assignments and grants, securely deliver rendered content, and review activity and reports.

AEGIS uses server-side authentication, permissions, organization isolation, access grants, assignments, and content publication/version state to decide whether an operation is allowed. A menu item being hidden or visible is not the authorization control; the backend remains authoritative.

## 2. Sign in and sign out

1. Open the AEGIS web address provided by your administrator.
2. On the sign-in page, enter:
   - **Organization slug** — the slug provided by your organization administrator.
   - **Email** — your organization account email.
   - **Password** — your assigned account password.
3. Select **Sign in**.
4. Confirm the workspace name and your role appear in the left navigation area.
5. To leave the application, select **Sign out** beside your account information. On desktop, account information stays pinned at the bottom of the sidebar while only the navigation list scrolls (without a visible scrollbar). On smaller screens, navigation is horizontal and the account section is hidden.

Sign-in uses a session and CSRF protection. AEGIS does not use a bearer-token login flow in the current application. Failed login messages are intentionally generic. If sign-in is rate limited, the page advises you to wait before trying again; it does not disclose an exact retry time or account state.

If you do not have an account, contact the organization administrator. There is no public self-registration page.

## 3. Roles and access

The organization administrator assigns roles and permissions. System roles are:

| Role | Typical capabilities |
|---|---|
| **Administrator** | Organization-level administration, user management, role and permission visibility, and broad access to application functions within that organization. |
| **Content Manager** | Create and manage content, upload and publish versions, manage programs, and assign content to programs. |
| **Content Consumer** | Search and view authorized content, open protected content, and review permitted personal activity and assigned-content reports. Access requires both an assignment and an active program access grant. |
| **Management** | Read-only access to the organization-level activity and reporting capabilities assigned to the role. This role does not include organization audit access in the current RBAC configuration. |

The role name does not replace access checks. For example, a Content Consumer needs an active grant to the program and the content must be assigned to that program. Content must also be published and have a current published version.

## 4. Main navigation

The sidebar displays pages allowed by the effective permissions on your account. Available pages can differ by role:

- **Overview**
- **Administration**
- **Content**
- **Programs**
- **Access**
- **Secure viewer**
- **Activity**
- **Audit**
- **Security events**
- **Analytics**
- **Reports**

Not every role sees every item. A direct request to a protected API is still checked by the server even if a link is hidden or a URL is known.

## 5. Overview

The Overview page welcomes you to your current organization workspace. If your permissions allow analytics, it also shows summary metrics such as content views, active users, and most-viewed content. Quick links lead to the content library, programs, and analytics.

An empty metric or page may mean there is no matching data yet, or that the current user does not have the corresponding permission.

## 6. Administration

The **Administration** page has organization-user and role/permission views, subject to permissions.

### 6.1 Organization users

Users with user-management permissions can:

1. Search the organization directory by name or email.
2. Select **Create User**.
3. Enter the user's name and email and select the appropriate role(s).
4. Submit the form.
5. Deliver the one-time displayed temporary password to the user through an approved secure channel. The temporary password is only shown once.
6. Activate or deactivate users when permitted.

User data is organization-scoped. An email address is unique within an organization, rather than globally across all organizations.

### 6.2 Roles and permissions

Authorized role managers can inspect the system role definitions and the permissions assigned to each role, as well as the available permission catalogue. The current screen presents this information for review; it is not a general-purpose role editor.

Role assignment and permission changes are privileged operations. Do not grant broader permissions to bypass a missing access grant or assignment. Managing content or assigning it to a Program does not itself authorize consumer access in the secure viewer. Administrator and Content Manager have a separate, audited preview workflow described in the viewer section below; it does not create consumer access.

## 7. Content library

The Content page is used to create content records, manage versions, and publish materials.

### 7.1 Create a content record

1. Select **Content** in the sidebar.
2. Select **Create content**.
3. Enter a title and, if useful, a description.
4. Submit. The record appears in the content list with its current lifecycle status.

The content record is metadata; a file is added as a version separately.

### 7.2 Search and inspect content

Use the content search field to search content metadata. Select a title to see its details and version history. Results are limited by the current user's organization and permissions. Content Consumers see only eligible assigned/granted published content.

### 7.3 Upload and publish a version

1. Select a content item.
2. Under **Upload a new version**, choose a supported file and optionally enter version notes.
3. Submit. The file is stored privately as a draft version.
4. Review the version row, then select **Publish** when authorized and ready.

Current upload formats include PDF, PowerPoint (`.pptx`), common image formats, and MP4 subject to server-side validation and size limits. The secure viewer currently renders supported PDFs and images. PowerPoint and video rendering are not available in the viewer.

Publishing a new version makes it the current published version. The previous current version is archived by the publication workflow. Published/archived version file identity and content metadata are protected from modification.

### 7.4 Archive

Users with the relevant permissions can archive a content item or eligible version. Archiving is a lifecycle action and preserves existing history; it is not a substitute for revoking a program grant or removing an assignment.

## 8. Programs and content assignments

Programs group content and define an access scope.

1. Open **Programs**.
2. Create a program if you have the required permission.
3. Select the program to see its status and assigned content.
4. Add content using the assignment control, or remove an assignment if authorized.
5. Activate or deactivate the program when permitted.

An assignment alone does **not** give a user access. A Content Consumer also needs an active Program Access Grant, and the program, content, and current content version must satisfy the active/published rules.

## 9. Program access grants

The **Access** page lets authorized administrators grant or revoke eligibility to use a program. Content Consumers can view their own grants when permitted.

### Grant access

1. Open **Access**.
2. Choose **Grant access**.
3. Select an active user with the Content Consumer role and an active program in the same organization.
4. Optionally set an expiration time if the form presents that field.
5. Submit and verify that the grant appears in the list.

### Revoke access

1. Find the grant in the access list.
2. Select **Revoke**.
3. Confirm the grant status changes to revoked.

Revocation is effective on subsequent protected access checks. Grant history is retained; revoking a grant does not delete prior access or activity records.

## 10. Secure viewer

The **Secure viewer** presents a rendered representation rather than a direct source-file download.

1. Select published content and an active program from the selectors.
2. Select **Open content**.
3. If authorized, the viewer renders the protected page with a watermark.
4. Use **Previous page** and **Next page** to navigate, and **Open full window** if desired.

The server checks the current user, organization, permission, active grant, active program, assignment, content publication state, and current published version for protected delivery. It rechecks access on delivery requests. A grant revocation or assignment/program/content lifecycle change should prevent subsequent protected delivery.

The viewer is a deterrent, not a guarantee against screenshots or saving a rendered representation. Do not treat watermarking as copy-proof DRM.

### Privileged content preview

Administrators and Content Managers with `CONTENT_PREVIEW`, `CONTENT_VIEW`, and
`VERSION_VIEW` can preview non-archived DRAFT or PUBLISHED versions from the
Content library:

1. Open **Content**, select an item, and locate an eligible version.
2. Select **Preview**. The protected viewer starts a separate preview session
   for that specific version; it does not require or create a Program grant or
   Content assignment.
3. Confirm the visible `PREVIEW` watermark and use the page controls to inspect
   the rendered representation.

The server checks the active account, current permissions, organization,
Content, version, and preview-session owner on every page request. Archiving
the Content/version or revoking preview permission prevents further delivery.
Each preview start is audited and viewer events are recorded with preview
context. Preview records are excluded from consumer access reports, analytics,
and access-burst signals. The source file is never returned; screenshots of
rendered pages cannot be prevented.

## 11. Activity, audit, and security events

These pages show different kinds of records and have different permissions:

- **Activity** — significant content interactions, such as opening a viewer or rendering a page. Users may be limited to their own activity; authorized roles may see organization activity.
- **Audit** — append-only records of supported administrative and lifecycle actions. The Management role does not receive organization-wide audit access by default.
- **Security events** — security-relevant events such as authentication outcomes and denied access. Organization views are permission-checked and tenant-scoped.

These records are read-only from the user interface. Do not interpret an event as proof of malicious intent; review the underlying context.

## 12. Analytics and reports

**Analytics** presents content view summaries, active-user counts, most-viewed content, and available time-series or content breakdowns. **Reports** provides the access report with the filters offered by the page.

The backend scopes results according to permissions and assignments. A Content Consumer's analytics/report scope is limited to authorized assigned content and their own access where applicable. Organization-level reports require the corresponding role permissions.

An empty result may be expected when no qualifying opens have occurred. Viewer page renders are not counted as additional content opens.

## 13. Scope-expansion capabilities and their current limitations

The React application includes the advisory Risk signals page, the Risk investigations workflow, and the Knowledge search page for permission-aware metadata retrieval.

### 13.1 Risk signals

Authorized operators with `SECURITY_EVENT_VIEW_ORGANIZATION` can open **Risk signals** from the navigation or call:

- `GET /api/v1/risk-signals/`
- `GET /api/v1/risk-signals/summary/`

The page displays the advisory signal type, severity, user reference, supporting counts, observed window, and explanation. Optional timezone-aware start/end filters and pagination are supported. `ACCESS_BURST` is based on at least four granted accesses across at least three distinct Content items within a rolling 24-hour window. `REPEATED_DENIALS` is based on at least three normal `ACCESS_DENIED` security events for Content within a rolling 24-hour window. Signals do not make access decisions. These thresholds and severities are current explainable rule behavior, not validated risk scores or formally approved policy definitions.

### 13.2 Risk investigations

Authorized operators can use **Risk investigations** to list and filter organization-scoped cases, open a detail view, create a case in a dialog, attach available authorized evidence, edit fields, and apply valid status transitions. The equivalent API endpoints are:

- `GET /api/v1/risk-investigations/`
- `GET /api/v1/risk-investigations/{investigation_id}/`
- `POST /api/v1/risk-investigations/`
- `PATCH /api/v1/risk-investigations/{investigation_id}/`

These operations require the existing organization-wide security-event-view permission. Valid status transitions are `OPEN` → `IN_REVIEW` or `DISMISSED`, and `IN_REVIEW` → `RESOLVED` or `DISMISSED`. Once resolved or dismissed, all details and evidence are read-only in both the interface and API; authorized users may still view the record. Creation and permitted pre-closure edits—including standalone notes and summary changes—are recorded through the existing audit system. Audit metadata records changed field names and evidence counts, not raw notes, summaries, or titles.

Record later findings in a separate investigation. A direct relationship between a follow-up investigation and the original is not currently supported.

Evidence references are limited to supported, existing Security Events and Audit Records. They are validated against the current organization and source-specific permission when attached, then checked again when displayed. A source that is no longer visible is omitted. Source records themselves are not changed by the investigation.

Use the manual workflow and API checks in [implementation-setup.md](implementation-setup.md). Automated tests pass for investigation API behavior and the frontend workflow; authenticated manual acceptance remains to be recorded.

### 13.3 Permission-aware retrieval endpoint

Users with both `CONTENT_SEARCH` and `CONTENT_VIEW` can open **Knowledge search** from the navigation or use:

- `POST /api/v1/assistant/query/`, with a JSON body containing a `question`.

Enter a short search phrase that may occur in a Content title or description. The page displays a notice below its heading explaining that this version searches metadata only; the search field and button are side by side on desktop. Each search checks current organization and content permissions and, for Content Consumers, published/current-version state, active Program assignment, and the user's active unexpired grant. The page displays only authorized metadata citations and a clear empty state if there are no authorized matches. Citations may show the source Content title, description, current version, and only those Program names visible to the current user.

This feature is not a completed generative RAG assistant:

- no model or external AI service is called;
- no document body extraction, persistent chunking/index, vector database, or semantic retrieval is used;
- the displayed retrieval status is fixed text, not an AI answer;
- citations point to content metadata and version information, not a supporting passage or page;
- each query is limited to 200 characters and returns at most five matches.

The Knowledge search page has no chat transcript and does not fabricate citations. It presents metadata matches in a results table within the search panel. Generative RAG and semantic document retrieval require a separate design and approval.

### 13.4 Privileged content preview

This operator workflow reuses the protected page renderer and returns only
watermarked page images. It is not a consumer grant, does not change
assignments, and does not provide unrestricted file download. Only
Administrator and Content Manager roles receive the explicit permission in
the standard role baseline.

## 14. Security and good practices

- Use only your own organization account and do not share credentials.
- Use synthetic or approved content in test environments.
- Do not attempt to bypass access by guessing identifiers or altering request data.
- Report unexpected access rather than repeatedly probing sensitive resources.
- Avoid copying private source files, session cookies, CSRF tokens, or sensitive content into logs or support messages.
- Sign out on shared devices.
- If a user, grant, assignment, or content state changes, rely on the server's next authorization check; do not trust a previously loaded page as proof that access remains current.

## 15. Troubleshooting

| Issue | What to check |
|---|---|
| Sign-in fails | Confirm organization slug, email, account status, and password with the administrator. If the page reports too many attempts, wait before retrying; no exact retry countdown is provided. |
| A sidebar item is missing | The signed-in account may not have the page's permissions. Ask the administrator to review the intended role; do not ask for blanket permission elevation. |
| Content is missing from search or viewer | Confirm organization, content status, current published version, program status, assignment, active grant, expiry, and user permissions. |
| Viewer reports unsupported content | Use a supported PDF or image for current rendering; PowerPoint/video rendering is not currently available. |
| Analytics is empty | Confirm successful content opens occurred and that the user has access to the relevant analytics scope. |
| Risk signals or investigations page is missing | The signed-in account needs `SECURITY_EVENT_VIEW_ORGANIZATION`; follow [implementation-setup.md](implementation-setup.md) for the authorized workflow. |
| API returns an authorization error | Confirm the endpoint permission and resource access requirements with an administrator. A successful sign-in alone does not grant resource access. |
| Local application does not load | Follow the startup and troubleshooting steps in [implementation-setup.md](implementation-setup.md). |

## 16. Current feature status

This manual describes the current application and its limitations. The scope-expansion backend additions are partial:

- Context-aware access policy enforcement is not implemented; current risk signals are advisory.
- Risk investigations have a React workflow, an audited workflow, and backend-enforced immutable terminal details; authenticated manual acceptance remains to be recorded.
- The assistant provides permission-aware metadata retrieval only; generative RAG is future work.

Refer to [implementation-status.md](implementation-status.md) for implementation and verification status, and to [api-specification.md](api-specification.md) for API conventions.
