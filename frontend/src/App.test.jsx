import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import App, { LoginPage } from "./App.jsx";
import { apiRequest } from "./api.js";

vi.mock("./api.js", () => ({
  ApiError: class ApiError extends Error {},
  apiRequest: vi.fn(),
}));

describe("login page", () => {
  it("submits organization-scoped credentials and proceeds after success", async () => {
    const user = userEvent.setup();
    const onLogin = vi.fn();
    apiRequest.mockResolvedValueOnce({ user: { id: "user-1" } });

    render(
      <MemoryRouter>
        <LoginPage onLogin={onLogin} />
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText("Organization slug"), "north");
    await user.type(screen.getByLabelText("Email"), "person@example.test");
    await user.type(screen.getByLabelText("Password"), "correct-horse");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(apiRequest).toHaveBeenCalledWith("/auth/login/", {
      method: "POST",
      body: {
        organization_slug: "north",
        email: "person@example.test",
        password: "correct-horse",
      },
    });
    expect(onLogin).toHaveBeenCalledOnce();
  });

  it("shows backend authentication errors", async () => {
    const user = userEvent.setup();
    apiRequest.mockRejectedValueOnce(new Error("Authentication failed."));
    render(
      <MemoryRouter>
        <LoginPage onLogin={vi.fn()} />
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText("Organization slug"), "north");
    await user.type(screen.getByLabelText("Email"), "person@example.test");
    await user.type(screen.getByLabelText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Authentication failed.");
  });

  it("gives non-specific wait-and-retry guidance when sign-in is rate limited", async () => {
    const user = userEvent.setup();
    apiRequest.mockRejectedValueOnce(
      Object.assign(new Error("Authentication failed."), { status: 429 }),
    );
    render(
      <MemoryRouter>
        <LoginPage onLogin={vi.fn()} />
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText("Organization slug"), "north");
    await user.type(screen.getByLabelText("Email"), "person@example.test");
    await user.type(screen.getByLabelText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Too many sign-in attempts. Please wait before trying again.",
    );
  });
});

describe("administration and access workflows", () => {
  it("shows the authenticated user in the organization directory on /administrator", async () => {
    const currentUser = {
      id: "admin-1",
      name: "Avery Admin",
      email: "avery@example.test",
      organization: { id: "org-1", name: "North" },
      roles: ["Administrator"],
      permissions: ["USER_VIEW", "USER_CREATE", "ROLE_MANAGE"],
    };
    apiRequest.mockImplementation((path) => {
      if (path === "/auth/me/") return Promise.resolve(currentUser);
      if (path.startsWith("/users/?")) {
        return Promise.resolve({
          results: [{
            id: currentUser.id,
            name: currentUser.name,
            email: currentUser.email,
            status: "active",
            roles: ["Administrator"],
          }],
          meta: { page: 1, page_size: 20, total: 1 },
        });
      }
      if (path === "/roles/" || path === "/permissions/") return Promise.resolve([]);
      return Promise.resolve([]);
    });

    render(
      <MemoryRouter initialEntries={["/administrator"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Organization users" })).toBeInTheDocument();
    expect(await screen.findByText("avery@example.test")).toBeInTheDocument();
  });

  it("grants program access to a selected active Content Consumer", async () => {
    const user = userEvent.setup();
    apiRequest.mockImplementation((path, options = {}) => {
      if (path === "/auth/me/") {
        return Promise.resolve({
          id: "admin-1",
          name: "Avery Admin",
          email: "avery@example.test",
          organization: { id: "org-1", name: "North" },
          roles: ["Administrator"],
          permissions: ["USER_VIEW", "ACCESS_GRANT", "ACCESS_REVOKE", "PROFILE_VIEW_OWN"],
        });
      }
      if (path.startsWith("/users/?role=content_consumer")) {
        return Promise.resolve({
          results: [{
            id: "consumer-1",
            name: "Casey Consumer",
            email: "casey@example.test",
            status: "active",
            roles: ["Content Consumer"],
          }],
          meta: { page: 1, page_size: 100, total: 1 },
        });
      }
      if (path === "/programs/?page_size=100") {
        return Promise.resolve([{
          id: "program-1",
          name: "Reference Program",
          status: "ACTIVE",
        }]);
      }
      if (path === "/program-access-grants/" && options.method === "POST") {
        return Promise.resolve({ id: "grant-1" });
      }
      if (path.startsWith("/program-access-grants/?")) {
        return Promise.resolve({
          results: [{
            id: "grant-1",
            user_name: "Casey Consumer",
            program_name: "Reference Program",
            status: "ACTIVE",
            granted_at: "2026-10-14T10:00:00Z",
            expires_at: null,
          }],
          meta: { page: 1, page_size: 50, total: 1 },
        });
      }
      return Promise.resolve([]);
    });

    render(
      <MemoryRouter initialEntries={["/access"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Casey Consumer")).toBeInTheDocument();
    expect(await screen.findByText("Reference Program")).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: "+ Grant access" }));
    const consumerSelect = await screen.findByLabelText("Content Consumer");
    expect(consumerSelect).toHaveValue("");
    await screen.findByRole("option", { name: /Casey Consumer/ });
    await user.selectOptions(consumerSelect, "consumer-1");
    await user.selectOptions(screen.getByLabelText("Program"), "program-1");
    await user.click(screen.getByRole("button", { name: "Grant access" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Program access granted.");
    expect(apiRequest).toHaveBeenCalledWith("/program-access-grants/", {
      method: "POST",
      body: { user_id: "consumer-1", program_id: "program-1" },
    });
  });

  it("explains why users without the Content Consumer role are not selectable", async () => {
    apiRequest.mockImplementation((path) => {
      if (path === "/auth/me/") {
        return Promise.resolve({
          id: "admin-1",
          name: "Avery Admin",
          email: "avery@example.test",
          organization: { id: "org-1", name: "North" },
          roles: ["Administrator"],
          permissions: ["USER_VIEW", "ACCESS_GRANT", "PROFILE_VIEW_OWN"],
        });
      }
      if (path.startsWith("/users/?role=content_consumer")) {
        return Promise.resolve({ results: [], meta: { page: 1, page_size: 100, total: 0 } });
      }
      if (path === "/programs/?page_size=100") return Promise.resolve([]);
      if (path.startsWith("/program-access-grants/?")) {
        return Promise.resolve({ results: [], meta: { page: 1, page_size: 50, total: 0 } });
      }
      return Promise.resolve([]);
    });

    render(
      <MemoryRouter initialEntries={["/access"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Only active users assigned the Content Consumer role can receive a program grant.",
    );
    expect(
      screen.getAllByRole("link", { name: "Administration" }).some((link) =>
        link.getAttribute("href") === "/administrator",
      ),
    ).toBe(true);
  });
});

describe("advisory risk review", () => {
  it("shows paginated advisory signals to a user with security-event permission", async () => {
    const user = userEvent.setup();
    const currentUser = {
      id: "admin-1",
      name: "Avery Admin",
      email: "avery@example.test",
      organization: { id: "org-1", name: "North" },
      roles: ["Administrator"],
      permissions: ["SECURITY_EVENT_VIEW_ORGANIZATION"],
    };
    apiRequest.mockImplementation((path) => {
      if (path === "/auth/me/") return Promise.resolve(currentUser);
      if (path === "/risk-signals/?page=1&page_size=20") {
        return Promise.resolve({
          results: [{
            type: "REPEATED_DENIALS",
            severity: "MEDIUM",
            user_id: "user-reference",
            event_count: 3,
            first_seen: "2026-10-19T10:00:00Z",
            last_seen: "2026-10-19T10:10:00Z",
            reason: "Multiple denied content-access attempts were recorded within 24 hours.",
          }],
          meta: { page: 1, page_size: 20, total: 21 },
        });
      }
      if (path === "/risk-signals/?page=2&page_size=20") {
        return Promise.resolve({
          results: [],
          meta: { page: 2, page_size: 20, total: 21 },
        });
      }
      return Promise.resolve([]);
    });

    render(
      <MemoryRouter initialEntries={["/risk-signals"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByRole("heading", { name: "Advisory risk signals" })).toBeInTheDocument();
    expect(await screen.findByText("REPEATED DENIALS")).toBeInTheDocument();
    expect(screen.getByText(/do not change access decisions/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Next" }));
    await screen.findByText("No advisory signals in this time range.");
    expect(apiRequest).toHaveBeenCalledWith("/risk-signals/?page=2&page_size=20");
  });
});

describe("risk investigation workflow", () => {
  const currentUser = {
    id: "admin-1",
    name: "Avery Admin",
    email: "avery@example.test",
    organization: { id: "org-1", name: "North" },
    roles: ["Administrator"],
    permissions: ["SECURITY_EVENT_VIEW_ORGANIZATION"],
  };
  const investigationId = "investigation-1";
  const eventId = "event-1";
  const investigation = {
    id: investigationId,
    title: "Review denied access",
    summary: "Several attempts were denied.",
    notes: "",
    status: "OPEN",
    severity: "MEDIUM",
    evidence: [],
    created_at: "2026-10-19T10:00:00Z",
  };

  it("applies status and severity filters and paginates the investigation list", async () => {
    const user = userEvent.setup();
    const requestedPaths = [];
    apiRequest.mockImplementation((path) => {
      requestedPaths.push(path);
      if (path === "/auth/me/") return Promise.resolve(currentUser);
      if (path.startsWith("/risk-investigations/?")) {
        return Promise.resolve({
          results: [],
          meta: { page: Number(new URLSearchParams(path.split("?")[1]).get("page")), page_size: 20, total: 21 },
        });
      }
      if (path === "/security-events/?event_type=ACCESS_DENIED&page=1&page_size=100") {
        return Promise.resolve({
          results: [{
            id: eventId,
            event_type: "ACCESS_DENIED",
            occurred_at: "2026-10-19T10:00:00Z",
          }],
          meta: { page: 1, page_size: 100, total: 1 },
        });
      }
      return Promise.resolve([]);
    });

    render(
      <MemoryRouter initialEntries={["/risk-investigations"]}>
        <App />
      </MemoryRouter>,
    );

    await screen.findByText("No investigations found.");
    await user.selectOptions(screen.getByLabelText("Status"), "OPEN");
    await user.selectOptions(screen.getByLabelText("Severity"), "HIGH");
    await user.click(screen.getByRole("button", { name: "Apply filters" }));
    await waitFor(() => {
      expect(requestedPaths).toContain(
        "/risk-investigations/?page=1&page_size=20&status=OPEN&severity=HIGH",
      );
    });
    await user.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => {
      expect(requestedPaths).toContain(
        "/risk-investigations/?page=2&page_size=20&status=OPEN&severity=HIGH",
      );
    });
  });

  it("loads details, saves audited fields through the API, and transitions status", async () => {
    const user = userEvent.setup();
    apiRequest.mockImplementation((path, options = {}) => {
      if (path === "/auth/me/") return Promise.resolve(currentUser);
      if (path.startsWith("/risk-investigations/?")) {
        return Promise.resolve({
          results: [investigation],
          meta: { page: 1, page_size: 20, total: 1 },
        });
      }
      if (path === "/security-events/?event_type=ACCESS_DENIED&page=1&page_size=100") {
        return Promise.resolve({
          results: [{
            id: eventId,
            event_type: "ACCESS_DENIED",
            occurred_at: "2026-10-19T10:00:00Z",
          }],
          meta: { page: 1, page_size: 100, total: 1 },
        });
      }
      if (path === `/risk-investigations/${investigationId}/` && options.method === "PATCH") {
        return Promise.resolve({ ...investigation, ...options.body });
      }
      if (path === `/risk-investigations/${investigationId}/`) {
        return Promise.resolve(investigation);
      }
      return Promise.resolve([]);
    });

    render(
      <MemoryRouter initialEntries={["/risk-investigations"]}>
        <App />
      </MemoryRouter>,
    );

    await user.click(await screen.findByRole("button", { name: "Review denied access" }));
    const notes = await screen.findByLabelText("Notes");
    await user.type(notes, "Reviewed evidence.");
    await user.click(screen.getByRole("button", { name: "Save changes" }));
    expect(apiRequest).toHaveBeenCalledWith(
      `/risk-investigations/${investigationId}/`,
      expect.objectContaining({
        method: "PATCH",
        body: expect.objectContaining({
          notes: "Reviewed evidence.",
        }),
      }),
    );
    const notesUpdate = apiRequest.mock.calls.find(
      ([path, options]) =>
        path === `/risk-investigations/${investigationId}/`
        && options?.method === "PATCH"
        && options?.body?.notes === "Reviewed evidence.",
    );
    expect(notesUpdate[1].body).not.toHaveProperty("evidence");
    await screen.findByText("Investigation changes saved.");
    await user.selectOptions(
      screen.getByLabelText("Authorized evidence"),
      eventId,
    );
    await user.click(screen.getByRole("button", { name: "Save changes" }));
    expect(apiRequest).toHaveBeenCalledWith(
      `/risk-investigations/${investigationId}/`,
      expect.objectContaining({
        method: "PATCH",
        body: expect.objectContaining({
          evidence: [{ type: "security_event", id: eventId }],
        }),
      }),
    );
    await user.click(screen.getByRole("button", { name: "IN REVIEW" }));
    expect(apiRequest).toHaveBeenCalledWith(
      `/risk-investigations/${investigationId}/`,
      { method: "PATCH", body: { status: "IN_REVIEW" } },
    );
  });

  it("shows resolved investigations as read-only", async () => {
    const user = userEvent.setup();
    const closedCase = {
      ...investigation,
      id: "closed-investigation",
      title: "Resolved case",
      status: "RESOLVED",
    };
    apiRequest.mockImplementation((path, options = {}) => {
      if (path === "/auth/me/") return Promise.resolve(currentUser);
      if (path.startsWith("/risk-investigations/?")) {
        return Promise.resolve({
          results: [closedCase],
          meta: { page: 1, page_size: 20, total: 1 },
        });
      }
      if (path === "/security-events/?event_type=ACCESS_DENIED&page=1&page_size=100") {
        return Promise.resolve([]);
      }
      if (path === `/risk-investigations/${closedCase.id}/` && !options.method) {
        return Promise.resolve(closedCase);
      }
      return Promise.resolve([]);
    });

    render(
      <MemoryRouter initialEntries={["/risk-investigations"]}>
        <App />
      </MemoryRouter>,
    );

    await user.click(await screen.findByRole("button", { name: "Resolved case" }));
    expect(await screen.findByRole("note")).toHaveTextContent("closed and read-only");
    const detailPanel = screen.getByRole("heading", { name: "Investigation details" }).closest("section");
    expect(within(detailPanel).getByLabelText("Title")).toBeDisabled();
    expect(within(detailPanel).getByLabelText("Summary")).toBeDisabled();
    expect(within(detailPanel).getByLabelText("Notes")).toBeDisabled();
    expect(within(detailPanel).getByLabelText("Severity")).toBeDisabled();
    expect(within(detailPanel).getByLabelText("Authorized evidence")).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Save changes" })).not.toBeInTheDocument();
    expect(apiRequest).not.toHaveBeenCalledWith(
      `/risk-investigations/${closedCase.id}/`,
      expect.objectContaining({ method: "PATCH" }),
    );
  });

  it("creates an investigation with a selected authorized security-event reference", async () => {
    const user = userEvent.setup();
    apiRequest.mockImplementation((path, options = {}) => {
      if (path === "/auth/me/") return Promise.resolve(currentUser);
      if (path.startsWith("/risk-investigations/?")) {
        return Promise.resolve({ results: [], meta: { page: 1, page_size: 20, total: 0 } });
      }
      if (path === "/security-events/?event_type=ACCESS_DENIED&page=1&page_size=100") {
        return Promise.resolve({
          results: [{
            id: eventId,
            event_type: "ACCESS_DENIED",
            occurred_at: "2026-10-19T10:00:00Z",
          }],
          meta: { page: 1, page_size: 100, total: 1 },
        });
      }
      if (path === "/risk-investigations/" && options.method === "POST") {
        return Promise.resolve({ ...investigation, id: investigationId, ...options.body });
      }
      if (path === `/risk-investigations/${investigationId}/`) {
        return Promise.resolve({ ...investigation, id: investigationId });
      }
      return Promise.resolve([]);
    });

    render(
      <MemoryRouter initialEntries={["/risk-investigations"]}>
        <App />
      </MemoryRouter>,
    );

    await user.click(await screen.findByRole("button", { name: "+ New investigation" }));
    expect(screen.getByRole("dialog", { name: "Create investigation" })).toBeInTheDocument();
    await user.type(screen.getByLabelText("Title"), "Denied access review");
    await user.selectOptions(
      screen.getByLabelText("Authorized denial-event evidence"),
      eventId,
    );
    await user.click(screen.getByRole("button", { name: "Create investigation" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Investigation created.");
    expect(apiRequest).toHaveBeenCalledWith(
      "/risk-investigations/",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          title: "Denied access review",
          evidence: [{ type: "security_event", id: eventId }],
        }),
      }),
    );
  });

  it("shows API validation failures without reporting a successful creation", async () => {
    const user = userEvent.setup();
    apiRequest.mockImplementation((path, options = {}) => {
      if (path === "/auth/me/") return Promise.resolve(currentUser);
      if (path.startsWith("/risk-investigations/?")) {
        return Promise.resolve({ results: [], meta: { page: 1, page_size: 20, total: 0 } });
      }
      if (path === "/security-events/?event_type=ACCESS_DENIED&page=1&page_size=100") {
        return Promise.resolve({ results: [], meta: { page: 1, page_size: 100, total: 0 } });
      }
      if (path === "/risk-investigations/" && options.method === "POST") {
        return Promise.reject(new Error("Investigation title is invalid."));
      }
      return Promise.resolve([]);
    });

    render(
      <MemoryRouter initialEntries={["/risk-investigations"]}>
        <App />
      </MemoryRouter>,
    );

    await user.click(await screen.findByRole("button", { name: "+ New investigation" }));
    await user.type(screen.getByLabelText("Title"), "Invalid case");
    await user.click(screen.getByRole("button", { name: "Create investigation" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Investigation title is invalid.",
    );
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});

describe("permission-aware metadata search", () => {
  const consumer = {
    id: "consumer-1",
    name: "Casey Consumer",
    email: "casey@example.test",
    organization: { id: "org-1", name: "North" },
    roles: ["Content Consumer"],
    permissions: ["CONTENT_SEARCH", "CONTENT_VIEW"],
  };

  it("submits metadata terms and displays authorized citations without presenting a generated answer", async () => {
    const user = userEvent.setup();
    apiRequest.mockImplementation((path, options = {}) => {
      if (path === "/auth/me/") return Promise.resolve(consumer);
      if (path === "/assistant/query/" && options.method === "POST") {
        return Promise.resolve({
          answer: "I found 1 authorized content item(s) with matching metadata. The citations below are permission-checked references; no answer was generated.",
          citations: [{
            content_id: "content-1",
            title: "Quarterly policy guidance",
            version_number: 2,
            program_names: ["Safety Program"],
            source_summary: "Policy guidance for the program.",
          }],
          insufficient_authorized_sources: false,
        });
      }
      return Promise.resolve([]);
    });

    render(
      <MemoryRouter initialEntries={["/assistant"]}>
        <App />
      </MemoryRouter>,
    );

    await user.type(
      await screen.findByLabelText("Search authorized content"),
      "Quarterly policy guidance",
    );
    await user.click(await screen.findByRole("button", { name: "Search authorized content" }));
    expect(apiRequest).toHaveBeenCalledWith("/assistant/query/", {
      method: "POST",
      body: { question: "Quarterly policy guidance" },
    });
    expect(await screen.findByRole("heading", { name: "Matching content" })).toBeInTheDocument();
    expect(screen.getByText("Quarterly policy guidance")).toBeInTheDocument();
    expect(screen.getByText("Safety Program")).toBeInTheDocument();
    expect(screen.getByText(/no answer was generated/)).toBeInTheDocument();
    const limitationNotice = screen.getByRole("note");
    const pageHeader = screen.getByRole("heading", { name: "Knowledge search" }).closest("header");
    expect(pageHeader.nextElementSibling).toBe(limitationNotice);
    expect(limitationNotice).toHaveClass("notice-info");
    expect(limitationNotice).toHaveTextContent(/does not search document contents/);
    const searchForm = screen.getByLabelText("Search authorized content").closest("form");
    expect(searchForm).toHaveClass("knowledge-search-toolbar");
    expect(screen.getByLabelText("Search authorized content").closest("label"))
      .toContainElement(screen.getByLabelText("Search authorized content"));
    expect(searchForm).toContainElement(
      within(searchForm).getByRole("button", { name: "Search authorized content" }),
    );
    const navigation = screen.getByRole("navigation", { name: "Main navigation" });
    expect(navigation.nextElementSibling).toHaveClass("sidebar-footer");
  });

  it("validates blank input and surfaces API errors", async () => {
    const user = userEvent.setup();
    apiRequest.mockImplementation((path) => {
      if (path === "/auth/me/") return Promise.resolve(consumer);
      if (path === "/assistant/query/") {
        return Promise.reject(new Error("Search permission is required."));
      }
      return Promise.resolve([]);
    });

    render(
      <MemoryRouter initialEntries={["/assistant"]}>
        <App />
      </MemoryRouter>,
    );

    await user.click(await screen.findByRole("button", { name: "Search authorized content" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Enter a search question.");
    expect(apiRequest).not.toHaveBeenCalledWith(
      "/assistant/query/",
      expect.anything(),
    );

    await user.type(await screen.findByLabelText("Search authorized content"), "not permitted");
    await user.click(screen.getByRole("button", { name: "Search authorized content" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Search permission is required.",
    );
  });
});

describe("authenticated content workflow", () => {
  it("creates content and opens its details", async () => {
    const user = userEvent.setup();
    let contentCreated = false;
    apiRequest.mockImplementation((path, options = {}) => {
      if (path === "/auth/me/") {
        return Promise.resolve({
          id: "user-1",
          name: "Avery User",
          email: "avery@example.test",
          organization: { id: "org-1", name: "North" },
          roles: ["Content Manager"],
          permissions: ["CONTENT_VIEW", "CONTENT_CREATE"],
        });
      }
      if (path === "/content/" && options.method === "POST") {
        contentCreated = true;
        return Promise.resolve({
          id: "content-1",
          title: "Operating guide",
          description: "A governed business reference.",
          status: "DRAFT",
        });
      }
      if (path.startsWith("/content/?")) {
        return Promise.resolve({
          results: contentCreated
            ? [
                {
                  id: "content-1",
                  title: "Operating guide",
                  description: "A governed business reference.",
                  status: "DRAFT",
                },
              ]
            : [],
          meta: { page: 1, page_size: 100, total: contentCreated ? 1 : 0 },
        });
      }
      return Promise.resolve([]);
    });

    render(
      <MemoryRouter initialEntries={["/content"]}>
        <App />
      </MemoryRouter>,
    );

    await user.click(await screen.findByRole("button", { name: "+ Create content" }));
    await user.type(await screen.findByLabelText("Title"), "Operating guide");
    await user.type(screen.getByLabelText("Description"), "A governed business reference.");
    await user.click(screen.getByRole("button", { name: "Create content" }));

    expect(
      await screen.findByRole("heading", { name: "Operating guide" }),
    ).toBeInTheDocument();
    expect(apiRequest).toHaveBeenCalledWith("/content/", {
      method: "POST",
      body: {
        title: "Operating guide",
        description: "A governed business reference.",
      },
    });
  });

  it("opens the protected preview route only for permitted content managers", async () => {
    const user = userEvent.setup();
    apiRequest.mockImplementation((path, options = {}) => {
      if (path === "/auth/me/") {
        return Promise.resolve({
          id: "manager-1",
          name: "Casey Manager",
          email: "casey@example.test",
          organization: { id: "org-1", name: "North" },
          roles: ["Content Manager"],
          permissions: [
            "CONTENT_VIEW",
            "CONTENT_SEARCH",
            "VERSION_VIEW",
            "CONTENT_PREVIEW",
          ],
        });
      }
      if (path === "/content/?page_size=100") {
        return Promise.resolve([{
          id: "content-1",
          title: "Operating guide",
          status: "PUBLISHED",
        }]);
      }
      if (path === "/content/content-1/versions/") {
        return Promise.resolve([{
          id: "version-1",
          version_number: 1,
          status: "PUBLISHED",
          created_at: "2026-10-19T10:00:00Z",
        }]);
      }
      if (path === "/content/content-1/preview/" && options.method === "POST") {
        return Promise.resolve({
          access_id: "preview-1",
          content_id: "content-1",
          version_id: "version-1",
        });
      }
      if (path === "/content/content-1/") {
        return Promise.resolve({
          id: "content-1",
          title: "Operating guide",
          status: "PUBLISHED",
        });
      }
      if (
        path === "/content/content-1/preview/preview-1/delivery/?page=1"
        && options.expect === "response"
      ) {
        return Promise.reject(
          Object.assign(new Error("Unsupported format."), { status: 415 }),
        );
      }
      return Promise.resolve([]);
    });

    render(
      <MemoryRouter initialEntries={["/content"]}>
        <App />
      </MemoryRouter>,
    );

    await user.click(await screen.findByRole("button", { name: "Operating guide" }));
    await user.click(await screen.findByRole("button", { name: "Preview" }));

    expect(await screen.findByText(/PREVIEW — this protected preview/)).toBeInTheDocument();
    expect(apiRequest).toHaveBeenCalledWith("/content/content-1/preview/", {
      method: "POST",
      body: { version_id: "version-1" },
    });
    expect(apiRequest).toHaveBeenCalledWith(
      "/content/content-1/preview/preview-1/delivery/?page=1",
      { expect: "response" },
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This file format is not yet supported in the protected viewer.",
    );
  });

  it("does not offer preview to users without the explicit preview permission", async () => {
    const user = userEvent.setup();
    apiRequest.mockImplementation((path) => {
      if (path === "/auth/me/") {
        return Promise.resolve({
          id: "manager-1",
          name: "Casey Manager",
          email: "casey@example.test",
          organization: { id: "org-1", name: "North" },
          roles: ["Content Manager"],
          permissions: ["CONTENT_VIEW", "VERSION_VIEW"],
        });
      }
      if (path === "/content/?page_size=100") {
        return Promise.resolve([{
          id: "content-1",
          title: "Operating guide",
          status: "PUBLISHED",
        }]);
      }
      if (path === "/content/content-1/versions/") {
        return Promise.resolve([{
          id: "version-1",
          version_number: 1,
          status: "PUBLISHED",
          created_at: "2026-10-19T10:00:00Z",
        }]);
      }
      return Promise.resolve([]);
    });

    render(
      <MemoryRouter initialEntries={["/content"]}>
        <App />
      </MemoryRouter>,
    );

    await user.click(await screen.findByRole("button", { name: "Operating guide" }));
    expect(await screen.findByText("Version history")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Preview" })).not.toBeInTheDocument();
  });

  it("assigns multiple roles from the create-user dropdown", async () => {
    const user = userEvent.setup();
    const currentUser = {
      id: "admin-1",
      name: "Avery Admin",
      email: "avery@example.test",
      organization: { id: "org-1", name: "North" },
      roles: ["Administrator"],
      permissions: ["USER_VIEW", "USER_CREATE", "ROLE_MANAGE"],
    };
    apiRequest.mockImplementation((path, options = {}) => {
      if (path === "/auth/me/") return Promise.resolve(currentUser);
      if (path.startsWith("/users/?")) {
        return Promise.resolve({ results: [], meta: { page: 1, page_size: 20, total: 0 } });
      }
      if (path === "/roles/") {
        return Promise.resolve([
          {
            id: "role-1",
            name: "Content Manager",
            code: "content_manager",
            permissions: [{ code: "CONTENT_VIEW", name: "View content" }],
          },
          { id: "role-2", name: "Management", code: "management", permissions: [] },
        ]);
      }
      if (path === "/permissions/") return Promise.resolve([]);
      if (path === "/users/" && options.method === "POST") {
        return Promise.resolve({ temporary_password: "temporary" });
      }
      return Promise.resolve([]);
    });

    render(
      <MemoryRouter initialEntries={["/administrator"]}>
        <App />
      </MemoryRouter>,
    );

    await user.click(await screen.findByRole("tab", { name: "Roles & Permissions" }));
    expect(await screen.findByText("View content")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Organization users" }));
    await user.click(await screen.findByRole("button", { name: "+ Create User" }));
    await user.type(screen.getByLabelText("Full name"), "Jordan User");
    await user.type(screen.getByLabelText("Email"), "jordan@example.test");
    await user.click(await screen.findByText("Select roles"));
    await user.click(screen.getByRole("checkbox", { name: "Content Manager" }));
    await user.click(screen.getByRole("checkbox", { name: "Management" }));
    await user.click(screen.getByRole("button", { name: "Create user" }));

    expect(apiRequest).toHaveBeenCalledWith("/users/", {
      method: "POST",
      body: {
        name: "Jordan User",
        email: "jordan@example.test",
        role_ids: ["role-1", "role-2"],
      },
    });
    expect(await screen.findByText("temporary")).toBeInTheDocument();
  });

  it("opens program creation in a dialog", async () => {
    const user = userEvent.setup();
    apiRequest.mockImplementation((path, options = {}) => {
      if (path === "/auth/me/") {
        return Promise.resolve({
          id: "manager-1",
          name: "Casey Manager",
          email: "casey@example.test",
          organization: { id: "org-1", name: "North" },
          roles: ["Content Manager"],
          permissions: ["PROGRAM_VIEW", "PROGRAM_CREATE"],
        });
      }
      if (path === "/programs/" && options.method === "POST") {
        return Promise.resolve({ id: "program-1" });
      }
      if (path.startsWith("/programs/?")) {
        return Promise.resolve({ results: [], meta: { page: 1, page_size: 100, total: 0 } });
      }
      if (path === "/content/?page_size=100") return Promise.resolve([]);
      return Promise.resolve([]);
    });

    render(
      <MemoryRouter initialEntries={["/programs"]}>
        <App />
      </MemoryRouter>,
    );

    await user.click(await screen.findByRole("button", { name: "+ Create program" }));
    await user.type(screen.getByLabelText("Name"), "Reference Program");
    await user.type(screen.getByLabelText("Description"), "Organizes references.");
    await user.click(screen.getByRole("button", { name: "Create program" }));

    expect(apiRequest).toHaveBeenCalledWith("/programs/", {
      method: "POST",
      body: { name: "Reference Program", description: "Organizes references." },
    });
    expect(await screen.findByRole("status")).toHaveTextContent("Program created.");
  });

  it("provides full-window viewer controls and explains unsupported formats", async () => {
    const user = userEvent.setup();
    const unsupported = Object.assign(new Error("Unsupported format."), { status: 415 });
    apiRequest.mockImplementation((path, options = {}) => {
      if (path === "/auth/me/") {
        return Promise.resolve({
          id: "consumer-1",
          name: "Casey Consumer",
          email: "casey@example.test",
          organization: { id: "org-1", name: "North" },
          roles: ["Content Consumer"],
          permissions: ["SECURE_DELIVERY"],
        });
      }
      if (path === "/content/?page_size=100") {
        return Promise.resolve([{ id: "content-1", title: "Presentation", status: "PUBLISHED" }]);
      }
      if (path === "/programs/?page_size=100") {
        return Promise.resolve([{ id: "program-1", name: "Reference Program", status: "ACTIVE" }]);
      }
      if (path === "/content/content-1/access/" && options.method === "POST") {
        return Promise.resolve({ access_id: "access-1", content_id: "content-1" });
      }
      if (options.expect === "response") return Promise.reject(unsupported);
      return Promise.resolve([]);
    });

    render(
      <MemoryRouter initialEntries={["/viewer"]}>
        <App />
      </MemoryRouter>,
    );

    await screen.findByRole("option", { name: "Presentation" });
    await user.selectOptions(screen.getByLabelText("Published content"), "content-1");
    await screen.findByRole("option", { name: "Reference Program" });
    await user.selectOptions(screen.getByLabelText("Active program"), "program-1");
    await user.click(screen.getByRole("button", { name: "Open content" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "PowerPoint and video rendering are planned for future development",
    );
    await user.click(screen.getByRole("button", { name: "Open full window" }));

    expect(screen.getByRole("link", { name: "Back to content library" })).toHaveAttribute("href", "/content");
    expect(screen.getByRole("button", { name: "Previous page" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next page" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Exit full window" })).toBeInTheDocument();
  });
});
