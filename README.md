# Gosrani Inventory Tracker

**Gosrani Wholesalers Limited, Eldoret, Kenya**

A role-based inventory system for recording stock movements, reviewing entries
before saving, and looking up inventory with a read-only assistant. The planned
interface uses the company colours (red and black) and supports light and dark
themes.

> The frontend uses the Flask API for authentication and application data.
> Inventory, catalog, user, and request changes are stored in the configured
> database; no sample login or in-memory application records are used.

## Contents

- [Planned features](#planned-features)
- [Roles and permissions](#roles-and-permissions)
- [Technology](#technology)
- [Getting started](#getting-started)
- [Project structure](#project-structure)
- [Routes and screens](#routes-and-screens)
- [Entry review and validation](#entry-review-and-validation)
- [Design and accessibility](#design-and-accessibility)
- [Planned API contract](#planned-api-contract)
- [Connecting the frontend and backend](#connecting-the-frontend-and-backend)
- [Backend security requirements](#backend-security-requirements)
- [Prototype limitations and open questions](#prototype-limitations-and-open-questions)
- [Deployment notes](#deployment-notes)

## Planned features

- Record stock movements with six fields: **Date, Item, Size, Quantity In,
  Quantity Out, Details**.
- Add one entry or multiple rows at once, with controls to add, remove, and
  duplicate rows.
- Review entered data before saving. Saving is disabled until the user confirms
  the reviewed information.
- Keep saved entries protected from changes by staff. Admin edits also go
  through review and show changed fields.
- Search, filter, sort, and paginate inventory records.
- Provide an AI assistant for read-only inventory lookups. Replies can include
  links to matching records and must remind users to verify important details.
- Let Admins manage users, edit and delete records, and lock records.
- Support light and dark themes, loading/empty/error states, and a friendly
  permission-denied state.
- Display dates in Kenyan `DD/MM/YYYY` format.
- Keep the interface focused on data entry and lookup; charts and statistics
  are out of scope.

## Roles and permissions

| Capability | Admin | User (staff) |
| --- | :---: | :---: |
| Sign in and view inventory | Yes | Yes |
| Add and review entries | Yes | Yes |
| Edit or delete saved entries | Yes | No |
| Manually lock an entry | Yes | No |
| Use the read-only assistant | Yes | No |
| Manage users | Yes | No |

Entries created by staff should be locked immediately. Admin-created entries
may remain saved and can be locked later. Hide Admin-only actions from staff in
the interface, but enforce all permissions again in the backend. UI checks are
not a security boundary.

## Technology

| Layer | Technology |
| --- | --- |
| Frontend | React with JavaScript and JSX (no TypeScript) |
| Routing | React Router |
| Build tool | Vite |
| Backend | Flask REST API (Python) |
| Dependency management | npm for frontend; Pipenv for backend |
| Data persistence | SQLAlchemy with SQLite for local development and PostgreSQL for production |

The frontend package manifest currently specifies React 18, React Router 6,
and Vite 6. The codebase is JavaScript: frontend source uses `.js` and `.jsx`,
and the Vite config is `vite.config.js`.

## Getting started

### Prerequisites

- Node.js and npm
- Python and Pipenv

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Copy `.env.example` to `.env.local` if the Flask API is not at
`http://localhost:5000/api`, then set `VITE_API_BASE_URL`. The dev server runs
at `http://localhost:8443`.

The frontend uses npm. Running `npm install` creates `package-lock.json`; commit
that file and use `npm ci` for clean, reproducible installs afterward.

Available npm scripts:

```bash
npm run dev      # Start the Vite development server
npm run build    # Create a production build in dist/
npm run preview  # Preview the production build locally
```

### Backend

```bash
cd backend
pipenv install
```

Create `backend/.env` from `.env.example`, set `SEED_ADMIN_EMAIL` and
`SEED_ADMIN_PASSWORD` (at least 6 characters), and then run:

```bash
pipenv run flask --app app db upgrade
pipenv run flask --app app seed
pipenv run flask --app app run --host 0.0.0.0 --port 5000
```

To create additional User accounts during seeding, repeat
`--user-email user@example.com` for each one. The seed command generates their
passwords and prints each newly created User's one-time login credentials.

The default local database is `backend/instance/gosrani.db`. Set
`CORS_ORIGINS` to a comma-separated list of exact frontend origins; the
development defaults match the Vite port. Production should use PostgreSQL and
the production cookie/TLS settings described in [backend/docs/DATABASE.md](backend/docs/DATABASE.md).

## Project structure

```text
.
├── README.md
├── .gitignore
├── frontend/
│   ├── .gitignore
│   ├── index.html
│   ├── package.json
│   ├── public/
│   │   └── favicon.svg
│   └── src/
│       ├── app/
│       │   ├── App.jsx
│       │   └── routes.jsx
│       ├── components/
│       │   ├── AppLayout.jsx
│       │   ├── AssistantChat.jsx
│       │   ├── ThemeToggle.jsx
│       │   └── ui.jsx
│       ├── context/
│       │   ├── AuthContext.jsx
│       │   └── ThemeContext.jsx
│       ├── hooks/
│       │   └── useApi.js
│       ├── pages/
│       │   ├── AssistantPage.jsx
│       │   ├── EntryDetailPage.jsx
│       │   ├── EntryFormPage.jsx
│       │   ├── InventoryPage.jsx
│       │   ├── LoginPage.jsx
│       │   ├── NotFoundPage.jsx
│       │   └── UsersPage.jsx
│       ├── services/
│       │   └── api.js
│       ├── utils/
│       │   └── format.js
│       ├── index.css
│       └── main.jsx
├── backend/
│   ├── .env.example
│   ├── .gitignore
│   ├── Pipfile
│   ├── requirements.txt
│   ├── run.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── assistant.py
│   │   ├── auth.py
│   │   ├── inventory.py
│   │   ├── models.py
│   │   ├── permissions.py
│   │   ├── users.py
│   │   └── validators.py
│   └── instance/
│       └── .gitkeep
```

The intended architecture keeps data access behind `frontend/src/services/api.js`.
Pages and components should call the API service rather than making network
requests directly.

## Routes and screens

| Path | Screen | Access |
| --- | --- | --- |
| `/login` | Sign in | Public |
| `/` | Redirect to `/inventory` | Signed in |
| `/inventory` | Inventory list, search, filters, sorting, pagination | Signed in |
| `/inventory/new` | Add one or more entries and review before saving | Signed in |
| `/inventory/:id` | Record details and audit information | Signed in |
| `/inventory/:id/edit` | Edit and review a saved record | Admin |
| `/assistant` | Full-page assistant | Admin |
| `/users` | User management | Admin |
| `*` | Not-found page | Signed in |

The assistant should also be available as a slide-over panel from Admin screens.

## Entry review and validation

The intended entry workflow is **Form → Review → Confirm & Save**. Review is
read-only, displays warnings, and requires explicit user confirmation. If
saving fails, preserve the entered data so the user can retry. Admin edits use
the same review flow and show a before/after list of changed fields.

Client-side validation should require a date and item, at least one of Quantity
In or Quantity Out, and whole non-negative quantities. Future dates may display
a hint without blocking review.

Review warnings should not block saving, but should flag values for the user to
check, including:

- unusually large quantities;
- both Quantity In and Quantity Out being supplied;
- Quantity Out exceeding current stock;
- future or very old dates; and
- item or size values that do not match known entries.

The backend must repeat validation and calculate stock-based warnings from
persisted records. Client-side checks are only for usability.

## Design and accessibility

- Use red as the primary brand colour and black as the secondary colour.
- Keep the sidebar near-black in both themes and use red for active navigation
  and primary actions.
- Define theme colours as CSS tokens and use them consistently.
- Format dates as `DD/MM/YYYY`.
- Provide visible keyboard focus, accessible names for icon-only buttons,
  appropriate live regions for chat updates, and reduced-motion support.
- On narrow screens, present navigation as a slide-in drawer.
- Use responsive CSS Grid and Flexbox layouts, switching the application shell,
  page headers, and inventory filters to compact layouts on narrow screens.
  Keep wide inventory and user tables inside horizontally scrollable panels.

## Planned API contract

Frontend data access is intended to be implemented in
`frontend/src/services/api.js`. Successful responses use a `data` envelope and
list responses may include pagination metadata:

```json
{
  "data": [],
  "meta": { "page": 1, "limit": 6, "total": 0, "pages": 0 }
}
```

Errors should return a JSON `message` and an appropriate HTTP status. The
frontend should handle `401` for invalid or expired sessions, `403` for
permission errors, `404` for missing records, and `422` for validation errors.

| Operation | Planned endpoint | Access |
| --- | --- | --- |
| Login | `POST /api/auth/login` | Public |
| Current user | `GET /api/auth/me` | Signed in |
| List inventory | `GET /api/inventory` | Signed in |
| Get inventory record | `GET /api/inventory/<id>` | Signed in |
| Validate entry rows | `POST /api/inventory/validate` | Signed in |
| Create entry rows | `POST /api/inventory` | Signed in |
| Update or lock a record | `PUT /api/inventory/<id>` | Admin |
| Delete a record | `DELETE /api/inventory/<id>` | Admin |
| Query assistant | `POST /api/assistant/query` | Signed in, read-only |
| List or manage users | `/api/users` | Admin |

Inventory list parameters should include `search`, `item`, `size`, inclusive ISO
date bounds (`from`, `to`), date sort order (`asc` or `desc`), `page`, and
`limit`.

An inventory record contains `id`, `date`, `item`, `size`, `quantityIn`,
`quantityOut`, `details`, `addedBy`, `createdAt`, `modifiedBy`, and `status`.
Dates are stored as ISO `YYYY-MM-DD`; quantities are integers or `null`;
statuses are `Saved` or `Locked`. System fields must be generated by the
backend, not trusted from request data.

The validation endpoint should return normalised rows and per-row warning
flags. The assistant endpoint should return `{ "data": { "answer": "...",
"records": [] } }`. For stock questions, calculate total Quantity In minus
total Quantity Out for the requested item and size.

## Connecting the frontend and backend

When implementing the real API:

1. Implement the Flask endpoints following the contract above.
2. Replace the mock/data layer in `frontend/src/services/api.js` with `fetch`
   calls while keeping the API function names and response shapes stable.
3. Send the stored authentication token with protected requests.
4. On application load, validate a stored session with `/api/auth/me`; clear
   invalid sessions and redirect to sign-in after `401` responses.
5. Load item and size catalog values from the backend rather than hard-coding
   them in the frontend.
6. Remove any demo credentials or mock-only login behavior when real
   authentication is introduced.
7. Configure a Vite `/api` development proxy or narrowly allow the frontend
   origin in Flask CORS settings.

## Backend security requirements

The Flask backend must enforce authorization and validation independently of
the frontend:

1. Require Admin privileges for update, delete, lock, and user-management
   endpoints.
2. Prevent staff from changing or deleting saved records through direct API
   requests.
3. Validate every record server-side, including required fields, integer
   non-negative quantities, and the requirement that at least one quantity is
   present.
4. Generate record IDs, creator/modifier information, timestamps, and status
   on the server. Never accept these system fields from staff input.
5. Hash passwords with a suitable password-hashing function and use
   appropriately short-lived JWTs.
6. Maintain an audit trail for record creation, changes, locks, and deletion.
7. Keep assistant operations read-only. Do not let a language model execute
   arbitrary SQL against the live database; use constrained, safe query
   functions instead.

## Prototype limitations and open questions

The application is not yet implemented, so persistence, authentication, API
behavior, assistant responses, review warnings, automated tests, and deployment
are not available yet. Decide the following before completing the backend:

1. Should inventory display a running stock balance per item and size?
2. Should users select from fixed item and size lists or be allowed to add new
   values?
3. Should an Admin edit preserve a record's existing Locked status?
4. Should deletion be permanent or soft-deletion with retained audit history?
5. How should new users receive initial credentials (invite, temporary
   password, or reset link)?
6. Are entries with both Quantity In and Quantity Out legitimate adjustments,
   or should they be rejected?
7. Which database and hosting environment will be used?

## Deployment notes

- The frontend is intended to be a single-page application. Configure the web
  server to serve `index.html` for client-side routes such as
  `/inventory/<id>`.
- Serve production frontend files over HTTPS.
- Browser requests include cookies and CSRF headers. Configure
  `CORS_ORIGINS` with the exact frontend origin(s); the API enables credentialed
  CORS for `/api/*`. Set `VITE_API_BASE_URL` to the reachable API base ending
  in `/api`. Never use `*` for credentialed CORS.
- Authentication persists in HTTP-only cookies across page reloads. Expired
  access tokens are refreshed automatically, and the frontend signs users out
  after 15 minutes without activity.
- Production auth cookies use `SameSite=None; Secure` by default so separate
  Render-hosted frontend and API domains can send cookies with credentialed
  requests. If the browser blocks third-party cookies, use custom frontend and
  API domains under the same registrable domain, set `COOKIE_DOMAIN` to that
  shared parent domain, and set `COOKIE_SAMESITE=Lax`.

---

© 2026 Gosrani Wholesalers Limited, Eldoret, Kenya. Internal business software.