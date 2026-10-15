import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
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
