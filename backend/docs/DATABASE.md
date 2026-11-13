# Database setup

Production uses PostgreSQL through SQLAlchemy and Psycopg 3. Supabase is the
managed PostgreSQL host; use its **session pooler** connection string, as
documented in the project architecture. The backend does not use Supabase
Auth or the Supabase client.

## Local development with SQLite

SQLite is the default for local development. Leave `DATABASE_URL` blank or
unset in `backend/.env`; the application stores data in
`backend/instance/gosrani.db`. From `backend/`, apply the schema and start the
API as usual:

```sh
PIPENV_VENV_IN_PROJECT=1 pipenv run flask --app app db upgrade
PIPENV_VENV_IN_PROJECT=1 pipenv run flask --app app run --port 5000
```

Alembic migrations run against SQLite, and migration autogeneration renders
SQLite table changes as batch operations. SQLite is intended for local
development; production startup requires PostgreSQL.

## Configure a database URL

Set `DATABASE_URL` in the backend environment to the connection string supplied
by Supabase (or another PostgreSQL provider). The application accepts
`postgres://`, `postgresql://`, and `postgresql+psycopg://` URLs, and normalizes
the first two to Psycopg 3. In production, TLS defaults to `sslmode=require`.
Explicit secure modes (`require`, `verify-ca`, or `verify-full`) are preserved;
non-TLS modes are rejected.

For PostgreSQL development or deployment, create `backend/.env` from
`.env.example` and set `DATABASE_URL`. Do not commit `.env` or paste database
credentials into source files or logs. Production startup refuses to run unless
its database URL uses PostgreSQL with Psycopg.

## Apply the schema

Run from the `backend/` directory after setting the environment variables:

```sh
PIPENV_VENV_IN_PROJECT=1 pipenv run flask --app app db upgrade
```

Run this as a release/pre-deploy step, not automatically on every web-worker
startup. The entry-unit migration adds `items.entry_unit` (PCS, BALE, or KG),
defaulting to PCS and backfilled as BALE for items with a specification pack
size. `inventory_records.pieces_per_bale` is nullable and positive when set;
only BALE records store it. Existing inventory quantities are not rewritten.
The local `flask apply-unit-policy` command applies the reviewed item/category
policy after migration. The `v_stock` view exposes base stock, `stock_pieces`,
and `stock_bales` by location and specification, using a record's saved bale
size or the specification's pack size for older records. It does not combine
different specifications. Do not run the destructive test suite against a
production database.

## Seed first-run data

After migrating the target database, set `SEED_ADMIN_EMAIL` and
`SEED_ADMIN_PASSWORD` in `backend/.env` or the deployment environment. The
password must contain at least 6 characters. Optionally set
`SEED_ADMIN_NAME`, `DEFAULT_LOCATION_CODE`, and `DEFAULT_LOCATION_NAME`.
The defaults identify the primary administrator as
`Gosrani Office-Primary Admin` and the location as `Gosrani Technical Office`.
Set these values in the deployment environment too if they are already
configured there. The seed command marks the configured administrator as
primary and synchronizes its display name without changing its password.
Primary administrators cannot be deleted, demoted, or deactivated through
user management.
Keep these values private; especially do not commit the password.

Then run from `backend/`:

```sh
PIPENV_VENV_IN_PROJECT=1 pipenv run flask --app app seed
```

The command creates the initial active Admin, the configured location, links
the Admin to that location, and adds the starter categories,
items, and specifications described in `../ARCHITECTURE.md`. Sofa Sets is
created as an empty category because its items are unconfirmed. Items whose
proposal has no specification receive a `Standard` specification without a
pack size, because inventory records must reference a specification. Seed
data is created only when missing; rerunning the command does not reset an
existing Admin password or reactivate existing accounts. Existing catalog
items with conflicting units or pack sizes stop the command and roll back all
changes.

The `apply-unit-policy` command is a dry run unless `--apply` is passed. It
matches category and item names exactly, ignoring case and surrounding
whitespace; it does not guess alternate names. It changes only
`items.entry_unit` and writes audit rows when applied. Run it only against a
local or otherwise explicitly reviewed database:

```sh
cd backend
pipenv run flask --app app apply-unit-policy
pipenv run flask --app app apply-unit-policy --apply
```

The approved mapping is BALE for all items in Pillows, Duvets except Duvet
Bags, and Blankets; plus Woolen Duvet, Plain School Bedcovers - Heavy, and
White Pillow Case. It is PCS for Duvet Bags and Pillow Kiss Case, and all
items in Sofa Sets, Mattresses, and Cushions. KG items and all products not
covered by these exact rules remain unchanged.

In the current seed catalog, BALE category matches are Pillow; Duvet N,
Duvet S, and Woolen Duvet; and Goldstar Blanket (BF). White Pillow Case is a
named match. PCS named matches are Duvet Bags and Pillow Kiss Case; the
Mattresses category includes HDF, SHDF, and SHDQ (and the local catalog may
also contain V HDQ); Cushions includes SHDQ Cushion. Sofa Sets exists but is
empty. Plain School Bedcovers - Heavy is missing. Bedcover 60x80, Fibre, and
the Packaging items are not covered by the policy and remain unchanged. The
migration's initial BALE backfill is broader than this policy: for example,
Bedcover 60x80 has a specification pack size and will remain initially BALE
until an administrator reviews its unit.

To create initial active User accounts as part of the same seed transaction,
pass `--user-email` once per account. The command generates a random password
for each newly created User, stores only its password hash, and prints the
password once after a successful seed. Existing active User accounts are left
unchanged and their passwords are not displayed. Treat the command output as
sensitive.

This seeds catalog metadata only, not inventory balances or historical Excel
entries. Those must be brought in through the separately planned import flow.

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
