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

function notifyCatalogRequestsChanged() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("catalog-requests-updated"));
  }
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
  { id: "cat-mattresses", name: "Mattresses" },
  { id: "cat-home-boarding", name: "Home & Boarding" },
  { id: "cat-yarns", name: "Yarns" },
  { id: "cat-school-uniforms", name: "School Uniforms" },
  { id: "cat-maasai-shuka", name: "Maasai Shuka" },
  { id: "cat-bedsheets", name: "Bedsheets" },
  { id: "cat-blankets", name: "Blankets" },
  { id: "cat-gumboots", name: "Gumboots" },
  { id: "cat-raincoats", name: "Raincoats" },
  { id: "cat-duvets", name: "Duvets" },
];

const catalog = {
  categories,
  items: [
    {
      id: "item-vivo-mattress",
      categoryId: "cat-mattresses",
      name: "Vivo Mattress",
      specifications: ["72*60*6", "72*60*8", "72*60*10", "75*60*6", "78*72*8"],
      active: true,
    },
    {
      id: "item-furahia-mattress",
      categoryId: "cat-mattresses",
      name: "Furahia Mattress",
      specifications: ["72*60*6", "72*60*8", "72*60*10", "75*60*6", "78*72*8"],
      active: true,
    },
    {
      id: "item-morning-glory-mattress",
      categoryId: "cat-mattresses",
      name: "Morning Glory Mattress",
      specifications: ["72*60*6", "72*60*8", "72*60*10", "75*60*6", "78*72*8"],
      active: true,
    },
    {
      id: "item-tufffoam-mattress",
      categoryId: "cat-mattresses",
      name: "Tufffoam Mattress",
      specifications: ["72*60*6", "72*60*8", "72*60*10", "75*60*6", "78*72*8"],
      active: true,
    },
    {
      id: "item-bombil-mattress",
      categoryId: "cat-mattresses",
      name: "Bombil Mattress",
      specifications: ["72*60*6", "72*60*8", "72*60*10", "75*60*6", "78*72*8"],
      active: true,
    },
    {
      id: "item-standard-foam-mattress",
      categoryId: "cat-mattresses",
      name: "Standard Foam Mattress",
      specifications: ["72*60*6", "72*60*8", "72*60*10", "75*60*6", "78*72*8"],
      active: true,
    },
    {
      id: "item-pillow",
      categoryId: "cat-home-boarding",
      name: "Pillow",
      specifications: ["Standard", "King Size"],
      active: true,
    },
    {
      id: "item-pillowcase",
      categoryId: "cat-home-boarding",
      name: "Pillowcase",
      specifications: ["Standard", "King Size"],
      active: true,
    },
    {
      id: "item-mattress-protector",
      categoryId: "cat-home-boarding",
      name: "Mattress Protector",
      specifications: ["Single", "Double", "Queen", "King"],
      active: true,
    },
    {
      id: "item-mosquito-net",
      categoryId: "cat-home-boarding",
      name: "Mosquito Net",
      specifications: ["Single", "Double", "Queen", "King"],
      active: true,
    },
    {
      id: "item-bath-towel",
      categoryId: "cat-home-boarding",
      name: "Bath Towel",
      specifications: ["Small", "Medium", "Large"],
      active: true,
    },
    {
      id: "item-school-trunk",
      categoryId: "cat-home-boarding",
      name: "School Trunk",
      specifications: ["Small", "Medium", "Large"],
      active: true,
    },
    {
      id: "item-basin",
      categoryId: "cat-home-boarding",
      name: "Plastic Basin",
      specifications: ["Small", "Medium", "Large"],
      active: true,
    },
    {
      id: "item-knitting-yarn",
      categoryId: "cat-yarns",
      name: "Knitting Yarn",
      specifications: ["100 g", "200 g", "500 g"],
      active: true,
    },
    {
      id: "item-acrylic-yarn",
      categoryId: "cat-yarns",
      name: "Acrylic Yarn",
      specifications: ["100 g", "200 g", "500 g"],
      active: true,
    },
    {
      id: "item-cotton-yarn",
      categoryId: "cat-yarns",
      name: "Cotton Yarn",
      specifications: ["100 g", "200 g", "500 g"],
      active: true,
    },
    {
      id: "item-sewing-thread",
      categoryId: "cat-yarns",
      name: "Sewing Thread",
      specifications: ["Small Reel", "Large Reel", "Pack of 12"],
      active: true,
    },
    {
      id: "item-school-shirt",
      categoryId: "cat-school-uniforms",
      name: "School Shirt",
      specifications: ["20", "22", "24", "26", "28", "30", "32", "34", "36", "38", "40"],
      active: true,
    },
    {
      id: "item-school-trousers",
      categoryId: "cat-school-uniforms",
      name: "School Trousers",
      specifications: ["20", "22", "24", "26", "28", "30", "32", "34", "36", "38", "40"],
      active: true,
    },
    {
      id: "item-school-skirt",
      categoryId: "cat-school-uniforms",
      name: "School Skirt",
      specifications: ["20", "22", "24", "26", "28", "30", "32", "34", "36", "38", "40"],
      active: true,
    },
    {
      id: "item-school-sweater",
      categoryId: "cat-school-uniforms",
      name: "School Sweater",
      specifications: ["XS", "S", "M", "L", "XL"],
      active: true,
    },
    {
      id: "item-school-socks",
      categoryId: "cat-school-uniforms",
      name: "School Socks",
      specifications: ["Small", "Medium", "Large"],
      active: true,
    },
    {
      id: "item-school-tie",
      categoryId: "cat-school-uniforms",
      name: "School Tie",
      specifications: ["Standard"],
      active: true,
    },
    {
      id: "item-maasai-shuka",
      categoryId: "cat-maasai-shuka",
      name: "Maasai Shuka",
      specifications: ["Standard", "Large"],
      active: true,
    },
    {
      id: "item-bedsheet-set",
      categoryId: "cat-bedsheets",
      name: "Bedsheet Set",
      specifications: ["3x6", "4x6", "5x6", "6x6"],
      active: true,
    },
    {
      id: "item-flat-bedsheet",
      categoryId: "cat-bedsheets",
      name: "Flat Bedsheet",
      specifications: ["3x6", "4x6", "5x6", "6x6"],
      active: true,
    },
    {
      id: "item-fitted-bedsheet",
      categoryId: "cat-bedsheets",
      name: "Fitted Bedsheet",
      specifications: ["3x6", "4x6", "5x6", "6x6"],
      active: true,
    },
    {
      id: "item-fleece-blanket",
      categoryId: "cat-blankets",
      name: "Fleece Blanket",
      specifications: ["Single", "Double", "Queen", "King"],
      active: true,
    },
    {
      id: "item-wool-blanket",
      categoryId: "cat-blankets",
      name: "Wool Blanket",
      specifications: ["Single", "Double", "Queen", "King"],
      active: true,
    },
    {
      id: "item-gumboots",
      categoryId: "cat-gumboots",
      name: "Gumboots",
      specifications: ["36", "37", "38", "39", "40", "41", "42", "43", "44", "45"],
      active: true,
    },
    {
      id: "item-raincoat",
      categoryId: "cat-raincoats",
      name: "Raincoat",
      specifications: ["S", "M", "L", "XL", "XXL"],
      active: true,
    },
    {
      id: "item-rain-suit",
      categoryId: "cat-raincoats",
      name: "Rain Suit",
      specifications: ["S", "M", "L", "XL", "XXL"],
      active: true,
    },
    {
      id: "item-duvet-set",
      categoryId: "cat-duvets",
      name: "Duvet Set",
      specifications: ["Single", "Double", "Queen", "King"],
      active: true,
    },
    {
      id: "item-duvet-inner",
      categoryId: "cat-duvets",
      name: "Duvet Inner",
      specifications: ["Single", "Double", "Queen", "King"],
      active: true,
    },
  ],
};

const seedRecords = [
  {
    id: "INV-1048",
    date: "2026-03-10",
    category: "Mattresses",
    item: "Vivo Mattress",
    size: "72*60*6",
    quantityIn: 24,
    quantityOut: null,
    details: "New mattress stock received",
    addedBy: "Grace Wanjiku",
    createdAt: "2026-03-10T08:42:00.000Z",
    modifiedBy: "Grace Wanjiku",
    status: "Locked",
  },
  {
    id: "INV-1047",
    date: "2026-03-09",
    category: "Mattresses",
    item: "Furahia Mattress",
    size: "72*60*8",
    quantityIn: null,
    quantityOut: 2,
    details: "Wholesale mattress order",
    addedBy: "Samuel Kiptoo",
    createdAt: "2026-03-09T15:18:00.000Z",
    modifiedBy: "Samuel Kiptoo",
    status: "Locked",
  },
  {
    id: "INV-1046",
    date: "2026-03-09",
    category: "Mattresses",
    item: "Morning Glory Mattress",
    size: "75*60*6",
    quantityIn: 12,
    quantityOut: null,
    details: "Supplier delivery",
    addedBy: "Grace Wanjiku",
    createdAt: "2026-03-09T10:05:00.000Z",
    modifiedBy: "Grace Wanjiku",
    status: "Saved",
  },
  {
    id: "INV-1045",
    date: "2026-03-08",
    category: "Mattresses",
    item: "Tufffoam Mattress",
    size: "78*72*8",
    quantityIn: 8,
    quantityOut: null,
    details: "Restock",
    addedBy: "Daniel Otieno",
    createdAt: "2026-03-08T16:32:00.000Z",
    modifiedBy: "Daniel Otieno",
    status: "Locked",
  },
  {
    id: "INV-1044",
    date: "2026-03-07",
    category: "Mattresses",
    item: "Bombil Mattress",
    size: "72*60*10",
    quantityIn: 6,
    quantityOut: null,
    details: "Premium mattress stock",
    addedBy: "Samuel Kiptoo",
    createdAt: "2026-03-07T09:21:00.000Z",
    modifiedBy: "Samuel Kiptoo",
    status: "Saved",
  },
  {
    id: "INV-1043",
    date: "2026-03-06",
    category: "Home & Boarding",
    item: "Pillow",
    size: "Standard",
    quantityIn: null,
    quantityOut: 18,
    details: "Boarding school order",
    addedBy: "Grace Wanjiku",
    createdAt: "2026-03-06T13:12:00.000Z",
    modifiedBy: "Grace Wanjiku",
    status: "Locked",
  },
  {
    id: "INV-1042",
    date: "2026-03-05",
    category: "Yarns",
    item: "Knitting Yarn",
    size: "100 g",
    quantityIn: 100,
    quantityOut: null,
    details: "Assorted yarn delivery",
    addedBy: "Daniel Otieno",
    createdAt: "2026-03-05T11:47:00.000Z",
    modifiedBy: "Daniel Otieno",
    status: "Saved",
  },
  {
    id: "INV-1041",
    date: "2026-03-04",
    category: "School Uniforms",
    item: "School Shirt",
    size: "32",
    quantityIn: 36,
    quantityOut: null,
    details: "Uniform order received",
    addedBy: "Grace Wanjiku",
    createdAt: "2026-03-04T08:10:00.000Z",
    modifiedBy: "Admin User",
    status: "Locked",
  },
  {
    id: "INV-1040",
    date: "2026-03-03",
    category: "Maasai Shuka",
    item: "Maasai Shuka",
    size: "Standard",
    quantityIn: 40,
    quantityOut: null,
    details: "Traditional shuka stock",
    addedBy: "Samuel Kiptoo",
    createdAt: "2026-03-03T14:24:00.000Z",
    modifiedBy: "Samuel Kiptoo",
    status: "Saved",
  },
  {
    id: "INV-1039",
    date: "2026-03-02",
    category: "Bedsheets",
    item: "Bedsheet Set",
    size: "6x6",
    quantityIn: 20,
    quantityOut: null,
    details: "King size bedding sets",
    addedBy: "Daniel Otieno",
    createdAt: "2026-03-02T10:15:00.000Z",
    modifiedBy: "Daniel Otieno",
    status: "Locked",
  },
  {
    id: "INV-1038",
    date: "2026-03-01",
    category: "Blankets",
    item: "Fleece Blanket",
    size: "Double",
    quantityIn: null,
    quantityOut: 5,
    details: "Retail dispatch",
    addedBy: "Grace Wanjiku",
    createdAt: "2026-03-01T12:30:00.000Z",
    modifiedBy: "Grace Wanjiku",
    status: "Saved",
  },
  {
    id: "INV-1037",
    date: "2026-02-28",
    category: "Gumboots",
    item: "Gumboots",
    size: "42",
    quantityIn: 30,
    quantityOut: null,
    details: "Rain season footwear restock",
    addedBy: "Samuel Kiptoo",
    createdAt: "2026-02-28T09:40:00.000Z",
    modifiedBy: "Samuel Kiptoo",
    status: "Locked",
  },
  {
    id: "INV-1036",
    date: "2026-02-27",
    category: "Raincoats",
    item: "Raincoat",
    size: "L",
    quantityIn: 25,
    quantityOut: null,
    details: "Adult rainwear delivery",
    addedBy: "Daniel Otieno",
    createdAt: "2026-02-27T13:05:00.000Z",
    modifiedBy: "Daniel Otieno",
    status: "Saved",
  },
  {
    id: "INV-1035",
    date: "2026-02-26",
    category: "Duvets",
    item: "Duvet Set",
    size: "Queen",
    quantityIn: 16,
    quantityOut: null,
    details: "Bedding stock received",
    addedBy: "Grace Wanjiku",
    createdAt: "2026-02-26T08:55:00.000Z",
    modifiedBy: "Grace Wanjiku",
    status: "Locked",
  },
  {
    id: "INV-1034",
    date: "2026-02-25",
    category: "Home & Boarding",
    item: "School Trunk",
    size: "Large",
    quantityIn: null,
    quantityOut: 4,
    details: "Boarding essentials order",
    addedBy: "Samuel Kiptoo",
    createdAt: "2026-02-25T14:24:00.000Z",
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
    createdAt: "2025-01-06T09:00:00.000Z",
  },
  {
    id: 2,
    name: "Grace Wanjiku",
    email: "grace@gosrani.co.ke",
    role: "User",
    status: "Active",
    password: "user123",
    createdAt: "2025-02-14T08:30:00.000Z",
  },
  {
    id: 3,
    name: "Samuel Kiptoo",
    email: "samuel@gosrani.co.ke",
    role: "User",
    status: "Active",
    password: "user123",
    createdAt: "2025-04-03T10:15:00.000Z",
  },
  {
    id: 4,
    name: "Daniel Otieno",
    email: "daniel@gosrani.co.ke",
    role: "User",
    status: "Inactive",
    password: "user123",
    createdAt: "2025-07-21T11:45:00.000Z",
  },
];

let records = seedRecords;
let users = seedUsers;
let requests = [
  {
    id: "REQ-1001",
    categoryId: "cat-home-boarding",
    category: "Home & Boarding",
    itemId: null,
    itemName: "Mosquito Net",
    specification: "Single",
    note: "Frequently requested by the boarding team",
    requestedById: 2,
    requestedBy: "Grace Wanjiku",
    status: "Pending",
    createdAt: "2026-03-11T09:20:00.000Z",
  },
  {
    id: "REQ-1002",
    categoryId: "cat-yarns",
    category: "Yarns",
    itemId: "item-knitting-yarn",
    itemName: "Knitting Yarn",
    specification: "250 g",
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

function generateTemporaryPassword() {
  const characters =
    "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$";
  const values = new Uint32Array(12);
  globalThis.crypto.getRandomValues(values);
  return `Gw-${Array.from(values, (value) => characters[value % characters.length]).join("")}`;
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
  const requestType =
    input.requestType ??
    (input.categoryName
      ? "category"
      : input.itemId
        ? "specification"
        : "product");
  if (!["category", "product", "specification"].includes(requestType)) {
    fail(422, "Choose a valid catalog request type.");
  }

  if (requestType === "category") {
    const categoryName = requireText(input.categoryName, "Category name");
    if (
      catalog.categories.some(
        (entry) => normalized(entry.name) === normalized(categoryName),
      )
    ) {
      fail(422, "A category with this name already exists.");
    }
    if (
      requests.some(
        (request) =>
          request.status === "Pending" &&
          request.requestType === "category" &&
          normalized(request.categoryName) === normalized(categoryName),
      )
    ) {
      fail(422, "A matching category request is already pending.");
    }

    const request = {
      id: createId("REQ", nextRequestId++),
      requestType,
      categoryId: null,
      category: categoryName,
      categoryName,
      itemId: null,
      itemName: "",
      specification: "",
      note: String(input.note ?? "").trim(),
      requestedById: activeUser.id,
      requestedBy: activeUser.name,
      status: "Pending",
      createdAt: new Date().toISOString(),
    };
    requests.unshift(request);
    notifyCatalogRequestsChanged();
    return request;
  }

  const category = getCategory(input.categoryId ?? input.category);
  if (!category) fail(422, "Choose a valid catalog category.");

  const existingItem = input.itemId
    ? getItem(input.itemId, category.id)
    : requestType === "specification"
      ? getItem(input.itemName, category.id)
      : null;
  const itemName = requireText(
    existingItem?.name ?? input.itemName,
    requestType === "product" ? "Product name" : "Item name",
  );
  const specification = String(
    input.specification ?? input.size ?? "",
  ).trim();

  if (requestType === "product" && getItem(itemName, category.id)) {
    fail(422, "This product already exists; request a missing specification instead.");
  }
  if (!specification) {
    fail(
      422,
      requestType === "product"
        ? "Provide an initial specification for the new product."
        : "Provide the missing specification.",
    );
  }
  if (requestType === "specification" && !existingItem) {
    fail(422, "Choose a valid existing catalog product.");
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
      (request.requestType ??
        (request.itemId ? "specification" : "product")) === requestType &&
      request.categoryId === category.id &&
      normalized(request.itemName) === normalized(itemName) &&
      normalized(request.specification) === normalized(specification),
  );
  if (duplicateRequest) {
    fail(422, "A matching catalog request is already pending.");
  }

  const request = {
    id: createId("REQ", nextRequestId++),
    requestType,
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
  notifyCatalogRequestsChanged();
  return request;
}

function addCatalogCategory(name) {
  const categoryName = requireText(name, "Category name");
  if (
    catalog.categories.some(
      (category) => normalized(category.name) === normalized(categoryName),
    )
  ) {
    fail(422, "A category with this name already exists.");
  }
  const category = {
    id: createId("cat-new", nextCategoryId++),
    name: categoryName,
  };
  catalog.categories.push(category);
  return category;
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
    if (!user) fail(401, "Invalid email or password.");

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
    ensureAdmin();
    const query = String(question ?? "").trim().toLocaleLowerCase();
    if (!query) fail(422, "Ask a question first.");
    if (query.length > 500) {
      fail(422, "Keep your question to 500 characters or fewer.");
    }

    const item = [...catalog.items]
      .sort((left, right) => right.name.length - left.name.length)
      .find((entry) => query.includes(normalized(entry.name)));
    const specification = item
      ? [...item.specifications]
          .sort((left, right) => right.length - left.length)
          .find((value) => query.includes(normalized(value)))
      : null;
    const category = [...catalog.categories]
      .sort((left, right) => right.name.length - left.name.length)
      .find((entry) => query.includes(normalized(entry.name)));
    const keywordMatch = query.match(
      /\bdetails?\s+(?:mention|mentions|contain|contains|say|says)\s+(.+)|\bmention\s+(.+)/,
    );
    const keyword = (keywordMatch?.[1] ?? keywordMatch?.[2])
      ?.replace(/[?.!,;:]+$/g, "")
      .trim();
    const direction = /\b(received|receive|incoming|inbound)\b/.test(query)
      ? "in"
      : /\b(went out|go out|outgoing|outbound|issued|dispatch|dispatched|sold)\b/.test(
            query,
          ) || /\bout\b/.test(query)
        ? "out"
        : null;
    const wantsStock = /\b(stock|balance|remaining|left)\b/.test(query);
    const today = formatToday();
    const shiftDate = (value, days) => {
      const date = new Date(`${value}T00:00:00.000Z`);
      date.setUTCDate(date.getUTCDate() + days);
      return date.toISOString().slice(0, 10);
    };

    let from = null;
    let to = null;
    const explicitRange =
      query.match(/\bfrom\s+(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})\b/) ??
      query.match(
        /\bbetween\s+(\d{4}-\d{2}-\d{2})\s+and\s+(\d{4}-\d{2}-\d{2})\b/,
      );
    if (explicitRange) {
      [, from, to] = explicitRange;
      const isValidDate = (value) => {
        const date = new Date(`${value}T00:00:00.000Z`);
        return (
          !Number.isNaN(date.getTime()) &&
          date.toISOString().slice(0, 10) === value
        );
      };
      if (!isValidDate(from) || !isValidDate(to) || from > to) {
        fail(422, "Enter a valid date range in YYYY-MM-DD format.");
      }
    } else if (/\byesterday\b/.test(query)) {
      from = shiftDate(today, -1);
      to = from;
    } else if (/\btoday\b/.test(query)) {
      from = today;
      to = today;
    } else if (/\bthis week\b/.test(query)) {
      const day = new Date(`${today}T00:00:00.000Z`).getUTCDay();
      from = shiftDate(today, -((day + 6) % 7));
      to = today;
    }

    const hasStructuredFilter = Boolean(
      item || category || keyword || direction || from || to,
    );
    const meaningfulTerms = query
      .split(/\s+/)
      .map((term) => term.replace(/^[^a-z0-9]+|[^a-z0-9]+$/g, ""))
      .filter(
        (term) =>
          term.length > 2 &&
          ![
            "how",
            "much",
            "what",
            "show",
            "everything",
            "find",
            "entries",
            "where",
            "the",
            "details",
            "mention",
            "mentions",
            "received",
            "receive",
            "incoming",
            "inbound",
            "went",
            "out",
            "today",
            "yesterday",
            "this",
            "week",
            "stock",
            "balance",
            "remaining",
            "left",
            "from",
            "between",
            "and",
            "with",
            "for",
            "in",
            "on",
            "of",
            "is",
          ].includes(term),
      );

    let matchingRecords = records.filter((record) => {
      if (item && !itemMatchesRecord(item, record)) return false;
      if (specification && normalized(record.size) !== normalized(specification)) {
        return false;
      }
      if (category && normalized(record.category) !== normalized(category.name)) {
        return false;
      }
      if (keyword && !normalized(record.details).includes(normalized(keyword))) {
        return false;
      }
      if (direction === "in" && (record.quantityIn ?? 0) <= 0) return false;
      if (direction === "out" && (record.quantityOut ?? 0) <= 0) return false;
      if (from && record.date < from) return false;
      if (to && record.date > to) return false;
      if (!hasStructuredFilter) {
        const recordText = normalized(
          `${record.category} ${record.item} ${record.size} ${record.details}`,
        );
        if (
          meaningfulTerms.length > 0 &&
          !meaningfulTerms.some((term) => recordText.includes(term))
        ) {
          return false;
        }
      }
      return true;
    }).sort((left, right) => right.date.localeCompare(left.date));

    const totalMatches = matchingRecords.length;
    const resultRecords = matchingRecords.slice(0, 5);
    const searchQuery = keyword || item?.name || category?.name || query;
    let answer = totalMatches
      ? `I found ${totalMatches} matching inventory ${
          totalMatches === 1 ? "record" : "records"
        }.`
      : "I couldn't find any matching records.";

    if (wantsStock && item) {
      const balance = matchingRecords.reduce(
        (total, record) =>
          total + (record.quantityIn ?? 0) - (record.quantityOut ?? 0),
        0,
      );
      answer = specification
        ? `Recorded stock for ${item.name} (${specification}) is ${balance}.`
        : `Recorded stock for ${item.name} is ${balance} across its specifications.`;
    } else if (totalMatches > 5) {
      answer = `I found ${totalMatches} matching inventory records. Showing the first 5.`;
    }

    return ok({
      answer,
      records: resultRecords,
      totalMatches,
      searchQuery,
    });
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
      password: generateTemporaryPassword(),
      createdAt: new Date().toISOString(),
    };
    users = [...users, user];
    return ok({
      user: publicUser(user),
      temporaryPassword: user.password,
    });
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

    const updatedRole = changes.role ?? user.role;
    const updatedStatus = changes.status ?? user.status;
    if (user.role === "Admin" && user.status === "Active") {
      const activeAdmins = users.filter(
        (entry) => entry.role === "Admin" && entry.status === "Active",
      );
      if (
        activeAdmins.length <= 1 &&
        (updatedRole !== "Admin" || updatedStatus !== "Active")
      ) {
        fail(422, "At least one active administrator must remain.");
      }
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
    return ok(addCatalogCategory(input.name));
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
      const requestType =
        request.requestType ?? (request.itemId ? "specification" : "product");
      if (requestType === "category") {
        const category = addCatalogCategory(
          input.categoryName ?? request.categoryName ?? request.category,
        );
        request.categoryId = category.id;
        request.category = category.name;
        request.categoryName = category.name;
        request.status = "Approved";
        request.processedBy = activeUser.name;
        request.processedAt = new Date().toISOString();
        notifyCatalogRequestsChanged();
        return ok(request);
      }

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
      notifyCatalogRequestsChanged();
      return ok(request);
    }
    if (action === "reject") {
      request.status = "Rejected";
      request.reason = String(input.reason ?? "").trim();
      request.processedBy = activeUser.name;
      request.processedAt = new Date().toISOString();
      notifyCatalogRequestsChanged();
      return ok(request);
    }
    fail(422, "Request action must be approve or reject.");
  },
};