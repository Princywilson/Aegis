import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Link,
  Navigate,
  NavLink,
  Route,
  Routes,
  useParams,
  useNavigate,
} from "react-router-dom";

import { ApiError, apiRequest } from "./api.js";

const navigation = [
  { label: "Overview", path: "/", permission: null },
  {
    label: "Administration",
    path: "/administration",
    permission: ["USER_VIEW", "ROLE_MANAGE", "CONFIGURATION_MANAGE"],
  },
  {
    label: "Content",
    path: "/content",
    permission: ["CONTENT_VIEW", "CONTENT_CREATE"],
  },
  {
    label: "Programs",
    path: "/programs",
    permission: ["PROGRAM_VIEW", "PROGRAM_CREATE"],
  },
  {
    label: "Access",
    path: "/access",
    permission: ["ACCESS_GRANT", "ACCESS_REVOKE", "PROFILE_VIEW_OWN"],
  },
  { label: "Secure viewer", path: "/viewer", permission: ["SECURE_DELIVERY"] },
  {
    label: "Activity",
    path: "/activity",
    permission: ["ACTIVITY_VIEW_OWN", "ACTIVITY_VIEW_ORGANIZATION"],
  },
  {
    label: "Audit",
    path: "/audit",
    permission: ["AUDIT_VIEW_ORGANIZATION"],
  },
  {
    label: "Security events",
    path: "/security-events",
    permission: ["SECURITY_EVENT_VIEW_ORGANIZATION"],
  },
  {
    label: "Risk signals",
    path: "/risk-signals",
    permission: ["SECURITY_EVENT_VIEW_ORGANIZATION"],
  },
  {
    label: "Investigations",
    path: "/risk-investigations",
    permission: ["SECURITY_EVENT_VIEW_ORGANIZATION"],
  },
  {
    label: "Knowledge search",
    path: "/assistant",
    allPermissions: ["CONTENT_SEARCH", "CONTENT_VIEW"],
  },
  {
    label: "Analytics",
    path: "/analytics",
    permission: ["ANALYTICS_VIEW_ASSIGNED", "ANALYTICS_VIEW_ORGANIZATION"],
  },
  {
    label: "Reports",
    path: "/reports",
    permission: ["REPORT_VIEW_ASSIGNED", "REPORT_VIEW_ORGANIZATION"],
  },
];

function canUse(user, permission) {
  return !permission || permission.some((code) => user.permissions.includes(code));
}

function ErrorMessage({ error }) {
  if (!error) return null;
  return (
    <p className="notice error" role="alert">
      {error}
    </p>
  );
}

function useResource(path, refreshKey = 0) {
  const [state, setState] = useState({ data: null, loading: true, error: "" });
  const reload = useCallback(async () => {
    if (!path) {
      setState({ data: [], loading: false, error: "" });
      return;
    }
    setState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const data = await apiRequest(path);
      setState({ data, loading: false, error: "" });
    } catch (error) {
      setState({
        data: null,
        loading: false,
        error: error.message || "Unable to load this information.",
      });
    }
  }, [path]);

  useEffect(() => {
    reload();
  }, [reload, refreshKey]);

  return { ...state, reload };
}

export function LoginPage({ onLogin }) {
  const [form, setForm] = useState({
    organization_slug: "",
    email: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await apiRequest("/auth/login/", { method: "POST", body: form });
      await onLogin();
    } catch (requestError) {
      setError(
        requestError.status === 429
          ? "Too many sign-in attempts. Please wait before trying again."
          : requestError.message,
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="brand-mark">A</div>
        <p className="eyebrow">Knowledge protection and delivery</p>
        <h1>Sign in to AEGIS</h1>
        <p className="muted">Use your organization account to continue.</p>
        <ErrorMessage error={error} />
        <form className="stack" onSubmit={submit}>
          <label>
            Organization slug
            <input
              autoComplete="organization"
              required
              value={form.organization_slug}
              onChange={(event) =>
                setForm({ ...form, organization_slug: event.target.value })
              }
            />
          </label>
          <label>
            Email
            <input
              type="email"
              autoComplete="username"
              required
              value={form.email}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
            />
          </label>
          <label>
            Password
            <input
              type="password"
              autoComplete="current-password"
              required
              value={form.password}
              onChange={(event) =>
                setForm({ ...form, password: event.target.value })
              }
            />
          </label>
          <button className="primary full-width" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="fine-print">Your session is protected by Django session and CSRF controls.</p>
      </section>
    </main>
  );
}

function App() {
  const [auth, setAuth] = useState({ loading: true, user: null, error: "" });
  const navigate = useNavigate();

  const loadCurrentUser = useCallback(async () => {
    try {
      const user = await apiRequest("/auth/me/");
      setAuth({ loading: false, user, error: "" });
      return user;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setAuth({ loading: false, user: null, error: "" });
      } else {
        setAuth({
          loading: false,
          user: null,
          error: error.message || "Unable to connect to AEGIS.",
        });
      }
      return null;
    }
  }, []);

  useEffect(() => {
    loadCurrentUser();
  }, [loadCurrentUser]);

  async function logout() {
    try {
      await apiRequest("/auth/logout/", { method: "POST" });
      setAuth({ loading: false, user: null, error: "" });
      navigate("/login");
    } catch (error) {
      setAuth((current) => ({ ...current, error: error.message }));
    }
  }

  if (auth.loading) {
    return <main className="loading-screen">Loading your secure workspace…</main>;
  }
  if (!auth.user) {
    return (
      <>
        <ErrorMessage error={auth.error} />
        <Routes>
          <Route path="/login" element={<LoginPage onLogin={loadCurrentUser} />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" to="/">
          <span className="brand-mark small">A</span>
          <span>
            <strong>AEGIS</strong>
            <small>Knowledge governance</small>
          </span>
        </Link>
        <div className="tenant-label">WORKSPACE</div>
        <div className="tenant-name">{auth.user.organization.name}</div>
        <nav className="nav-list" aria-label="Main navigation">
          {navigation.filter((item) => (
            canUse(auth.user, item.permission)
            && (!item.allPermissions || item.allPermissions.every((code) => auth.user.permissions.includes(code)))
          )).map((item) => (
            <NavLink
              end={item.path === "/"}
              key={item.path}
              to={item.path}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="avatar">{(auth.user.name || auth.user.email)[0].toUpperCase()}</div>
          <div className="user-info">
            <strong>{auth.user.name || auth.user.email}</strong>
            <small>{auth.user.roles.join(" · ") || "Member"}</small>
          </div>
          <button className="sidebar-signout" onClick={logout} aria-label="Sign out" title="Sign out">
            <svg aria-hidden="true" viewBox="0 0 24 24">
              <path d="M10 4H5v16h5M14 8l4 4-4 4M8 12h10" />
            </svg>
            <span>Sign out</span>
          </button>
        </div>
      </aside>
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard user={auth.user} />} />
          <Route path="/administration" element={<Administration user={auth.user} />} />
          <Route path="/administrator" element={<Administration user={auth.user} />} />
          <Route path="/content" element={<ContentPage user={auth.user} />} />
          <Route path="/programs" element={<ProgramsPage user={auth.user} />} />
          <Route path="/access" element={<AccessPage user={auth.user} />} />
          <Route path="/viewer" element={<ViewerPage />} />
          <Route
            path="/preview/:contentId/:versionId"
            element={<ViewerPage preview />}
          />
          <Route path="/activity" element={<AccountabilityPage endpoint="activities/" title="Activity" />} />
          <Route path="/audit" element={<AccountabilityPage endpoint="audits/" title="Audit records" />} />
          <Route path="/security-events" element={<AccountabilityPage endpoint="security-events/" title="Security events" />} />
          <Route path="/risk-signals" element={<RiskSignalsPage />} />
          <Route path="/risk-investigations" element={<RiskInvestigationsPage />} />
          <Route path="/risk-investigation" element={<RiskInvestigationsPage />} />
          <Route path="/assistant" element={<KnowledgeSearchPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function PageHeader({ eyebrow, title, description, children }) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {description && <p className="muted">{description}</p>}
      </div>
      {children}
    </header>
  );
}

function Dashboard({ user }) {
  const canViewAnalytics = canUse(user, [
    "ANALYTICS_VIEW_ASSIGNED",
    "ANALYTICS_VIEW_ORGANIZATION",
  ]);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (canViewAnalytics) {
      apiRequest("/analytics/content/")
        .then(setSummary)
        .catch((requestError) => setError(requestError.message));
    }
  }, [canViewAnalytics]);

  return (
    <>
      <PageHeader
        eyebrow="Workspace overview"
        title={`Welcome${user.name ? `, ${user.name.split(" ")[0]}` : ""}`}
        description={`${user.organization.name} · ${user.roles.join(" · ") || "Member"}`}
      />
      <ErrorMessage error={error} />
      {summary && (
        <div className="metric-grid">
          <Metric label="Content views" value={summary.total_views} />
          <Metric label="Active users" value={summary.active_users} />
          <Metric label="Top content" value={summary.most_viewed_content?.title || "—"} />
        </div>
      )}
      <section className="panel welcome-panel">
        <div className="welcome-copy">
          <p className="eyebrow">Secure by design</p>
          <h2>Knowledge, governed end to end.</h2>
          <p className="muted">
            Manage published content, control program access, and review
            organization activity from one tenant-scoped workspace.
          </p>
        </div>
        <div className="welcome-art" aria-hidden="true">
          <span className="orbit orbit-one" />
          <span className="orbit orbit-two" />
          <span className="shield">A</span>
        </div>
      </section>
      <div className="quick-links">
        <Link className="quick-link" to="/content">
          <span className="quick-icon">▤</span>
          <span><strong>Content library</strong><small>Manage versions and publication</small></span>
          <span className="arrow">→</span>
        </Link>
        <Link className="quick-link" to="/programs">
          <span className="quick-icon">▦</span>
          <span><strong>Programs</strong><small>Organize assigned content</small></span>
          <span className="arrow">→</span>
        </Link>
        <Link className="quick-link" to="/analytics">
          <span className="quick-icon">⌁</span>
          <span><strong>Analytics</strong><small>Review access and activity</small></span>
          <span className="arrow">→</span>
        </Link>
      </div>
    </>
  );
}

function Metric({ label, value }) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value ?? "—"}</strong>
    </article>
  );
}

function Modal({ title, onClose, children }) {
  useEffect(() => {
    function closeOnEscape(event) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        aria-labelledby="modal-title"
        aria-modal="true"
        className="modal-panel"
        role="dialog"
      >
        <div className="section-heading">
          <h2 id="modal-title">{title}</h2>
          <button className="icon-button modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}

function Administration({ user }) {
  const canViewUsers = user.permissions.includes("USER_VIEW");
  const canCreateUsers = user.permissions.includes("USER_CREATE");
  const canUpdateUsers = user.permissions.includes("USER_UPDATE");
  const canDeactivateUsers = user.permissions.includes("USER_DEACTIVATE");
  const canManageRoles = user.permissions.includes("ROLE_MANAGE");
  const [refreshKey, setRefreshKey] = useState(0);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState({ name: "", email: "" });
  const [selectedRoles, setSelectedRoles] = useState([]);
  const [temporaryPassword, setTemporaryPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [userPage, setUserPage] = useState(1);
  const [activeTab, setActiveTab] = useState(canViewUsers ? "users" : "roles");
  const [createOpen, setCreateOpen] = useState(false);
  const userParams = new URLSearchParams({ page_size: "20", page: String(userPage) });
  if (search.trim()) userParams.set("search", search.trim());
  const users = useResource(
    canViewUsers ? `/users/?${userParams}` : null,
    refreshKey,
  );
  const roles = useResource(canManageRoles ? "/roles/" : null, refreshKey);
  const permissions = useResource(
    canManageRoles ? "/permissions/" : null,
    refreshKey,
  );
  const userItems = users.data?.results || users.data || [];
  const roleItems = roles.data?.results || roles.data || [];
  const permissionItems = permissions.data?.results || permissions.data || [];

  async function createUser(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setTemporaryPassword("");
    try {
      const created = await apiRequest("/users/", {
        method: "POST",
        body: {
          ...form,
          role_ids: selectedRoles,
        },
      });
      setTemporaryPassword(created.temporary_password);
      setForm({ name: "", email: "" });
      setSelectedRoles([]);
      setRefreshKey((key) => key + 1);
      setCreateOpen(false);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function updateStatus(item) {
    const status = item.status === "active" ? "inactive" : "active";
    setBusy(true);
    setError("");
    try {
      await apiRequest(`/users/${item.id}/`, {
        method: "PATCH",
        body: { status },
      });
      setRefreshKey((key) => key + 1);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Administration"
        title="People and access"
        description="Manage organization users and review the seeded role and permission catalogue."
      />
      <ErrorMessage error={error || users.error || roles.error || permissions.error} />
      {temporaryPassword && (
        <section className="panel notice success" aria-live="polite">
          <h2>Temporary password — shown once</h2>
          <p>Share this password with the new user through an approved secure channel.</p>
          <code>{temporaryPassword}</code>
        </section>
      )}
      <div className="tab-list" role="tablist" aria-label="Administration sections">
        {canViewUsers && (
          <button
            aria-controls="organization-users-panel"
            aria-selected={activeTab === "users"}
            className={activeTab === "users" ? "tab-button active" : "tab-button"}
            id="organization-users-tab"
            onClick={() => setActiveTab("users")}
            role="tab"
          >
            Organization users
          </button>
        )}
        {canManageRoles && (
          <button
            aria-controls="roles-permissions-panel"
            aria-selected={activeTab === "roles"}
            className={activeTab === "roles" ? "tab-button active" : "tab-button"}
            id="roles-permissions-tab"
            onClick={() => setActiveTab("roles")}
            role="tab"
          >
            Roles &amp; Permissions
          </button>
        )}
      </div>
      {activeTab === "users" && canViewUsers ? (
        <section
          aria-labelledby="organization-users-tab"
          className="panel"
          id="organization-users-panel"
          role="tabpanel"
        >
          <div className="section-heading admin-users-heading">
            <div>
              <h2>Organization users</h2>
              <p className="muted">User data and filters are scoped to this organization.</p>
            </div>
            <div className="admin-toolbar">
              <label>
                Search
                <input
                  type="search"
                  value={search}
                  onChange={(event) => {
                    setSearch(event.target.value);
                    setUserPage(1);
                  }}
                  placeholder="Name or email"
                />
              </label>
              {canCreateUsers && (
                <button className="primary" onClick={() => setCreateOpen(true)}>
                  + Create User
                </button>
              )}
            </div>
          </div>
          {users.loading ? (
            <p className="muted">Loading users…</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Name</th><th>Email</th><th>Status</th><th>Roles</th><th>Action</th></tr>
                </thead>
                <tbody>
                  {userItems.map((item) => (
                    <tr key={item.id}>
                      <td>{item.name || "—"}</td>
                      <td>{item.email}</td>
                      <td>{item.status}</td>
                      <td>{item.roles.join(", ") || "—"}</td>
                      <td>
                        {canUpdateUsers && (
                          <button
                            className="secondary"
                            type="button"
                            disabled={busy || (item.status === "active" && !canDeactivateUsers)}
                            onClick={() => updateStatus(item)}
                          >
                            {item.status === "active" ? "Deactivate" : "Activate"}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {!userItems.length && (
                    <tr><td colSpan="5" className="empty-cell">No users found.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
          {users.data?.meta && (
            <div className="pagination">
              <span>
                Page {users.data.meta.page} of {Math.max(1, Math.ceil(users.data.meta.total / users.data.meta.page_size))}
                {" · "}{users.data.meta.total} users
              </span>
              <div>
                <button
                  className="secondary"
                  type="button"
                  disabled={users.loading || userPage <= 1}
                  onClick={() => setUserPage((page) => page - 1)}
                >
                  Previous
                </button>
                <button
                  className="secondary"
                  type="button"
                  disabled={users.loading || userPage * users.data.meta.page_size >= users.data.meta.total}
                  onClick={() => setUserPage((page) => page + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </section>
      ) : activeTab === "roles" && canManageRoles ? (
        <section
          aria-labelledby="roles-permissions-tab"
          className="panel"
          id="roles-permissions-panel"
          role="tabpanel"
        >
          <h2>Roles &amp; Permissions</h2>
          {roles.loading ? <p className="muted">Loading roles…</p> : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Role name</th><th>Permissions</th></tr></thead>
                <tbody>
                  {roleItems.map((role) => (
                    <tr key={role.id}>
                      <td><strong>{role.name}</strong><br /><code>{role.code}</code></td>
                      <td>
                        {(role.permissions || []).map((permission) => permission.name).join(", ") || "No permissions"}
                      </td>
                    </tr>
                  ))}
                  {!roleItems.length && <tr><td colSpan="2" className="empty-cell">No roles found.</td></tr>}
                </tbody>
              </table>
            </div>
          )}
          <details className="permission-catalogue">
            <summary>Permission catalogue · all available system permissions ({permissionItems.length})</summary>
            <p className="muted">
              This is the reference list of capabilities available to roles. The table above shows the permissions actually assigned to each role.
            </p>
            <ul className="permission-list">
              {permissionItems.map((permission) => (
                <li key={permission.code}>
                  <code>{permission.code}</code> — {permission.name}
                  {permission.description && <span className="muted"> · {permission.description}</span>}
                </li>
              ))}
            </ul>
          </details>
        </section>
      ) : (
        <section className="panel">
          <h2>Administration section unavailable</h2>
          <p className="muted">Your role does not include permission to view this section.</p>
        </section>
      )}
      {createOpen && canCreateUsers && (
        <Modal title="Create user" onClose={() => setCreateOpen(false)}>
          <form className="stack" onSubmit={createUser}>
            <label>
              Full name
              <input
                required
                maxLength="301"
                value={form.name}
                onChange={(event) => setForm({ ...form, name: event.target.value })}
              />
            </label>
            <label>
              Email
              <input
                required
                type="email"
                value={form.email}
                onChange={(event) => setForm({ ...form, email: event.target.value })}
              />
            </label>
            {canManageRoles && (
              <div className="role-field">
                <span className="field-label">Roles</span>
                <details className="multi-select-dropdown">
                  <summary>
                    {selectedRoles.length
                      ? `${selectedRoles.length} role${selectedRoles.length === 1 ? "" : "s"} selected`
                      : "Select roles"}
                  </summary>
                  <div className="dropdown-options">
                    {roleItems.map((role) => (
                      <label key={role.id} className="checkbox-label">
                        <input
                          checked={selectedRoles.includes(role.id)}
                          onChange={(event) => setSelectedRoles((current) =>
                            event.target.checked
                              ? [...current, role.id]
                              : current.filter((id) => id !== role.id))}
                          type="checkbox"
                        />
                        {role.name}
                      </label>
                    ))}
                  </div>
                </details>
                <span className="fine-print">Select one or more roles.</span>
              </div>
            )}
            <div className="modal-actions">
              <button className="secondary" type="button" onClick={() => setCreateOpen(false)}>Cancel</button>
              <button className="primary" type="submit" disabled={busy}>
                {busy ? "Creating…" : "Create user"}
              </button>
            </div>
          </form>
        </Modal>
      )}
      <p className="muted">Organization profile/configuration editing is not specified by the current API contract.</p>
    </>
  );
}

function ContentPage({ user }) {
  const navigate = useNavigate();
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedId, setSelectedId] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [searchValue, setSearchValue] = useState("");
  const [form, setForm] = useState({ title: "", description: "" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const contentPath = useMemo(() => {
    const params = new URLSearchParams({ page_size: "100" });
    if (search) params.set("search", search);
    return `/content/?${params}`;
  }, [search]);
  const content = useResource(contentPath, refreshKey);
  const selected = (content.data?.results || content.data || []).find(
    (item) => item.id === selectedId,
  );
  const versions = useResource(
    selectedId ? `/content/${selectedId}/versions/` : "/content/",
    refreshKey,
  );
  const canCreate = user.permissions.includes("CONTENT_CREATE");
  const canCreateVersion = user.permissions.includes("VERSION_CREATE");
  const canPublish = user.permissions.includes("VERSION_PUBLISH");
  const canPreview = user.permissions.includes("CONTENT_PREVIEW")
    && user.permissions.includes("VERSION_VIEW");

  async function createContent(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      const created = await apiRequest("/content/", { method: "POST", body: form });
      setForm({ title: "", description: "" });
      setSelectedId(created.id);
      setRefreshKey((value) => value + 1);
      setMessage("Content created.");
      setCreateOpen(false);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function uploadVersion(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const payload = new FormData(formElement);
    setError("");
    try {
      await apiRequest(`/content/${selectedId}/versions/`, {
        method: "POST",
        body: payload,
      });
      formElement.reset();
      setRefreshKey((value) => value + 1);
      setMessage("Version uploaded as a private draft.");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function changeVersion(versionId, action) {
    setError("");
    try {
      await apiRequest(`/content/${selectedId}/versions/${versionId}/${action}/`, {
        method: "POST",
        body: {},
      });
      setRefreshKey((value) => value + 1);
      setMessage(action === "publish" ? "Version published." : "Version archived.");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function archiveContent(id) {
    setError("");
    try {
      await apiRequest(`/content/${id}/archive/`, { method: "POST", body: {} });
      setRefreshKey((value) => value + 1);
      setMessage("Content archived.");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  const contentItems = content.data?.results || content.data || [];
  const versionItems = versions.data?.results || versions.data || [];
  return (
    <>
      <PageHeader
        eyebrow="Content"
        title="Content library"
        description="Create content, manage private versions, and publish approved materials."
      />
      <ErrorMessage error={error || content.error || (selectedId ? versions.error : "")} />
      {message && <p className="notice success" role="status">{message}</p>}
      <section className="panel">
        <div className="section-heading">
          <h2>All content</h2>
          <div className="content-toolbar">
            <form className="inline-form" onSubmit={(event) => { event.preventDefault(); setSearch(searchValue.trim()); }}>
              <input aria-label="Search content" placeholder="Search content…" value={searchValue} onChange={(event) => setSearchValue(event.target.value)} />
              <button className="secondary">Search</button>
            </form>
            {canCreate && <button className="primary" onClick={() => setCreateOpen(true)}>+ Create content</button>}
          </div>
        </div>
        {content.loading ? <p className="muted">Loading content…</p> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Title</th><th>Status</th><th>Description</th><th /></tr></thead>
              <tbody>
                {contentItems.map((item) => (
                  <tr key={item.id} className={selectedId === item.id ? "selected-row" : ""}>
                    <td><button className="text-button" onClick={() => setSelectedId(item.id)}>{item.title}</button></td>
                    <td><StatusBadge value={item.status} /></td>
                    <td>{item.description || "—"}</td>
                    <td>{user.permissions.includes("CONTENT_ARCHIVE") && item.status !== "ARCHIVED" && <button className="text-button danger-text" onClick={() => archiveContent(item.id)}>Archive</button>}</td>
                  </tr>
                ))}
                {!contentItems.length && <tr><td colSpan="4" className="empty-cell">No content found.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </section>
      {selected && (
        <section className="panel">
          <div className="section-heading"><div><p className="eyebrow">Content details</p><h2>{selected.title}</h2></div><StatusBadge value={selected.status} /></div>
          <p className="muted">{selected.description || "No description provided."}</p>
          <h3>Version history</h3>
          <ErrorMessage error={versions.error} />
          <div className="table-wrap">
            <table>
              <thead><tr><th>Version</th><th>Status</th><th>Notes</th><th>Created</th><th /></tr></thead>
              <tbody>{versionItems.map((version) => (
                <tr key={version.id}>
                  <td>v{version.version_number}</td><td><StatusBadge value={version.status} /></td><td>{version.version_notes || "—"}</td><td>{formatDate(version.created_at)}</td>
                  <td>
                    {canPreview && selected.status !== "ARCHIVED"
                      && ["DRAFT", "PUBLISHED"].includes(version.status) && (
                        <button
                          className="text-button"
                          onClick={() => navigate(`/preview/${selectedId}/${version.id}`)}
                        >
                          Preview
                        </button>
                      )}
                    {version.status === "DRAFT" && canPublish && (
                      <button
                        className="text-button"
                        onClick={() => changeVersion(version.id, "publish")}
                      >
                        Publish
                      </button>
                    )}
                    {version.status !== "PUBLISHED"
                      && version.status !== "ARCHIVED"
                      && user.permissions.includes("VERSION_ARCHIVE") && (
                        <button
                          className="text-button danger-text"
                          onClick={() => changeVersion(version.id, "archive")}
                        >
                          Archive version
                        </button>
                      )}
                  </td>
                </tr>
              ))}{!versionItems.length && <tr><td colSpan="5" className="empty-cell">No versions uploaded.</td></tr>}</tbody>
            </table>
          </div>
          {canCreateVersion && selected.status !== "ARCHIVED" && (
            <form className="upload-form" onSubmit={uploadVersion}>
              <h3>Upload a new version</h3>
              <label>File<input name="file" type="file" required accept=".pdf,.pptx,.jpg,.jpeg,.png,.webp,.mp4" /></label>
              <label>Version notes<input name="version_notes" maxLength="500" /></label>
              <button className="primary">Upload draft</button>
            </form>
          )}
        </section>
      )}
      {createOpen && canCreate && (
        <Modal title="Create content" onClose={() => setCreateOpen(false)}>
          <form className="stack" onSubmit={createContent}>
            <label>Title<input required value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label>
            <label>Description<textarea rows="3" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
            <div className="modal-actions">
              <button className="secondary" type="button" onClick={() => setCreateOpen(false)}>Cancel</button>
              <button className="primary">Create content</button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}

function ProgramsPage({ user }) {
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedId, setSelectedId] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({ name: "", description: "" });
  const programs = useResource("/programs/?page_size=100", refreshKey);
  const programItems = programs.data?.results || programs.data || [];
  const assignments = useResource(
    selectedId ? `/programs/${selectedId}/content/` : "/programs/",
    refreshKey,
  );
  const contents = useResource("/content/?page_size=100");
  const contentItems = contents.data?.results || contents.data || [];
  const currentProgram = programItems.find((program) => program.id === selectedId);

  async function submitProgram(event) {
    event.preventDefault();
    try {
      await apiRequest("/programs/", { method: "POST", body: form });
      setForm({ name: "", description: "" });
      setRefreshKey((value) => value + 1);
      setMessage("Program created.");
      setError("");
      setCreateOpen(false);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function updateProgram(action) {
    try {
      await apiRequest(`/programs/${selectedId}/${action}/`, { method: "POST", body: {} });
      setRefreshKey((value) => value + 1);
      setError("");
      setMessage(`Program ${action === "activate" ? "activated" : "deactivated"}.`);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function addAssignment(event) {
    event.preventDefault();
    const contentId = new FormData(event.currentTarget).get("content_id");
    try {
      await apiRequest(`/programs/${selectedId}/content/`, {
        method: "POST",
        body: { content_id: contentId },
      });
      setRefreshKey((value) => value + 1);
      setError("");
      setMessage("Content assigned. Assignment alone does not grant user access.");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function removeAssignment(contentId) {
    try {
      await apiRequest(`/programs/${selectedId}/content/${contentId}/`, { method: "DELETE" });
      setRefreshKey((value) => value + 1);
      setMessage("Assignment removed.");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  const assigned = assignments.data?.results || assignments.data || [];
  return (
    <>
      <PageHeader eyebrow="Programs" title="Program management" description="Group content and control when it is available." />
      <ErrorMessage error={error || programs.error || (selectedId ? assignments.error : "")} />
      {message && <p className="notice success" role="status">{message}</p>}
      <div className="split-layout">
        <section className="panel">
          <div className="section-heading">
            <h2>Programs</h2>
            {user.permissions.includes("PROGRAM_CREATE") && (
              <button className="primary" onClick={() => setCreateOpen(true)}>+ Create program</button>
            )}
          </div>
          {programs.loading ? <p className="muted">Loading programs…</p> : (
            <div className="program-list">{programItems.map((program) => (
              <button className={`program-item ${selectedId === program.id ? "chosen" : ""}`} key={program.id} onClick={() => setSelectedId(program.id)}>
                <span><strong>{program.name}</strong><small>{program.description || "No description"}</small></span><StatusBadge value={program.status} />
              </button>
            ))}{!programItems.length && <p className="muted">No programs found.</p>}</div>
          )}
        </section>
        {currentProgram && (
          <section className="panel">
            <div className="section-heading"><div><p className="eyebrow">Program details</p><h2>{currentProgram.name}</h2></div>
              {user.permissions.includes("PROGRAM_UPDATE") && <button className="secondary" onClick={() => updateProgram(currentProgram.status === "ACTIVE" ? "deactivate" : "activate")}>{currentProgram.status === "ACTIVE" ? "Deactivate" : "Activate"}</button>}
            </div>
            <p className="muted">{currentProgram.description || "No description provided."}</p>
            <h3>Assigned content</h3>
            <div className="table-wrap"><table><thead><tr><th>Content</th><th>Status</th><th /></tr></thead><tbody>
              {assigned.map((item) => <tr key={item.content_id}><td>{item.content_title}</td><td><StatusBadge value={item.content_status} /></td><td>{user.permissions.includes("ASSIGNMENT_MANAGE") && <button className="text-button danger-text" onClick={() => removeAssignment(item.content_id)}>Remove</button>}</td></tr>)}
              {!assigned.length && <tr key="no-assignments"><td colSpan="3" className="empty-cell">No content assigned.</td></tr>}
            </tbody></table></div>
            {user.permissions.includes("ASSIGNMENT_MANAGE") && (
              <form className="inline-form assign-form" onSubmit={addAssignment}>
                <select name="content_id" required defaultValue=""><option value="" disabled>Select content to assign</option>{contentItems.filter((item) => item.status !== "ARCHIVED" && !assigned.some((a) => a.content_id === item.id)).map((item) => <option value={item.id} key={item.id}>{item.title}</option>)}</select>
                <button className="primary">Assign</button>
              </form>
            )}
          </section>
        )}
      </div>
      {createOpen && user.permissions.includes("PROGRAM_CREATE") && (
        <Modal title="Create a program" onClose={() => setCreateOpen(false)}>
          <form className="stack" onSubmit={submitProgram}>
            <label>Name<input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
            <label>Description<textarea rows="3" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
            <div className="modal-actions">
              <button className="secondary" type="button" onClick={() => setCreateOpen(false)}>Cancel</button>
              <button className="primary">Create program</button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}

function AccessPage({ user }) {
  const [refreshKey, setRefreshKey] = useState(0);
  const [grantPage, setGrantPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);
  const [targetId, setTargetId] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const canViewUsers = user.permissions.includes("USER_VIEW");
  const canGrantOthers = user.permissions.includes("ACCESS_GRANT");
  const grantPath = canGrantOthers
    ? `/program-access-grants/?page=${grantPage}&page_size=50`
    : `/users/${user.id}/access/`;
  const grants = useResource(grantPath, refreshKey);
  const programs = useResource("/programs/?page_size=100");
  const eligibleUsers = useResource(
    canViewUsers
      ? "/users/?role=content_consumer&status=active&page_size=100"
      : null,
  );
  const programItems = programs.data?.results || programs.data || [];
  const eligibleUserItems = eligibleUsers.data?.results || eligibleUsers.data || [];

  async function grantAccess(event) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    const body = {
      user_id: targetId.trim(),
      program_id: values.get("program_id"),
      ...(values.get("expires_at")
        ? { expires_at: new Date(values.get("expires_at")).toISOString() }
        : {}),
    };
    try {
      await apiRequest("/program-access-grants/", { method: "POST", body });
      setGrantPage(1);
      setRefreshKey((value) => value + 1);
      setMessage("Program access granted.");
      setError("");
      setCreateOpen(false);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function revoke(grantId) {
    try {
      await apiRequest(`/program-access-grants/${grantId}/revoke/`, { method: "POST", body: {} });
      setRefreshKey((value) => value + 1);
      setMessage("Program access revoked.");
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  const grantItems = grants.data?.results || grants.data || [];
  return (
    <>
      <PageHeader eyebrow="Access control" title="Program access grants" description="Grant or revoke a user's eligibility to access a program." />
      <ErrorMessage error={error || grants.error || programs.error || eligibleUsers.error} />
      {message && <p className="notice success" role="status">{message}</p>}
      {canGrantOthers && (
        <section className="panel">
          <div className="section-heading">
            <div>
              <h2>Program access</h2>
              <p className="muted">Organization-scoped grants for users and their assigned programs.</p>
            </div>
            <button className="primary" onClick={() => setCreateOpen(true)}>+ Grant access</button>
          </div>
          {canViewUsers && !eligibleUsers.loading && eligibleUserItems.length === 0 && (
            <p className="fine-print" role="status">
              No eligible users are available. Only active users assigned the Content Consumer role can receive a program grant.
              Create a user with that role from <Link to="/administrator">Administration</Link>, or ask an organization role manager to assign it to an existing user.
            </p>
          )}
        </section>
      )}
      <section className="panel">
        <div className="section-heading"><h2>{canGrantOthers ? "Organization program access" : "My program grants"}</h2></div>
        {grants.loading ? <p className="muted">Loading grants…</p> : (
          <div className="table-wrap"><table><thead><tr><th>User</th><th>Program</th><th>Status</th><th>Granted</th><th>Expires</th><th /></tr></thead><tbody>
            {grantItems.map((grant) => <tr key={grant.id}><td>{grant.user_name || "Unnamed user"}</td><td>{grant.program_name || "Unnamed program"}</td><td><StatusBadge value={grant.status} /></td><td>{formatDate(grant.granted_at)}</td><td>{grant.expires_at ? formatDate(grant.expires_at) : "Never"}</td><td>{grant.status === "ACTIVE" && user.permissions.includes("ACCESS_REVOKE") && <button className="text-button danger-text" onClick={() => revoke(grant.id)}>Revoke</button>}</td></tr>)}
            {!grantItems.length && <tr><td colSpan="6" className="empty-cell">No access grants found.</td></tr>}
          </tbody></table></div>
        )}
        {grants.data?.meta && (
          <div className="pagination">
            <span>{grants.data.meta.total} grants</span>
            <div>
              <button className="secondary" disabled={grantPage <= 1} onClick={() => setGrantPage((page) => page - 1)}>Previous</button>
              <span>Page {grants.data.meta.page}</span>
              <button className="secondary" disabled={grantPage * grants.data.meta.page_size >= grants.data.meta.total} onClick={() => setGrantPage((page) => page + 1)}>Next</button>
            </div>
          </div>
        )}
      </section>
      {createOpen && canGrantOthers && (
        <Modal title="Grant program access" onClose={() => setCreateOpen(false)}>
          <form className="stack" onSubmit={grantAccess}>
            {canViewUsers ? (
              <label>Content Consumer
                <select required value={targetId} onChange={(event) => setTargetId(event.target.value)}>
                  <option value="" disabled>Select a user</option>
                  {eligibleUserItems.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name ? `${item.name} — ${item.email}` : item.email}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <label>User ID<input required value={targetId} onChange={(event) => setTargetId(event.target.value)} placeholder="Content Consumer UUID" /></label>
            )}
            <label>Program<select name="program_id" required defaultValue=""><option value="" disabled>Select a program</option>{programItems.filter((item) => item.status === "ACTIVE").map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
            <label>Expires at (optional)<input name="expires_at" type="datetime-local" /></label>
            <div className="modal-actions">
              <button className="secondary" type="button" onClick={() => setCreateOpen(false)}>Cancel</button>
              <button className="primary" disabled={eligibleUsers.loading || (canViewUsers && eligibleUserItems.length === 0)}>Grant access</button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}

function ViewerPage({ preview = false }) {
  const { contentId: previewContentId = "", versionId: previewVersionId = "" } = useParams();
  const [contentId, setContentId] = useState(previewContentId);
  const [programId, setProgramId] = useState("");
  const [access, setAccess] = useState(null);
  const [fullWindow, setFullWindow] = useState(false);
  const [page, setPage] = useState(1);
  const [pageCount, setPageCount] = useState(1);
  const [imageUrl, setImageUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const content = useResource(
    preview ? `/content/${previewContentId}/` : "/content/?page_size=100",
  );
  const programs = useResource(preview ? null : "/programs/?page_size=100");
  const contentItems = preview
    ? (content.data ? [content.data] : [])
    : (content.data?.results || content.data || []);
  const programItems = programs.data?.results || programs.data || [];

  useEffect(() => () => {
    if (imageUrl) URL.revokeObjectURL(imageUrl);
  }, [imageUrl]);

  useEffect(() => {
    if (!preview || !previewContentId || !previewVersionId) return undefined;
    let active = true;
    setBusy(true);
    setError("");
    apiRequest(`/content/${previewContentId}/preview/`, {
      method: "POST",
      body: { version_id: previewVersionId },
    }).then((result) => {
      if (active) {
        setAccess(result);
        setPage(1);
      }
    }).catch((requestError) => {
      if (active) setError(requestError.message);
    }).finally(() => {
      if (active) setBusy(false);
    });
    return () => {
      active = false;
    };
  }, [preview, previewContentId, previewVersionId]);

  async function startAccess(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setAccess(null);
    try {
      const result = await apiRequest(`/content/${contentId}/access/`, {
        method: "POST",
        body: { program_id: programId },
      });
      setAccess(result);
      setPage(1);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    let active = true;
    let nextUrl = "";
    async function loadPage() {
      if (!access) return;
      setBusy(true);
      setError("");
      try {
        const response = await apiRequest(
          preview
            ? `/content/${access.content_id}/preview/${access.access_id}/delivery/?page=${page}`
            : `/content/${access.content_id}/access/${access.access_id}/delivery/?page=${page}`,
          { expect: "response" },
        );
        const blob = await response.blob();
        nextUrl = URL.createObjectURL(blob);
        if (active) {
          setImageUrl(nextUrl);
          setPageCount(Number(response.headers.get("X-Page-Count")) || 1);
        } else {
          URL.revokeObjectURL(nextUrl);
        }
      } catch (requestError) {
        if (active) {
          setError(
            requestError.status === 415
              ? "This file format is not yet supported in the protected viewer. PowerPoint and video rendering are planned for future development; use PDF or image content for now."
              : requestError.message,
          );
        }
      } finally {
        if (active) setBusy(false);
      }
    }
    loadPage();
    return () => {
      active = false;
      if (nextUrl) URL.revokeObjectURL(nextUrl);
    };
  }, [access, page, preview]);

  return (
    <>
      <PageHeader
        eyebrow={preview ? "Privileged preview" : "Secure delivery"}
        title={preview ? "Content preview" : "Content viewer"}
        description={preview
          ? "This preview is permission-checked on every page and does not grant consumer access."
          : "Rendered content is delivered only after the server validates current access."}
      />
      <ErrorMessage error={error || content.error || programs.error} />
      {preview && (
        <p className="notice">
          PREVIEW — this protected preview does not create a consumer grant or assignment.
        </p>
      )}
      {!preview && <section className="panel">
        <form className="form-grid" onSubmit={startAccess}>
          <label>Published content<select required value={contentId} onChange={(event) => setContentId(event.target.value)}><option value="" disabled>Select content</option>{contentItems.filter((item) => item.status === "PUBLISHED").map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
          <label>Active program<select required value={programId} onChange={(event) => setProgramId(event.target.value)}><option value="" disabled>Select program</option>{programItems.filter((item) => item.status === "ACTIVE").map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <div><button className="primary" disabled={busy || !contentId || !programId}>{busy && !access ? "Checking access…" : "Open content"}</button></div>
        </form>
      </section>}
      {access && (
        <section className={`panel viewer-panel${fullWindow ? " viewer-fullscreen" : ""}`}>
          <div className="section-heading">
            <div className="viewer-heading">
              {fullWindow && <Link className="secondary" to="/content">Back to content library</Link>}
              <div>
                <p className="eyebrow">Protected representation</p>
                <h2>{contentItems.find((item) => item.id === access.content_id)?.title || "Content"}</h2>
              </div>
            </div>
            <div className="viewer-heading-actions">
              <span className="page-counter">Page {page} of {pageCount}</span>
              <button className="secondary" onClick={() => setFullWindow((value) => !value)}>
                {fullWindow ? "Exit full window" : "Open full window"}
              </button>
            </div>
          </div>
          <div className="viewer-canvas">{busy ? <p className="muted">Rendering protected page…</p> : imageUrl ? <img src={imageUrl} alt={`Watermarked content page ${page}`} /> : <p className="muted">Page preview is unavailable.</p>}</div>
          <div className="viewer-controls"><button className="secondary" disabled={page <= 1 || busy} onClick={() => setPage((value) => value - 1)}>Previous page</button><button className="secondary" disabled={page >= pageCount || busy} onClick={() => setPage((value) => value + 1)}>Next page</button></div>
          <p className="fine-print">This rendered preview is watermarked. Screenshots and saving a rendered representation cannot be prevented.</p>
        </section>
      )}
    </>
  );
}

function AccountabilityPage({ endpoint, title }) {
  const [refreshKey, setRefreshKey] = useState(0);
  const resource = useResource(`/${endpoint}?page_size=50`, refreshKey);
  const items = resource.data?.results || resource.data || [];
  const headers = endpoint === "audits/"
    ? ["Action", "Resource", "User", "Occurred"]
    : endpoint === "security-events/"
      ? ["Event", "Severity", "User", "Resource", "Occurred"]
      : ["Event", "User", "Content", "Program", "Occurred"];
  return (
    <>
      <PageHeader eyebrow="Accountability" title={title} description="Read-only, organization-scoped records from trusted backend workflows.">
        <button className="secondary" onClick={() => setRefreshKey((value) => value + 1)}>Refresh</button>
      </PageHeader>
      <ErrorMessage error={resource.error} />
      <section className="panel"><div className="table-wrap"><table><thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead><tbody>
        {items.map((item) => endpoint === "audits/" ? (
          <tr key={item.id}><td>{item.action}</td><td>{item.resource_name || item.resource_type.replaceAll("_", " ")}</td><td>{item.actor_user_name || "System"}</td><td>{formatDate(item.occurred_at)}</td></tr>
        ) : endpoint === "security-events/" ? (
          <tr key={item.id}><td>{item.event_type}</td><td><StatusBadge value={item.severity} /></td><td>{item.user_name || "System"}</td><td>{item.resource_name || item.resource_type?.replaceAll("_", " ") || "—"}</td><td>{formatDate(item.occurred_at)}</td></tr>
        ) : (
          <tr key={item.id}><td>{item.event_type}</td><td>{item.user_name || "System"}</td><td>{item.content_title || "—"}</td><td>{item.program_name || "—"}</td><td>{formatDate(item.occurred_at)}</td></tr>
        ))}
        {!resource.loading && !items.length && <tr><td colSpan={headers.length} className="empty-cell">No records found.</td></tr>}
      </tbody></table></div></section>
    </>
  );
}

function AnalyticsPage() {
  const resource = useResource("/analytics/content/");
  const data = resource.data;
  return (
    <>
      <PageHeader eyebrow="Insights" title="Content analytics" description="Successful content opens are counted once; page renders do not add views." />
      <ErrorMessage error={resource.error} />
      {data && <>
        <div className="metric-grid">
          <Metric label="Total views" value={data.total_views} />
          <Metric label="Active users" value={data.active_users} />
          <Metric label="Most viewed" value={data.most_viewed_content?.title || "—"} />
        </div>
        <div className="split-layout analytics-tables">
          <section className="panel"><h2>Daily access frequency</h2><DataTable columns={["Date", "Views"]} rows={data.access_frequency.map((item) => [item.date, item.views])} /></section>
          <section className="panel"><h2>Version usage</h2><DataTable columns={["Content", "Version", "Views"]} rows={data.version_usage.map((item) => [item.content_title, `v${item.version_number}`, item.views])} /></section>
        </div>
        <section className="panel"><h2>Recent activity</h2><DataTable columns={["Event", "User", "Content", "Program", "Occurred"]} rows={data.recent_activity.map((item) => [item.event_type, item.user_name || "System", item.content_title || "—", item.program_name || "—", formatDate(item.occurred_at)])} /></section>
      </>}
      {resource.loading && <p className="muted">Loading analytics…</p>}
    </>
  );
}

function ReportsPage() {
  const [page, setPage] = useState(1);
  const resource = useResource(`/reports/access/?page=${page}&page_size=50`, page);
  const records = resource.data?.results || resource.data || [];
  return (
    <>
      <PageHeader eyebrow="Insights" title="Content access report" description="A record is created for each successful content open." />
      <ErrorMessage error={resource.error} />
      <section className="panel"><div className="table-wrap"><table><thead><tr><th>Content</th><th>Version</th><th>Program</th><th>User</th><th>Accessed</th></tr></thead><tbody>
        {records.map((record) => <tr key={record.id}><td>{record.content_title}</td><td>v{record.version_number}</td><td>{record.program_name || "—"}</td><td>{record.user_name || "Unknown user"}</td><td>{formatDate(record.accessed_at)}</td></tr>)}
        {!resource.loading && !records.length && <tr><td colSpan="5" className="empty-cell">No access records found.</td></tr>}
      </tbody></table></div>
      {resource.data?.meta && <div className="pagination"><span>{resource.data.meta.total} records</span><div><button className="secondary" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>Previous</button><span>Page {page}</span><button className="secondary" disabled={page * resource.data.meta.page_size >= resource.data.meta.total} onClick={() => setPage((value) => value + 1)}>Next</button></div></div>}
      </section>
    </>
  );
}

function RiskSignalsPage() {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ from: "", to: "" });
  const [appliedFilters, setAppliedFilters] = useState({ from: "", to: "" });
  const [validationError, setValidationError] = useState("");
  const query = new URLSearchParams({ page: String(page), page_size: "20" });
  if (appliedFilters.from) {
    query.set("from", new Date(appliedFilters.from).toISOString());
  }
  if (appliedFilters.to) {
    query.set("to", new Date(appliedFilters.to).toISOString());
  }
  const resource = useResource(`/risk-signals/?${query.toString()}`);
  const signals = resource.data?.results || [];

  function submitFilters(event) {
    event.preventDefault();
    setValidationError("");
    const from = filters.from ? new Date(filters.from) : null;
    const to = filters.to ? new Date(filters.to) : null;
    if (
      (from && Number.isNaN(from.getTime()))
      || (to && Number.isNaN(to.getTime()))
      || (from && to && from > to)
    ) {
      setValidationError("Enter a valid time range with the start no later than the end.");
      return;
    }
    setPage(1);
    setAppliedFilters(filters);
  }

  return (
    <>
      <PageHeader
        eyebrow="Security review"
        title="Advisory risk signals"
        description="Explainable activity indicators for review. These signals do not change access decisions."
      />
      <ErrorMessage error={validationError || resource.error} />
      <section className="panel">
        <form className="content-toolbar filter-toolbar" onSubmit={submitFilters}>
          <label>
            From
            <input
              type="datetime-local"
              value={filters.from}
              onChange={(event) => setFilters({ ...filters, from: event.target.value })}
            />
          </label>
          <label>
            To
            <input
              type="datetime-local"
              value={filters.to}
              onChange={(event) => setFilters({ ...filters, to: event.target.value })}
            />
          </label>
          <button className="primary" type="submit">Apply time filter</button>
        </form>
      </section>
      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>Signals</h2>
            <p className="muted">Thresholds reflect current rule behavior and are not validated risk scores.</p>
          </div>
          <span className="muted">{resource.data?.meta?.total ?? 0} signals</span>
        </div>
        {resource.loading ? (
          <p className="muted">Loading advisory signals…</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Signal</th>
                  <th>Severity</th>
                  <th>User reference</th>
                  <th>Events</th>
                  <th>Content items</th>
                  <th>Observed window</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {signals.map((signal) => (
                  <tr key={`${signal.type}-${signal.user_id}`}>
                    <td>{signal.type.replaceAll("_", " ")}</td>
                    <td><StatusBadge value={signal.severity} /></td>
                    <td>{signal.user_id}</td>
                    <td>{signal.event_count}</td>
                    <td>{signal.content_count ?? "—"}</td>
                    <td>{formatDate(signal.first_seen)} – {formatDate(signal.last_seen)}</td>
                    <td>{signal.reason}</td>
                  </tr>
                ))}
                {!signals.length && (
                  <tr><td colSpan="7" className="empty-cell">No advisory signals in this time range.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
        {resource.data?.meta && (
          <div className="pagination">
            <span>Page {page} of {Math.max(1, Math.ceil(resource.data.meta.total / resource.data.meta.page_size))}</span>
            <div>
              <button className="secondary" disabled={page <= 1 || resource.loading} onClick={() => setPage((value) => value - 1)}>Previous</button>
              <button className="secondary" disabled={page * resource.data.meta.page_size >= resource.data.meta.total || resource.loading} onClick={() => setPage((value) => value + 1)}>Next</button>
            </div>
          </div>
        )}
      </section>
    </>
  );
}

function RiskInvestigationsPage() {
  const [page, setPage] = useState(1);
  const [refreshKey, setRefreshKey] = useState(0);
  const [filters, setFilters] = useState({ status: "", severity: "" });
  const [appliedFilters, setAppliedFilters] = useState(filters);
  const [selectedId, setSelectedId] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [createBusy, setCreateBusy] = useState(false);
  const [createError, setCreateError] = useState("");
  const [createMessage, setCreateMessage] = useState("");
  const [editBusy, setEditBusy] = useState(false);
  const [editError, setEditError] = useState("");
  const [editMessage, setEditMessage] = useState("");
  const [evidenceChanged, setEvidenceChanged] = useState(false);
  const [createForm, setCreateForm] = useState({
    title: "",
    summary: "",
    notes: "",
    severity: "MEDIUM",
    evidenceIds: [],
  });
  const [editForm, setEditForm] = useState({
    title: "",
    summary: "",
    notes: "",
    severity: "MEDIUM",
    evidenceIds: [],
  });
  const listQuery = new URLSearchParams({ page: String(page), page_size: "20" });
  if (appliedFilters.status) listQuery.set("status", appliedFilters.status);
  if (appliedFilters.severity) listQuery.set("severity", appliedFilters.severity);
  const listResource = useResource(
    `/risk-investigations/?${listQuery.toString()}`,
    refreshKey,
  );
  const investigation = useResource(
    selectedId ? `/risk-investigations/${selectedId}/` : null,
    refreshKey,
  );
  const evidenceResource = useResource(
    "/security-events/?event_type=ACCESS_DENIED&page=1&page_size=100",
  );
  const investigations = listResource.data?.results || [];
  const availableEvents = evidenceResource.data?.results || [];
  const selected = investigation.data;
  const isClosed = selected?.status === "RESOLVED" || selected?.status === "DISMISSED";
  const evidenceOptions = new Map(
    [...availableEvents, ...(selected?.evidence || [])].map((item) => [item.id, item]),
  );

  useEffect(() => {
    if (!selected) return;
    setEditForm({
      title: selected.title || "",
      summary: selected.summary || "",
      notes: selected.notes || "",
      severity: selected.severity || "MEDIUM",
      evidenceIds: (selected.evidence || []).map((item) => item.id),
    });
    setEvidenceChanged(false);
    setEditError("");
    setEditMessage("");
  }, [selected]);

  function applyFilters(event) {
    event.preventDefault();
    setPage(1);
    setAppliedFilters(filters);
  }

  async function createInvestigation(event) {
    event.preventDefault();
    setCreateBusy(true);
    setCreateError("");
    setCreateMessage("");
    try {
      const result = await apiRequest("/risk-investigations/", {
        method: "POST",
        body: {
          title: createForm.title,
          summary: createForm.summary,
          notes: createForm.notes,
          severity: createForm.severity,
          evidence: createForm.evidenceIds.map((id) => ({ type: "security_event", id })),
        },
      });
      setSelectedId(result.id);
      setCreateForm({
        title: "",
        summary: "",
        notes: "",
        severity: "MEDIUM",
        evidenceIds: [],
      });
      setCreateMessage("Investigation created.");
      setShowCreate(false);
      setRefreshKey((value) => value + 1);
    } catch (error) {
      setCreateError(error.message || "Unable to create the investigation.");
    } finally {
      setCreateBusy(false);
    }
  }

  async function saveInvestigation(event) {
    event.preventDefault();
    if (!selectedId || isClosed) return;
    setEditBusy(true);
    setEditError("");
    setEditMessage("");
    try {
      const body = {
        title: editForm.title,
        summary: editForm.summary,
        notes: editForm.notes,
        severity: editForm.severity,
      };
      if (evidenceChanged) {
        body.evidence = editForm.evidenceIds.map((id) => {
          const source = evidenceOptions.get(id);
          return {
            type: source?.type || "security_event",
            id,
          };
        });
      }
      await apiRequest(`/risk-investigations/${selectedId}/`, {
        method: "PATCH",
        body,
      });
      setEditMessage("Investigation changes saved.");
      setRefreshKey((value) => value + 1);
    } catch (error) {
      setEditError(error.message || "Unable to save the investigation.");
    } finally {
      setEditBusy(false);
    }
  }

  async function transitionInvestigation(status) {
    if (!selectedId) return;
    setEditBusy(true);
    setEditError("");
    setEditMessage("");
    try {
      await apiRequest(`/risk-investigations/${selectedId}/`, {
        method: "PATCH",
        body: { status },
      });
      setEditMessage(`Investigation moved to ${status.replaceAll("_", " ")}.`);
      setRefreshKey((value) => value + 1);
    } catch (error) {
      setEditError(error.message || "Unable to update the investigation status.");
    } finally {
      setEditBusy(false);
    }
  }

  const transitions = {
    OPEN: ["IN_REVIEW", "DISMISSED"],
    IN_REVIEW: ["RESOLVED", "DISMISSED"],
    RESOLVED: [],
    DISMISSED: [],
  };

  return (
    <>
      <PageHeader
        eyebrow="Security review"
        title="Risk investigations"
        description="Review organization-scoped findings, attach authorized evidence, and record audited updates."
      >
        <button className="primary" onClick={() => setShowCreate((value) => !value)}>
          {showCreate ? "Close form" : "+ New investigation"}
        </button>
      </PageHeader>
      {createMessage && <p className="notice success" role="status">{createMessage}</p>}
      {showCreate && (
        <Modal title="Create investigation" onClose={() => setShowCreate(false)}>
          <ErrorMessage error={createError} />
          <form className="stack" onSubmit={createInvestigation}>
            <label>Title<input required maxLength={255} value={createForm.title} onChange={(event) => setCreateForm({ ...createForm, title: event.target.value })} /></label>
            <label>Summary<textarea value={createForm.summary} onChange={(event) => setCreateForm({ ...createForm, summary: event.target.value })} /></label>
            <label>Notes<textarea value={createForm.notes} onChange={(event) => setCreateForm({ ...createForm, notes: event.target.value })} /></label>
            <label>Severity<select value={createForm.severity} onChange={(event) => setCreateForm({ ...createForm, severity: event.target.value })}><option value="LOW">Low</option><option value="MEDIUM">Medium</option><option value="HIGH">High</option></select></label>
            <label>Authorized denial-event evidence
              <select multiple value={createForm.evidenceIds} onChange={(event) => setCreateForm({ ...createForm, evidenceIds: Array.from(event.target.selectedOptions, (option) => option.value) })}>
                {availableEvents.map((item) => <option key={item.id} value={item.id}>{item.event_type} · {formatDate(item.occurred_at)} · {item.id}</option>)}
              </select>
            </label>
            {evidenceResource.error && <ErrorMessage error={evidenceResource.error} />}
            {!evidenceResource.loading && !availableEvents.length && <p className="muted">No authorized denied-content events are available to attach.</p>}
            <div className="modal-actions">
              <button className="secondary" type="button" onClick={() => setShowCreate(false)}>Cancel</button>
              <button className="primary" disabled={createBusy || evidenceResource.loading}>{createBusy ? "Creating…" : "Create investigation"}</button>
            </div>
          </form>
        </Modal>
      )}
      <section className="panel">
        <form className="content-toolbar filter-toolbar" onSubmit={applyFilters}>
          <label>Status<select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}><option value="">All statuses</option><option value="OPEN">Open</option><option value="IN_REVIEW">In review</option><option value="RESOLVED">Resolved</option><option value="DISMISSED">Dismissed</option></select></label>
          <label>Severity<select value={filters.severity} onChange={(event) => setFilters({ ...filters, severity: event.target.value })}><option value="">All severities</option><option value="LOW">Low</option><option value="MEDIUM">Medium</option><option value="HIGH">High</option></select></label>
          <button className="primary" type="submit">Apply filters</button>
        </form>
        <ErrorMessage error={listResource.error} />
        {listResource.loading ? <p className="muted">Loading investigations…</p> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Title</th><th>Status</th><th>Severity</th><th>Created</th></tr></thead>
              <tbody>
                {investigations.map((item) => (
                  <tr key={item.id} aria-selected={selectedId === item.id}>
                    <td><button className="text-button" onClick={() => setSelectedId(item.id)}>{item.title}</button></td>
                    <td><StatusBadge value={item.status} /></td>
                    <td><StatusBadge value={item.severity} /></td>
                    <td>{formatDate(item.created_at)}</td>
                  </tr>
                ))}
                {!investigations.length && <tr><td colSpan="4" className="empty-cell">No investigations found.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
        {listResource.data?.meta && (
          <div className="pagination">
            <span>{listResource.data.meta.total} investigations · page {page}</span>
            <div>
              <button className="secondary" disabled={page <= 1 || listResource.loading} onClick={() => setPage((value) => value - 1)}>Previous</button>
              <button className="secondary" disabled={page * listResource.data.meta.page_size >= listResource.data.meta.total || listResource.loading} onClick={() => setPage((value) => value + 1)}>Next</button>
            </div>
          </div>
        )}
      </section>
      {selectedId && (
        <section className="panel">
          {investigation.error && <ErrorMessage error={investigation.error} />}
          {investigation.loading ? <p className="muted">Loading investigation…</p> : selected && (
            <>
              <div className="section-heading">
                <h2>Investigation details</h2>
                <StatusBadge value={selected.status} />
              </div>
              <ErrorMessage error={editError} />
              {editMessage && <p className="notice success" role="status">{editMessage}</p>}
              {isClosed && (
                <p className="muted" role="note">
                  This investigation is closed and read-only. Record later findings in a separate investigation.
                </p>
              )}
              <form className="stack" onSubmit={saveInvestigation}>
                <label>Title<input required maxLength={255} disabled={isClosed || editBusy} value={editForm.title} onChange={(event) => setEditForm({ ...editForm, title: event.target.value })} /></label>
                <label>Summary<textarea disabled={isClosed || editBusy} value={editForm.summary} onChange={(event) => setEditForm({ ...editForm, summary: event.target.value })} /></label>
                <label>Notes<textarea disabled={isClosed || editBusy} value={editForm.notes} onChange={(event) => setEditForm({ ...editForm, notes: event.target.value })} /></label>
                <label>Severity<select disabled={isClosed || editBusy} value={editForm.severity} onChange={(event) => setEditForm({ ...editForm, severity: event.target.value })}><option value="LOW">Low</option><option value="MEDIUM">Medium</option><option value="HIGH">High</option></select></label>
                <label>Authorized evidence
                  <select multiple disabled={isClosed || editBusy} value={editForm.evidenceIds} onChange={(event) => {
                    setEvidenceChanged(true);
                    setEditForm({ ...editForm, evidenceIds: Array.from(event.target.selectedOptions, (option) => option.value) });
                  }}>
                    {Array.from(evidenceOptions.values()).map((item) => <option key={item.id} value={item.id}>{item.event_type || item.action} · {formatDate(item.occurred_at)} · {item.id}</option>)}
                  </select>
                </label>
                <div className="content-toolbar">
                  {!isClosed && (
                    <button className="primary" disabled={editBusy}>{editBusy ? "Saving…" : "Save changes"}</button>
                  )}
                  {transitions[selected.status]?.map((status) => (
                    <button key={status} className="secondary" type="button" disabled={editBusy} onClick={() => transitionInvestigation(status)}>{status.replaceAll("_", " ")}</button>
                  ))}
                </div>
              </form>
            </>
          )}
        </section>
      )}
    </>
  );
}

function KnowledgeSearchPage() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function searchKnowledge(event) {
    event.preventDefault();
    const normalizedQuestion = question.trim();
    if (!normalizedQuestion) {
      setError("Enter a search question.");
      setResult(null);
      return;
    }
    if (normalizedQuestion.length > 200) {
      setError("Search questions must be no more than 200 characters.");
      setResult(null);
      return;
    }

    setBusy(true);
    setError("");
    setResult(null);
    try {
      const response = await apiRequest("/assistant/query/", {
        method: "POST",
        body: { question: normalizedQuestion },
      });
      setResult(response);
    } catch (requestError) {
      setError(requestError.message || "Unable to search authorized content.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Permission-aware retrieval"
        title="Knowledge search"
        description="Find currently authorized content by searching its title and description."
      />
      <p className="notice notice-info" role="note">
        <span className="notice-icon" aria-hidden="true">!</span>
        <span>
          This version searches content metadata only. It does not search document
          contents, generate answers, or call an AI service.
        </span>
      </p>
      <section className="panel">
        <form className="content-toolbar filter-toolbar knowledge-search-toolbar" onSubmit={searchKnowledge}>
          <label htmlFor="knowledge-search-question">
            <span>Search authorized content</span>
            <input
              id="knowledge-search-question"
              maxLength={200}
              value={question}
              onChange={(event) => {
                setQuestion(event.target.value);
                setError("");
                setResult(null);
              }}
              placeholder="Enter title or description terms"
            />
          </label>
          <button className="primary" disabled={busy}>
            {busy ? "Searching…" : "Search authorized content"}
          </button>
        </form>
        <p className="muted">Up to 200 characters. Results are reauthorized for each search.</p>
        <ErrorMessage error={error} />
        {busy && <p className="muted" role="status">Searching authorized content…</p>}
        {result && (
          <div className="retrieval-results" aria-live="polite">
            <div className="section-heading">
              <h2>Matching content</h2>
              <span className="muted">
                {result.citations?.length || 0} result{result.citations?.length === 1 ? "" : "s"}
              </span>
            </div>
            <p>{result.answer}</p>
            {!result.citations?.length ? (
              <p className="empty-cell">No authorized content metadata matched this search.</p>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Content</th><th>Version</th><th>Authorized programs</th><th>Description</th></tr></thead>
                  <tbody>
                    {result.citations.map((citation) => (
                      <tr key={citation.content_id}>
                        <td><strong>{citation.title}</strong><br /><span className="muted">{citation.content_id}</span></td>
                        <td>{citation.version_number == null ? "—" : `Version ${citation.version_number}`}</td>
                        <td>{citation.program_names?.join(", ") || "—"}</td>
                        <td>{citation.source_summary}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </section>
    </>
  );
}

function DataTable({ columns, rows }) {
  return <div className="table-wrap"><table><thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={index}>{row.map((value, cell) => <td key={cell}>{value}</td>)}</tr>)}{!rows.length && <tr><td className="empty-cell" colSpan={columns.length}>No data available.</td></tr>}</tbody></table></div>;
}

function StatusBadge({ value }) {
  const normalized = (value || "unknown").toLowerCase();
  return <span className={`status-badge status-${normalized}`}>{value || "Unknown"}</span>;
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export default App;
