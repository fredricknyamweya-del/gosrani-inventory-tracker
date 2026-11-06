# PostgreSQL setup

Production uses PostgreSQL through SQLAlchemy and Psycopg 3. Supabase is the
managed PostgreSQL host; use its **session pooler** connection string, as
documented in the project architecture. The backend does not use Supabase
Auth or the Supabase client.

## Configure a database URL

Set `DATABASE_URL` in the backend environment to the connection string supplied
by Supabase (or another PostgreSQL provider). The application accepts
`postgres://`, `postgresql://`, and `postgresql+psycopg://` URLs, and normalizes
the first two to Psycopg 3. In production, TLS defaults to `sslmode=require`.
Explicit secure modes (`require`, `verify-ca`, or `verify-full`) are preserved;
non-TLS modes are rejected.

For local development, create `backend/.env` from `.env.example` and set
`DATABASE_URL`. Do not commit `.env` or paste database credentials into source
files or logs. Local SQLite remains the default when no development URL is set.
Production startup refuses to run unless its database URL uses PostgreSQL
with Psycopg.

## Apply the schema

Run from the `backend/` directory after setting the environment variables:

```sh
PIPENV_VENV_IN_PROJECT=1 pipenv run flask --app app db upgrade
```

Run this as a release/pre-deploy step, not automatically on every web-worker
startup. The migration creates the schema and the `v_stock` view. Do not run
the destructive test suite against a production database.

## Test against PostgreSQL

The normal test suite uses in-memory SQLite. To run it against a disposable
PostgreSQL database, set `TEST_DATABASE_URL` to that database's Psycopg URL and
run:

```sh
PIPENV_VENV_IN_PROJECT=1 pipenv run pytest
```

The test fixtures create and drop their tables. Use a dedicated test database
whose user has schema creation and deletion permissions; never point this
setting at production.

## Connection pool

PostgreSQL connections use a bounded SQLAlchemy pool (`pool_size=5`,
`max_overflow=5`) with health checks and a 30-second checkout timeout. This
allows up to ten pooled connections per application process; account for the
number of deployed workers when setting the provider's connection limit.
