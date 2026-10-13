const API_ROOT = "/api/v1";

let csrfToken = null;

export class ApiError extends Error {
  constructor(message, status, code = "API_ERROR") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function readJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function formatErrorDetails(details) {
  if (!details || typeof details !== "object" || Array.isArray(details)) return [];

  return Object.entries(details).flatMap(([field, value]) => {
    const messages = Array.isArray(value) ? value : [value];
    return messages
      .filter((message) => typeof message === "string" || typeof message === "number")
      .map((message) => `${field}: ${message}`);
  });
}

export async function refreshCsrfToken() {
  const response = await fetch(`${API_ROOT}/auth/csrf/`, {
    credentials: "include",
    headers: { Accept: "application/json" },
  });
  const payload = await readJson(response);
  if (!response.ok || !payload?.data?.csrf_token) {
    throw new ApiError("Unable to initialize secure requests.", response.status);
  }
  csrfToken = payload.data.csrf_token;
  return csrfToken;
}

export async function apiRequest(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const headers = new Headers(options.headers || {});
  headers.set("Accept", options.expect === "response" ? "*/*" : "application/json");

  if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
    if (!csrfToken) await refreshCsrfToken();
    headers.set("X-CSRFToken", csrfToken);
  }
  if (options.body !== undefined && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_ROOT}${path}`, {
    method,
    credentials: "include",
    headers,
    body:
      options.body instanceof FormData
        ? options.body
        : options.body === undefined
          ? undefined
          : JSON.stringify(options.body),
  });

  if (options.expect === "response" && response.ok) return response;
  if (response.status === 204) return null;

  const payload = await readJson(response);
  if (!response.ok) {
    const message = payload?.error?.message || payload?.detail || "The request could not be completed.";
    const details = formatErrorDetails(payload?.error?.details);
    throw new ApiError(
      [message, ...details].join(" "),
      response.status,
      payload?.error?.code,
    );
  }
  if (path === "/auth/login/") {
    csrfToken = null;
    await refreshCsrfToken();
  }
  if (payload?.meta && Array.isArray(payload.data)) {
    return { results: payload.data, meta: payload.meta };
  }
  return payload?.data ?? payload;
}

export function resetCsrfTokenForTests() {
  csrfToken = null;
}
