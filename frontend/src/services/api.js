const wait = (milliseconds = 80) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

const clone = (value) => structuredClone(value);
const ok = (data, meta) => ({
  data: clone(data),
  ...(meta ? { meta: clone(meta) } : {}),
});

function fail(status, message, extra = {}) {
  const error = new Error(message);
  error.status = status;
  Object.assign(error, extra);
  throw error;
}

function normalized(value) {
  return String(value ?? "").trim().toLocaleLowerCase();
}

function findNearMatch(value, values) {
  const target = normalized(value).replace(/\s+/g, " ");
  if (!target) return null;

  const distance = (left, right) => {
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
  };

  return values.find((candidate) => {
    const comparison = normalized(candidate).replace(/\s+/g, " ");
    const maxLength = Math.max(target.length, comparison.length);
    return (
      maxLength > 3 &&
      distance(target, comparison) <= Math.max(1, Math.floor(maxLength * 0.2))
    );
  }) ?? null;
}

export function findCatalogNearMatch(name, categoryId) {
  const candidates = catalog.items
    .filter((item) => item.categoryId === categoryId)
    .map((item) => item.name);
  return findNearMatch(name, candidates);
}

const categories = [
  { id: "cat-flour-grains", name: "Flour & Grains" },
  { id: "cat-cooking-oils", name: "Cooking Oils" },
  { id: "cat-sugar-salt", name: "Sugar & Salt" },
  { id: "cat-household", name: "Household" },
];

const catalog = {
  categories,
  items: [
    {
      id: "item-maize-flour",
      categoryId: "cat-flour-grains",
      name: "Maize Flour",
      specifications: ["1 kg", "2 kg", "5 kg"],
      active: true,
    },
    {
      id: "item-wheat-flour",
      categoryId: "cat-flour-grains",
      name: "Wheat Flour",
      specifications: ["1 kg", "2 kg", "5 kg"],
      active: true,
    },
    {
      id: "item-rice",
      categoryId: "cat-flour-grains",
      name: "Rice",
      specifications: ["1 kg", "2 kg", "5 kg"],
      active: true,
    },
    {
      id: "item-cooking-oil",
      categoryId: "cat-cooking-oils",
      name: "Cooking Oil",
      specifications: ["1 L", "5 L"],
      active: true,
    },
    {
      id: "item-white-sugar",
      categoryId: "cat-sugar-salt",
      name: "White Sugar",
      specifications: ["1 kg", "2 kg", "5 kg"],
      active: true,
    },
    {
      id: "item-salt",
      categoryId: "cat-sugar-salt",
      name: "Salt",
      specifications: ["500 g", "1 kg"],
      active: true,
    },
    {
      id: "item-bar-soap",
      categoryId: "cat-household",
      name: "Bar Soap",
      specifications: ["800 g", "1 kg"],
      active: true,
    },
  ],
};

const seedRecords = [
  {
    id: "INV-1048",
    date: "2026-03-10",
    category: "Flour & Grains",
    item: "Maize Flour",
    size: "2 kg",
    quantityIn: 240,
    quantityOut: null,
    details: "Received from main supplier",
    addedBy: "Grace Wanjiku",
    createdAt: "2026-03-10T08:42:00.000Z",
    modifiedBy: "Grace Wanjiku",
    status: "Locked",
  },
  {
    id: "INV-1047",
    date: "2026-03-09",
    category: "Cooking Oils",
    item: "Cooking Oil",
    size: "1 L",
    quantityIn: null,
    quantityOut: 48,
    details: "Dispatch to Annex branch",
    addedBy: "Samuel Kiptoo",
    createdAt: "2026-03-09T15:18:00.000Z",
    modifiedBy: "Samuel Kiptoo",
    status: "Locked",
  },
  {
    id: "INV-1046",
    date: "2026-03-09",
    category: "Sugar & Salt",
    item: "White Sugar",
    size: "1 kg",
    quantityIn: 120,
    quantityOut: null,
    details: "PO 416 delivery",
    addedBy: "Grace Wanjiku",
    createdAt: "2026-03-09T10:05:00.000Z",
    modifiedBy: "Grace Wanjiku",
    status: "Saved",
  },
  {
    id: "INV-1045",
    date: "2026-03-08",
    category: "Household",
    item: "Bar Soap",
    size: "800 g",
    quantityIn: null,
    quantityOut: 36,
    details: "Counter sales",
    addedBy: "Daniel Otieno",
    createdAt: "2026-03-08T16:32:00.000Z",
    modifiedBy: "Daniel Otieno",
    status: "Locked",
  },
  {
    id: "INV-1044",
    date: "2026-03-07",
    category: "Flour & Grains",
    item: "Rice",
    size: "5 kg",
    quantityIn: 80,
    quantityOut: null,
    details: "Weekly restock",
    addedBy: "Samuel Kiptoo",
    createdAt: "2026-03-07T09:21:00.000Z",
    modifiedBy: "Samuel Kiptoo",
    status: "Saved",
  },
  {
    id: "INV-1043",
    date: "2026-03-06",
    category: "Flour & Grains",
    item: "Wheat Flour",
    size: "2 kg",
    quantityIn: null,
    quantityOut: 75,
    details: "Wholesale order 0981",
    addedBy: "Grace Wanjiku",
    createdAt: "2026-03-06T13:12:00.000Z",
    modifiedBy: "Grace Wanjiku",
    status: "Locked",
  },
  {
    id: "INV-1042",
    date: "2026-03-05",
    category: "Cooking Oils",
    item: "Cooking Oil",
    size: "5 L",
    quantityIn: 60,
    quantityOut: null,
    details: "Supplier delivery",
    addedBy: "Daniel Otieno",
    createdAt: "2026-03-05T11:47:00.000Z",
    modifiedBy: "Daniel Otieno",
    status: "Saved",
  },
  {
    id: "INV-1041",
    date: "2026-03-04",
    category: "Flour & Grains",
    item: "Maize Flour",
    size: "1 kg",
    quantityIn: 300,
    quantityOut: 24,
    details: "Opening balance adjustment",
    addedBy: "Grace Wanjiku",
    createdAt: "2026-03-04T08:10:00.000Z",
    modifiedBy: "Admin User",
    status: "Locked",
  },
  {
    id: "INV-1040",
    date: "2026-03-03",
    category: "Sugar & Salt",
    item: "Salt",
    size: "500 g",
    quantityIn: 180,
    quantityOut: null,
    details: "Monthly restock",
    addedBy: "Samuel Kiptoo",
    createdAt: "2026-03-03T14:24:00.000Z",
    modifiedBy: "Samuel Kiptoo",
    status: "Saved",
  },
];

const seedUsers = [
  {
    id: 1,
    name: "Admin User",
    email: "admin@gosrani.co.ke",
    role: "Admin",
    status: "Active",
    password: "admin123",
  },
  {
    id: 2,
    name: "Grace Wanjiku",
    email: "grace@gosrani.co.ke",
    role: "User",
    status: "Active",
    password: "user123",
  },
  {
    id: 3,
    name: "Samuel Kiptoo",
    email: "samuel@gosrani.co.ke",
    role: "User",
    status: "Active",
    password: "user123",
  },
  {
    id: 4,
    name: "Daniel Otieno",
    email: "daniel@gosrani.co.ke",
    role: "User",
    status: "Inactive",
    password: "user123",
  },
];

let records = seedRecords;
let users = seedUsers;
let requests = [
  {
    id: "REQ-1001",
    categoryId: "cat-household",
    category: "Household",
    itemId: null,
    itemName: "Dishwashing Liquid",
    specification: "1 L",
    note: "Frequently requested by the cleaning team",
    requestedById: 2,
    requestedBy: "Grace Wanjiku",
    status: "Pending",
    createdAt: "2026-03-11T09:20:00.000Z",
  },
  {
    id: "REQ-1002",
    categoryId: "cat-flour-grains",
    category: "Flour & Grains",
    itemId: "item-rice",
    itemName: "Rice",
    specification: "10 kg",
    note: "",
    requestedById: 3,
    requestedBy: "Samuel Kiptoo",
    status: "Pending",
    createdAt: "2026-03-11T10:05:00.000Z",
  },
];

let activeUser = null;
const AUTH_TOKEN_KEY = "gosrani-auth-token";
let nextRecordId = 1049;
let nextUserId = 5;
let nextItemId = 1;
let nextCategoryId = 1;
let nextRequestId = 1003;

function ensureSignedIn() {
  if (!activeUser) fail(401, "Please sign in to continue.");
}

function ensureAdmin() {
  ensureSignedIn();
  if (activeUser.role !== "Admin") {
    fail(403, "This action is available to administrators only.");
  }
}

function ensureStaff() {
  ensureSignedIn();
  if (activeUser.role !== "User") {
    fail(403, "This action is available to staff users only.");
  }
}

function publicUser(user) {
  const { password: _password, ...safeUser } = user;
  return safeUser;
}

function requireText(value, label) {
  const text = String(value ?? "").trim();
  if (!text) fail(422, `${label} is required.`);
  return text;
}

function getCategory(value) {
  const key = normalized(value);
  return catalog.categories.find(
    (category) =>
      normalized(category.id) === key || normalized(category.name) === key,
  );
}

function getItem(value, categoryId) {
  const key = normalized(value);
  return catalog.items.find(
    (item) =>
      item.categoryId === categoryId &&
      (normalized(item.id) === key || normalized(item.name) === key),
  );
}

function normalizeQuantity(value, label) {
  if (value === "" || value == null) return null;
  const quantity = Number(value);
  if (!Number.isInteger(quantity) || quantity < 0) {
    fail(422, `${label} must be a whole non-negative number.`);
  }
  return quantity;
}

function normalizeRecord(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    fail(422, "Each inventory entry must be an object.");
  }

  const date = requireText(input.date, "Date");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
    fail(422, "Date must use the ISO YYYY-MM-DD format.");
  }
  const [year, month, day] = date.split("-").map(Number);
  const parsedDate = new Date(Date.UTC(year, month - 1, day));
  if (
    parsedDate.getUTCFullYear() !== year ||
    parsedDate.getUTCMonth() !== month - 1 ||
    parsedDate.getUTCDate() !== day
  ) {
    fail(422, "Date must be a valid calendar date.");
  }

  const category = getCategory(input.category ?? input.categoryId);
  if (!category) fail(422, "Category must be selected from the catalog.");

  const itemName = requireText(input.item ?? input.itemId, "Item");
  const item = getItem(itemName, category.id);
  if (!item || !item.active) {
    fail(422, "Item must be an active item in the selected category.");
  }

  const sizeValue = String(input.size ?? input.specification ?? "").trim();
  if (item.specifications.length > 0 && !sizeValue) {
    fail(422, "Size / Specifications is required for this item.");
  }
  const specification = item.specifications.find(
    (value) => normalized(value) === normalized(sizeValue),
  );
  if (sizeValue && !specification) {
    fail(422, "Size / Specifications must be selected from the item catalog.");
  }

  const quantityIn = normalizeQuantity(input.quantityIn, "Quantity In");
  const quantityOut = normalizeQuantity(input.quantityOut, "Quantity Out");
  if (quantityIn == null && quantityOut == null) {
    fail(422, "Enter a value for Quantity In or Quantity Out.");
  }

  return {
    date,
    category: category.name,
    item: item.name,
    size: specification ?? "",
    quantityIn,
    quantityOut,
    details: String(input.details ?? "").trim(),
  };
}

function itemMatchesRecord(item, record) {
  const category = getCategory(record.category);
  return (
    category?.id === item.categoryId &&
    normalized(item.name) === normalized(record.item)
  );
}

function createId(prefix, counter) {
  return `${prefix}-${counter}`;
}

function cleanSpecifications(values) {
  if (!Array.isArray(values)) fail(422, "Specifications must be a list.");
  const result = [];
  for (const value of values) {
    const specification = requireText(value, "Specification");
    if (result.some((entry) => normalized(entry) === normalized(specification))) {
      fail(422, `Specification "${specification}" already exists.`);
    }
    result.push(specification);
  }
  return result;
}

function assertUniqueItem(categoryId, name, excludedId) {
  const duplicate = catalog.items.find(
    (item) =>
      item.id !== excludedId &&
      item.categoryId === categoryId &&
      normalized(item.name) === normalized(name),
  );
  if (duplicate) {
    const suggestion = findNearMatch(
      name,
      catalog.items
        .filter((item) => item.categoryId === categoryId)
        .map((item) => item.name),
    );
    fail(
      422,
      `An item with this name already exists${suggestion ? `. Did you mean ${suggestion}?` : "."}`,
      { suggestion },
    );
  }
}

function addCatalogItem({ categoryId, category, name, specifications = [] }) {
  const selectedCategory = getCategory(categoryId ?? category);
  if (!selectedCategory) fail(422, "Choose a valid catalog category.");
  const itemName = requireText(name, "Item name");
  assertUniqueItem(selectedCategory.id, itemName);
  const savedSpecifications = cleanSpecifications(specifications);
  if (savedSpecifications.length === 0) {
    fail(422, "Add at least one item specification.");
  }

  const item = {
    id: createId("item-new", nextItemId++),
    categoryId: selectedCategory.id,
    name: itemName,
    specifications: savedSpecifications,
    active: true,
  };
  catalog.items.push(item);
  return item;
}

function formatToday() {
  const now = new Date();
  return `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, "0")}-${String(now.getUTCDate()).padStart(2, "0")}`;
}

function inventoryWarnings(row, index) {
  const flags = [];
  if ((row.quantityIn ?? 0) >= 500 || (row.quantityOut ?? 0) >= 500) {
    flags.push({
      field: "quantity",
      message: "Unusually large quantity. Check that the units are correct.",
    });
  }
  if (row.quantityIn != null && row.quantityOut != null) {
    flags.push({
      field: "quantity",
      message: "Both Quantity In and Quantity Out have values.",
    });
  }

  const stock = records
    .filter(
      (record) =>
        normalized(record.category) === normalized(row.category) &&
        normalized(record.item) === normalized(row.item) &&
        normalized(record.size) === normalized(row.size),
    )
    .reduce(
      (balance, record) =>
        balance + (record.quantityIn ?? 0) - (record.quantityOut ?? 0),
      0,
    );
  if (row.quantityOut != null && row.quantityOut > stock) {
    flags.push({
      field: "quantityOut",
      message: "Quantity Out is greater than the recorded available stock.",
    });
  }

  const daysFromToday =
    (Date.parse(`${row.date}T00:00:00.000Z`) -
      Date.parse(`${formatToday()}T00:00:00.000Z`)) /
    86_400_000;
  if (daysFromToday > 0) {
    flags.push({ field: "date", message: "This date is in the future." });
  }
  if (daysFromToday < -180) {
    flags.push({
      field: "date",
      message: "This date is more than six months in the past.",
    });
  }
  return { index, flags };
}

function createRequest(input) {
  const category = getCategory(input.categoryId ?? input.category);
  if (!category) fail(422, "Choose a valid catalog category.");

  const existingItem = input.itemId
    ? getItem(input.itemId, category.id)
    : getItem(input.itemName, category.id);
  const itemName = requireText(
    existingItem?.name ?? input.itemName,
    "Item name",
  );
  const specification = String(
    input.specification ?? input.size ?? "",
  ).trim();

  if (!existingItem && !specification) {
    fail(422, "Provide at least one specification for the new item.");
  }
  if (!specification) {
    fail(422, "Provide the missing specification.");
  }
  if (
    existingItem &&
    existingItem.specifications.some(
      (entry) => normalized(entry) === normalized(specification),
    )
  ) {
    fail(422, "This specification is already available in the catalog.");
  }

  const duplicateRequest = requests.find(
    (request) =>
      request.status === "Pending" &&
      request.categoryId === category.id &&
      normalized(request.itemName) === normalized(itemName) &&
      normalized(request.specification) === normalized(specification),
  );
  if (duplicateRequest) {
    fail(422, "A matching catalog request is already pending.");
  }

  const request = {
    id: createId("REQ", nextRequestId++),
    categoryId: category.id,
    category: category.name,
    itemId: existingItem?.id ?? null,
    itemName,
    specification,
    note: String(input.note ?? "").trim(),
    requestedById: activeUser.id,
    requestedBy: activeUser.name,
    status: "Pending",
    createdAt: new Date().toISOString(),
  };
  requests.unshift(request);
  return request;
}

export const api = {
  async login(credentials = {}) {
    await wait(100);
    const email = normalized(credentials.email);
    const password = String(credentials.password ?? "");
    const user = users.find(
      (entry) =>
        normalized(entry.email) === email &&
        entry.password === password &&
        entry.status === "Active",
    );
    if (!user) fail(401, "The email or password you entered is incorrect.");

    activeUser = publicUser(user);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(AUTH_TOKEN_KEY, `mock-jwt-${user.id}`);
    }
    return ok({
      token: `mock-jwt-${user.id}`,
      user: activeUser,
    });
  },

  async me() {
    await wait();
    if (!activeUser && typeof window !== "undefined") {
      const token = window.localStorage.getItem(AUTH_TOKEN_KEY);
      const userId = token?.match(/^mock-jwt-(\d+)$/)?.[1];
      const user = users.find(
        (entry) => entry.id === Number(userId) && entry.status === "Active",
      );
      if (user) activeUser = publicUser(user);
    }
    if (activeUser) {
      const user = users.find(
        (entry) => entry.id === activeUser.id && entry.status === "Active",
      );
      if (!user) {
        activeUser = null;
        if (typeof window !== "undefined") {
          window.localStorage.removeItem(AUTH_TOKEN_KEY);
        }
      } else {
        activeUser = publicUser(user);
      }
    }
    ensureSignedIn();
    return ok(activeUser);
  },

  logout() {
    activeUser = null;
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(AUTH_TOKEN_KEY);
    }
  },

  setActiveUser(user) {
    activeUser = user ? clone(user) : null;
    if (!user && typeof window !== "undefined") {
      window.localStorage.removeItem(AUTH_TOKEN_KEY);
    }
  },

  async getInventory(params = {}) {
    await wait();
    ensureSignedIn();
    let result = [...records];
    const query = normalized(params.search);
    if (query) {
      result = result.filter((record) =>
        [
          record.category,
          record.item,
          record.size,
          record.details,
          record.addedBy,
        ].some((value) => normalized(value).includes(query)),
      );
    }
    if (params.category) {
      result = result.filter(
        (record) =>
          normalized(record.category) === normalized(params.category),
      );
    }
    if (params.item) {
      result = result.filter(
        (record) => normalized(record.item) === normalized(params.item),
      );
    }
    if (params.size) {
      result = result.filter(
        (record) => normalized(record.size) === normalized(params.size),
      );
    }
    if (params.from) result = result.filter((record) => record.date >= params.from);
    if (params.to) result = result.filter((record) => record.date <= params.to);

    const sort = params.sort === "asc" ? "asc" : "desc";
    result.sort((left, right) =>
      sort === "asc"
        ? left.date.localeCompare(right.date)
        : right.date.localeCompare(left.date),
    );

    const page = Number(params.page ?? 1);
    const limit = Number(params.limit ?? 6);
    if (!Number.isInteger(page) || page < 1) {
      fail(422, "Page must be a positive whole number.");
    }
    if (!Number.isInteger(limit) || limit < 1 || limit > 100) {
      fail(422, "Limit must be a whole number between 1 and 100.");
    }
    const start = (page - 1) * limit;
    return ok(result.slice(start, start + limit), {
      page,
      limit,
      total: result.length,
      pages: Math.ceil(result.length / limit),
    });
  },

  async getInventoryById(id) {
    await wait();
    ensureSignedIn();
    const record = records.find((entry) => entry.id === id);
    if (!record) fail(404, "Inventory record not found.");
    return ok(record);
  },

  async validateInventory(input) {
    await wait();
    ensureSignedIn();
    const inputRows = Array.isArray(input) ? input : [input];
    if (inputRows.length === 0) fail(422, "Add at least one inventory entry.");

    const rows = inputRows.map(normalizeRecord);
    const warnings = rows.map(inventoryWarnings);
    return ok({ rows, warnings });
  },

  async createInventory(input) {
    await wait();
    ensureSignedIn();
    const inputRows = Array.isArray(input) ? input : [input];
    if (inputRows.length === 0) fail(422, "Add at least one inventory entry.");

    const normalizedRows = inputRows.map(normalizeRecord);
    const userName = activeUser.name;
    const status = activeUser.role === "User" ? "Locked" : "Saved";
    const created = normalizedRows.map((row) => ({
      ...row,
      id: createId("INV", nextRecordId++),
      addedBy: userName,
      createdAt: new Date().toISOString(),
      modifiedBy: userName,
      status,
    }));
    records = [...created, ...records];
    return ok(created);
  },

  async updateInventory(id, input = {}) {
    await wait();
    ensureAdmin();
    const index = records.findIndex((entry) => entry.id === id);
    if (index < 0) fail(404, "Inventory record not found.");

    const current = records[index];
    const updatedFields = normalizeRecord({ ...current, ...input });
    const status = input.status ?? current.status;
    if (!["Saved", "Locked"].includes(status)) {
      fail(422, "Status must be Saved or Locked.");
    }
    records[index] = {
      ...current,
      ...updatedFields,
      modifiedBy: activeUser.name,
      status,
    };
    return ok(records[index]);
  },

  async deleteInventory(id) {
    await wait();
    ensureAdmin();
    const index = records.findIndex((entry) => entry.id === id);
    if (index < 0) fail(404, "Inventory record not found.");
    records = records.filter((entry) => entry.id !== id);
    return ok({ id });
  },

  async assistantQuery(question) {
    await wait(140);
    ensureSignedIn();
    const query = String(question ?? "").trim().toLocaleLowerCase();
    if (!query) fail(422, "Ask a question first.");

    const item = catalog.items.find((entry) =>
      query.includes(normalized(entry.name)),
    );
    const specification = item?.specifications.find((value) =>
      query.includes(normalized(value)),
    );
    const wantsStock = /\b(stock|balance|remaining|left)\b/.test(query);
    let matchingRecords = records.filter((record) => {
      const recordText = normalized(
        `${record.category} ${record.item} ${record.size} ${record.details}`,
      );
      if (item && !itemMatchesRecord(item, record)) return false;
      if (
        specification &&
        normalized(record.size) !== normalized(specification)
      ) {
        return false;
      }
      const terms = query.split(/\s+/).filter((term) => term.length > 3);
      return terms.length === 0 || terms.some((term) => recordText.includes(term));
    });
    if (!item && matchingRecords.length === 0) {
      const terms = query.split(/\s+/).filter((term) => term.length > 3);
      matchingRecords = records.filter((record) =>
        terms.some((term) =>
          normalized(
            `${record.category} ${record.item} ${record.size} ${record.details}`,
          ).includes(term),
        ),
      );
    }
    matchingRecords = matchingRecords.slice(0, 6);

    let answer = matchingRecords.length
      ? `I found ${matchingRecords.length} matching inventory ${
          matchingRecords.length === 1 ? "record" : "records"
        }.`
      : "I could not find any records matching that request.";

    if (wantsStock && item) {
      const stockRecords = records.filter(
        (record) =>
          itemMatchesRecord(item, record) &&
          (!specification ||
            normalized(record.size) === normalized(specification)),
      );
      const balance = stockRecords.reduce(
        (total, record) =>
          total + (record.quantityIn ?? 0) - (record.quantityOut ?? 0),
        0,
      );
      answer = specification
        ? `Recorded stock for ${item.name} (${specification}) is ${balance}.`
        : `Recorded stock for ${item.name} is ${balance} across its specifications.`;
      matchingRecords = stockRecords.slice(0, 6);
    }

    return ok({ answer, records: matchingRecords });
  },

  async queryAssistant(question) {
    return api.assistantQuery(question);
  },

  async getUsers() {
    await wait();
    ensureAdmin();
    return ok(users.map(publicUser));
  },

  async createUser(input = {}) {
    await wait();
    ensureAdmin();
    const name = requireText(input.name, "Name");
    const email = requireText(input.email, "Email");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      fail(422, "Enter a valid email address.");
    }
    if (users.some((user) => normalized(user.email) === normalized(email))) {
      fail(422, "A user with this email already exists.");
    }
    const role = input.role ?? "User";
    if (!["Admin", "User"].includes(role)) {
      fail(422, "Role must be Admin or User.");
    }
    const user = {
      id: nextUserId++,
      name,
      email,
      role,
      status: "Active",
      password: String(input.password ?? "user123"),
    };
    users = [...users, user];
    return ok(publicUser(user));
  },

  async updateUser(id, input = {}) {
    await wait();
    ensureAdmin();
    const user = users.find((entry) => entry.id === Number(id));
    if (!user) fail(404, "User not found.");

    const changes = {};
    if (input.role != null) {
      if (!["Admin", "User"].includes(input.role)) {
        fail(422, "Role must be Admin or User.");
      }
      changes.role = input.role;
    }
    if (input.status != null) {
      if (!["Active", "Inactive"].includes(input.status)) {
        fail(422, "Status must be Active or Inactive.");
      }
      changes.status = input.status;
    }
    if (input.name != null) changes.name = requireText(input.name, "Name");
    if (input.email != null) {
      const email = requireText(input.email, "Email");
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        fail(422, "Enter a valid email address.");
      }
      if (
        users.some(
          (entry) =>
            entry.id !== user.id &&
            normalized(entry.email) === normalized(email),
        )
      ) {
        fail(422, "A user with this email already exists.");
      }
      changes.email = email;
    }

    Object.assign(user, changes);
    if (activeUser?.id === user.id) activeUser = publicUser(user);
    return ok(publicUser(user));
  },

  async getCatalog() {
    await wait();
    ensureSignedIn();
    return ok(catalog);
  },

  async createCatalogItem(input = {}) {
    await wait();
    ensureAdmin();
    return ok(addCatalogItem(input));
  },

  async updateCatalogItem(id, input = {}) {
    await wait();
    ensureAdmin();
    const item = catalog.items.find((entry) => entry.id === id);
    if (!item) fail(404, "Catalog item not found.");

    const changes = {};
    if (input.name != null) {
      const name = requireText(input.name, "Item name");
      assertUniqueItem(item.categoryId, name, item.id);
      changes.name = name;
    }
    let specifications = [...item.specifications];
    if (input.specifications != null) {
      specifications = cleanSpecifications(input.specifications);
    }
    if (input.addSpecifications != null) {
      const added = cleanSpecifications(input.addSpecifications);
      for (const specification of added) {
        if (
          specifications.some(
            (entry) => normalized(entry) === normalized(specification),
          )
        ) {
          fail(422, `Specification "${specification}" already exists.`);
        }
      }
      specifications.push(...added);
    }
    if (input.removeSpecifications != null) {
      if (!Array.isArray(input.removeSpecifications)) {
        fail(422, "Specifications to remove must be a list.");
      }
      const removed = new Set(input.removeSpecifications.map(normalized));
      specifications = specifications.filter(
        (specification) => !removed.has(normalized(specification)),
      );
    }
    if (input.active != null) {
      if (typeof input.active !== "boolean") {
        fail(422, "Active must be a boolean.");
      }
      changes.active = input.active;
    }
    Object.assign(item, changes, { specifications });
    return ok(item);
  },

  async createCatalogCategory(input = {}) {
    await wait();
    ensureAdmin();
    const name = requireText(input.name, "Category name");
    if (
      catalog.categories.some(
        (category) => normalized(category.name) === normalized(name),
      )
    ) {
      fail(422, "A category with this name already exists.");
    }
    const category = {
      id: createId("cat-new", nextCategoryId++),
      name,
    };
    catalog.categories.push(category);
    return ok(category);
  },

  async createCatalogRequest(input = {}) {
    await wait();
    ensureStaff();
    return ok(createRequest(input));
  },

  async getCatalogRequests() {
    await wait();
    ensureSignedIn();
    const visibleRequests =
      activeUser.role === "Admin"
        ? requests
        : requests.filter((request) => request.requestedById === activeUser.id);
    return ok(visibleRequests);
  },

  async updateCatalogRequest(id, input = {}) {
    await wait();
    ensureAdmin();
    const request = requests.find((entry) => entry.id === id);
    if (!request) fail(404, "Catalog request not found.");
    if (request.status !== "Pending") {
      fail(422, "This catalog request has already been processed.");
    }

    const action = String(input.action ?? input.status ?? "").toLowerCase();
    if (action === "approve") {
      const itemName = String(input.itemName ?? request.itemName).trim();
      if (!itemName) fail(422, "Item name is required for approval.");

      if (request.itemId) {
        const item = catalog.items.find((entry) => entry.id === request.itemId);
        if (!item) fail(404, "Requested catalog item no longer exists.");
        const specification = requireText(
          input.specification ?? request.specification,
          "Specification",
        );
        if (
          item.specifications.some(
            (entry) => normalized(entry) === normalized(specification),
          )
        ) {
          fail(422, `Specification "${specification}" already exists.`);
        }
        if (input.itemName != null && itemName !== item.name) {
          assertUniqueItem(item.categoryId, itemName, item.id);
        }
        item.specifications.push(specification);
        if (input.itemName != null && itemName !== item.name) {
          item.name = itemName;
        }
      } else {
        addCatalogItem({
          categoryId: request.categoryId,
          name: itemName,
          specifications: [
            ...(Array.isArray(input.specifications) ? input.specifications : []),
            ...(input.specification ?? request.specification
              ? [input.specification ?? request.specification]
              : []),
          ],
        });
      }
      request.itemName = itemName;
      request.status = "Approved";
      request.processedBy = activeUser.name;
      request.processedAt = new Date().toISOString();
      return ok(request);
    }
    if (action === "reject") {
      request.status = "Rejected";
      request.reason = String(input.reason ?? "").trim();
      request.processedBy = activeUser.name;
      request.processedAt = new Date().toISOString();
      return ok(request);
    }
    fail(422, "Request action must be approve or reject.");
  },
};