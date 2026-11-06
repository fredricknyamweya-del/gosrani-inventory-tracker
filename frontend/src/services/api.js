const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api"
).replace(/\/+$/, "");

function csrfToken(path) {
  if (typeof document === "undefined") return "";
  const cookieName = path === "/auth/refresh" ? "csrf_refresh_token" : "csrf_access_token";
  const cookie = document.cookie
    .split("; ")
    .find((entry) => entry.startsWith(`${cookieName}=`));
  return cookie ? decodeURIComponent(cookie.slice(cookieName.length + 1)) : "";
}

async function request(path, { method = "GET", body, query } = {}) {
  const url = new URL(`${API_BASE_URL}${path}`);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }

  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (
    ["POST", "PUT", "PATCH", "DELETE"].includes(method) &&
    path !== "/auth/login"
  ) {
    const token = csrfToken(path);
    if (token) headers["X-CSRF-TOKEN"] = token;
  }

  let response;
  try {
    response = await fetch(url, {
      method,
      headers,
      credentials: "include",
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
  } catch {
    throw new Error(
      `Unable to reach the Gosrani API at ${API_BASE_URL}. Check that the backend is running and VITE_API_BASE_URL is correct.`,
    );
  }

  let result;
  try {
    result = response.status === 204 ? {} : await response.json();
  } catch {
    throw new Error(`The API returned an invalid response (${response.status}).`);
  }
  if (!response.ok) {
    const error = new Error(result.message || `The request failed (${response.status}).`);
    error.status = response.status;
    error.code = result.code;
    error.errors = result.errors ?? [];
    const suggestion = result.suggestion;
    if (suggestion) error.suggestion = suggestion;
    throw error;
  }
  return result;
}

function normalized(value) {
  return String(value ?? "").trim().replace(/\s+/g, " ").toLocaleLowerCase();
}

function editDistance(left, right) {
  const previous = Array.from({ length: right.length + 1 }, (_, index) => index);
  for (let row = 1; row <= left.length; row += 1) {
    let diagonal = previous[0];
    previous[0] = row;
    for (let column = 1; column <= right.length; column += 1) {
      const above = previous[column];
      previous[column] = Math.min(
        previous[column] + 1,
        previous[column - 1] + 1,
        diagonal + (left[row - 1] === right[column - 1] ? 0 : 1),
      );
      diagonal = above;
    }
  }
  return previous[right.length];
}

export function findCatalogNearMatch(name, categoryId, items = []) {
  const target = normalized(name);
  if (!target) return null;
  return (
    items
      .filter((item) => String(item.categoryId) === String(categoryId))
      .map((item) => item.name)
      .find((candidate) => {
        const comparison = normalized(candidate);
        const maxLength = Math.max(target.length, comparison.length);
        return (
          maxLength > 3 &&
          editDistance(target, comparison) <= Math.max(1, Math.floor(maxLength * 0.2))
        );
      }) ?? null
  );
}

export function getCatalogSpecificationExample(items, categoryId) {
  return (
    items
      .filter(
        (item) => item.active && String(item.categoryId) === String(categoryId),
      )
      .flatMap((item) => item.specifications)
      .find(Boolean) ?? null
  );
}

export const api = {
  login(credentials = {}) {
    return request("/auth/login", { method: "POST", body: credentials });
  },

  me() {
    return request("/auth/me");
  },

  logout() {
    return request("/auth/logout", { method: "POST", body: {} });
  },

  getInventory(params = {}) {
    return request("/inventory", { query: params });
  },

  getInventoryById(id) {
    return request(`/inventory/${encodeURIComponent(id)}`);
  },

  validateInventory(input) {
    return request("/inventory/validate", { method: "POST", body: input });
  },

  createInventory(input) {
    return request("/inventory", { method: "POST", body: input });
  },

  updateInventory(id, input = {}) {
    return request(`/inventory/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: input,
    });
  },

  deleteInventory(id) {
    return request(`/inventory/${encodeURIComponent(id)}`, { method: "DELETE" });
  },

  assistantQuery(question) {
    return request("/assistant/query", {
      method: "POST",
      body: { question },
    });
  },

  queryAssistant(question) {
    return api.assistantQuery(question);
  },

  getUsers() {
    return request("/users");
  },

  createUser(input = {}) {
    return request("/users", { method: "POST", body: input });
  },

  updateUser(id, input = {}) {
    return request(`/users/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: input,
    });
  },

  getCatalog() {
    return request("/catalog");
  },

  createCatalogItem(input = {}) {
    return request("/catalog/items", { method: "POST", body: input });
  },

  updateCatalogItem(id, input = {}) {
    return request(`/catalog/items/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: input,
    });
  },

  createCatalogCategory(input = {}) {
    return request("/catalog/categories", { method: "POST", body: input });
  },

  createCatalogRequest(input = {}) {
    return request("/catalog/requests", { method: "POST", body: input });
  },

  getCatalogRequests() {
    return request("/catalog/requests");
  },

  updateCatalogRequest(id, input = {}) {
    return request(`/catalog/requests/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: input,
    });
  },
};
