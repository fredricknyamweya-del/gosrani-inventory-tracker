# Agent guidance

## Inventory entry units

- An item has one required entry unit: `BALE`, `PCS`, or `KG`. Read it from
  `Item.entry_unit`; never add an entry-unit selector or infer the unit from a
  specification.
- Inventory API quantities are stored in base units: pieces for piece-counted
  items and kilograms for weight-counted items. BALE requests convert whole
  bale counts using the submitted `piecesPerBale`, or the specification's
  standard pack size when omitted.
- Keep each bale record's conversion on `InventoryRecord.pieces_per_bale`.
  Never rewrite historical quantities. Display values using
  `backend/app/units.py::format_quantity_display` and server-supplied values;
  do not sum across specifications.
- A specification's standard pack size is optional for BALE items, and is
  invalid for PCS or KG items. Entry units and specification pack sizes are
  immutable after related inventory exists.
- The approved policy is BALE for Pillows, Duvets except Duvet Bags, Blankets,
  Woolen Duvet, Plain School Bedcovers - Heavy, and White Pillow Case. It is
  PCS for Duvet Bags, Pillow Kiss Case, and Sofa Sets, Mattresses, and
  Cushions. KG items and all unlisted items are left for review.
- `flask apply-unit-policy` must remain dry-run by default, match names
  exactly (case-insensitively), and audit changes. Use only a local or
  explicitly reviewed database; never use production credentials.

## Validation

Run backend commands from `backend/` with Pipenv and frontend commands from
`frontend/` with npm. Before committing relevant changes, run:

```sh
cd backend
pipenv run pytest -q
pipenv run ruff check .
cd ../frontend
npm run build
```

Do not commit `.env` files, add dependencies, rewrite existing inventory data,
or push changes unless requested.
