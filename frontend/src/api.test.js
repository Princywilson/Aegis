import { afterEach, describe, expect, it, vi } from "vitest";

import { apiRequest, resetCsrfTokenForTests } from "./api.js";

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("API client", () => {
  afterEach(() => {
    resetCsrfTokenForTests();
    vi.unstubAllGlobals();
  });

  it("sends session credentials and a refreshed CSRF token for login", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ data: { csrf_token: "before-login" } }))
      .mockResolvedValueOnce(jsonResponse({ data: { user: { id: "user-1" } } }))
      .mockResolvedValueOnce(jsonResponse({ data: { csrf_token: "after-login" } }));
    vi.stubGlobal("fetch", fetchMock);

    await apiRequest("/auth/login/", {
      method: "POST",
      body: {
        organization_slug: "north",
        email: "user@example.test",
        password: "secret",
      },
    });

    expect(fetchMock).toHaveBeenCalledTimes(3);
    const loginOptions = fetchMock.mock.calls[1][1];
    expect(loginOptions.credentials).toBe("include");
    expect(loginOptions.headers.get("X-CSRFToken")).toBe("before-login");
    expect(JSON.parse(loginOptions.body)).toEqual({
      organization_slug: "north",
      email: "user@example.test",
      password: "secret",
    });
  });

  it("preserves pagination metadata and exposes API errors", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({ data: [{ id: "content-1" }], meta: { page: 1, total: 1 } }),
      )
      .mockResolvedValueOnce(
        jsonResponse({ error: { code: "FORBIDDEN", message: "Not allowed." } }, 403),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiRequest("/content/")).resolves.toEqual({
      results: [{ id: "content-1" }],
      meta: { page: 1, total: 1 },
    });
    await expect(apiRequest("/audits/")).rejects.toMatchObject({
      name: "ApiError",
      status: 403,
      message: "Not allowed.",
    });
  });

  it("includes field-level validation details in API error messages", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce(jsonResponse({ data: { csrf_token: "csrf-token" } }))
        .mockResolvedValueOnce(
          jsonResponse(
            {
              error: {
                code: "VALIDATION_ERROR",
                message: "One or more fields are invalid.",
                details: { user_id: ["Program access can only be granted to a Content Consumer."] },
              },
            },
            400,
          ),
      ),
    );

    await expect(apiRequest("/program-access-grants/", { method: "POST", body: {} }))
      .rejects.toMatchObject({
        status: 400,
        message: "One or more fields are invalid. user_id: Program access can only be granted to a Content Consumer.",
      });
  });
});
