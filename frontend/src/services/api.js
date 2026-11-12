const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api"
).replace(/\/+$/, "");
const AUTH_STORAGE_KEY = "gosrani:authTokens";
let refreshRequest = null;

function getAuthTokens() {
  if (typeof window === "undefined") return {};
  const stored = window.localStorage.getItem(AUTH_STORAGE_KEY);
  if (!stored) return {};
  try {
    const tokens = JSON.parse(stored);
    return {
      accessToken:
        typeof tokens.accessToken === "string" ? tokens.accessToken : null,
      refreshToken:
        typeof tokens.refreshToken === "string" ? tokens.refreshToken : null,
    };
  } catch {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    return {};
  }
}

function storeAuthTokens(data) {
  if (
    typeof window !== "undefined" &&
    typeof data?.accessToken === "string" &&
    typeof data?.refreshToken === "string"
  ) {
    window.localStorage.setItem(
      AUTH_STORAGE_KEY,
      JSON.stringify({
        accessToken: data.accessToken,
        refreshToken: data.refreshToken,
      }),
    );
  }
}

function clearAuthTokens() {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
  }
}

async function request(path, options = {}, retryAfterRefresh = true) {
  const { method = "GET", body, query, cache: cacheMode } = options;
  const url = new URL(`${API_BASE_URL}${path}`);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }

  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const tokens = getAuthTokens();
  const token = path === "/auth/refresh"
    ? tokens.refreshToken
    : path === "/auth/login"
      ? null
      : tokens.accessToken;
  if (token) headers.Authorization = `Bearer ${token}`;
  const requestBody =
    path === "/auth/logout"
      ? { ...(body ?? {}), refreshToken: tokens.refreshToken }
      : body;

  let response;
  try {
    response = await fetch(url, {
      method,
      headers,
      credentials: "omit",
      ...(cacheMode ? { cache: cacheMode } : {}),
      ...(requestBody !== undefined
        ? { body: JSON.stringify(requestBody) }
        : {}),
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
  storeAuthTokens(result.data);
  if (
    response.status === 401 &&
    retryAfterRefresh &&
    !["/auth/login", "/auth/refresh"].includes(path)
  ) {
    refreshRequest ??= request(
      "/auth/refresh",
      { method: "POST", body: {} },
      false,
    ).finally(() => {
      refreshRequest = null;
    });
    await refreshRequest;
    return request(path, options, false);
  }
  if (!response.ok) {
    if (path === "/auth/refresh" && response.status === 401) {
      clearAuthTokens();
    }
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

  changePassword(input = {}) {
    return request("/auth/change-password", { method: "POST", body: input });
  },

  logout() {
    return request("/auth/logout", {
      method: "POST",
      body: {},
    }).finally(clearAuthTokens);
  },

  getInventory(params = {}) {
    return request("/inventory", { query: params });
  },

  getInventoryById(id) {
    return request(`/inventory/${encodeURIComponent(id)}`);
  },

  getInventoryStock(id) {
    return request(`/inventory/${encodeURIComponent(id)}/stock`, {
      cache: "no-store",
    });
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

  async deleteInventory(id) {
    const response = await request(`/inventory/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("inventory-stock-changed"));
    }
    return response;
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

  getLocations() {
    return request("/locations");
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

  deleteUser(id) {
    return request(`/users/${encodeURIComponent(id)}`, { method: "DELETE" });
  },

  getCatalog() {
    return request("/catalog");
  },

  getInventorySummary() {
    return request("/catalog/summary", { cache: "no-store" });
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
