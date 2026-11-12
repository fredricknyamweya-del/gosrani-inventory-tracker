# Gosrani Inventory Tracker

Inventory management software for Gosrani Wholesalers Limited in Eldoret,
Kenya. The application has a React frontend and a Flask API backed by a
relational database. Signed-in staff can record and review stock movements;
administrators can also manage users and the product catalog, edit records, and
use the read-only inventory assistant.

## Current scope

- Create and review stock movement records against a location, category, item,
  and specification. Records include the date, quantities in and out, handler,
  and optional details.
- Browse, search, filter, sort, paginate, and inspect inventory records within
  the signed-in user's assigned locations.
- Review current stock remaining on an inventory record, calculated across all
  non-deleted entries for the same specification and location.
- Validate entries on the server and show review warnings, including large
  quantities, both quantity fields being filled, outgoing quantity exceeding
  recorded stock, and unusual dates.
- Use a managed catalog of categories, items, and specifications. Staff can
  request missing catalog entries; administrators can review requests and
  maintain catalog items.
- Manage user accounts, roles, active status, and location assignments as an
  administrator.
- Use the inventory assistant as an administrator. Its database operations are
  read-only and location-scoped. Without an OpenAI API key it uses built-in
  responses; when a key is configured, the question and relevant inventory
  results may be sent to OpenAI to phrase the answer.
- Protect API changes with server-side validation and authorization, support
  bearer-token and cookie-based authentication, and keep an audit log of
  application changes.

Inventory quantities are associated with product specifications. Products
support piece (`PCS`) or kilogram (`KG`) stock units, and specifications can
carry pack-size metadata. Historical spreadsheet import and offline operation
are not currently part of the application.

## Roles

| Capability | Admin | User |
| --- | :---: | :---: |
| Sign in, browse, and inspect inventory | Yes | Yes |
| Add and review inventory records | Yes | Yes |
| Edit or delete inventory records | Yes | No |
| Manage catalog items and review catalog requests | Yes | No |
| Manage users | Yes | No |
| Use the inventory assistant | Yes | No |

New records created by a User are locked; Admin-created records can remain
saved. The API enforces permissions independently of the frontend.

## Technology

| Layer | Technology |
| --- | --- |
| Frontend | React 19, JavaScript/JSX, React Router 7 |
| Frontend build | Vite 8 |
| Backend | Flask, Python 3.12 |
| Database access | SQLAlchemy and Flask-Migrate |
| Local database | SQLite |
| Production database | PostgreSQL with Psycopg 3 |
| Dependency management | npm and Pipenv |

The frontend requires Node.js 22.12 or newer. The backend Pipfile targets
Python 3.12.

## Getting started

### Frontend

```sh
cd frontend
npm ci
npm run dev
```

The Vite server runs at `http://localhost:8443`. The API defaults to
`http://localhost:5000/api`. To use another API URL, set
`VITE_API_BASE_URL` in `frontend/.env.local`; see
[`frontend/.env.example`](frontend/.env.example).

Available scripts:

```sh
npm run dev      # Start the development server
npm run build    # Build the production frontend into dist/
npm run preview  # Preview the production build
```

### Backend

```sh
cd backend
pipenv sync --dev
```

Create `backend/.env` from [`backend/.env.example`](backend/.env.example) if
you do not already have a local environment file. Set a valid
`SEED_ADMIN_EMAIL` and a `SEED_ADMIN_PASSWORD` of at least six characters
before seeding. Keep `.env` and all credentials private; do not commit them.

Run the database migration, seed the initial administrator, location, and
starter catalog, then start the API:

```sh
pipenv run flask --app app db upgrade
pipenv run flask --app app seed
pipenv run flask --app app run --port 5000
```

The seed command accepts `--user-email user@example.com` more than once to
create additional User accounts. It generates a temporary password for each
new account and prints it once after a successful seed; handle that output as
sensitive.

SQLite is used locally by default at `backend/instance/gosrani.db`. For
production, configure a PostgreSQL `DATABASE_URL` and the required signing
secrets in the service environment. Production requires a TLS PostgreSQL
connection. See [the database guide](backend/docs/DATABASE.md) for database,
seeding, and deployment configuration details.

## Application routes

| Path | Screen | Access |
| --- | --- | --- |
| `/login` | Sign in | Public |
| `/inventory` | Inventory list | Signed in |
| `/inventory/new` | Add and review an inventory record | Signed in |
| `/inventory/:id` | Inventory record details | Signed in |
| `/inventory/:id/edit` | Edit an inventory record | Admin |
| `/account/password` | Change password | Signed in |
| `/assistant` | Read-only inventory assistant | Admin |
| `/catalog` | Catalog and catalog requests | Admin |
| `/users` | User management | Admin |

The root path redirects signed-in users to `/inventory`.

## API overview

The Flask API is rooted at `/api`. It provides authentication and session
operations under `/auth`, plus:

| Endpoint | Purpose |
| --- | --- |
| `/api/health` | Health check |
| `/api/inventory` | List and create inventory records |
| `/api/inventory/validate` | Validate a record before saving |
| `/api/inventory/<id>` | Read, update, or delete an inventory record |
| `/api/inventory/<id>/stock` | Read current stock for an administrator's record |
| `/api/locations` | List locations available to the signed-in user |
| `/api/catalog` | Read the active catalog |
| `/api/catalog/categories` and `/api/catalog/items` | Manage catalog entries |
| `/api/catalog/requests` | Submit or review missing-catalog requests |
| `/api/users` | Admin user management |
| `/api/assistant/query` | Admin read-only inventory questions |

The frontend stores access and refresh tokens in `localStorage` and sends
bearer authorization headers, avoiding mobile-browser cross-site cookie
restrictions. The backend also supports cookie authentication with CSRF
protection for compatible clients. Configure `CORS_ORIGINS` with the exact
frontend origin(s); do not use a wildcard origin. Because scripts can access
`localStorage`, keep dependencies current and prevent cross-site scripting.

## Tests

Backend tests use an in-memory SQLite database by default. From `backend/`,
run:

```sh
pipenv run pytest
```

Build the frontend from `frontend/` with `npm run build`.

## Project structure

```text
.
├── backend/
│   ├── app/                 # Flask API, models, validation, and business logic
│   ├── docs/                 # Database and deployment guidance
│   ├── migrations/           # Alembic database migrations
│   └── tests/                # Backend test suite
├── frontend/
│   ├── src/app/              # Application routes and shell
│   ├── src/components/       # Shared interface components
│   ├── src/pages/            # Inventory, catalog, assistant, and account screens
│   └── src/services/api.js   # Frontend API client
├── assets/                   # Project data model and visual assets
└── README.md
```
