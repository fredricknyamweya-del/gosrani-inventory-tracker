# API

All responses use JSON. Successful responses are wrapped in `data`; list
responses also include pagination metadata. Error responses contain `message`
and `code`, with `errors` included for validation failures. Dates use
`YYYY-MM-DD`; timestamps are UTC ISO 8601.

Authentication supports short-lived HS256 JWTs in either HttpOnly cookies or
`Authorization: Bearer` headers. The frontend uses bearer tokens stored in
`localStorage` so mobile browsers can authenticate without cross-site cookies.
This makes protection against cross-site scripting especially important.
Cookie-authenticated clients must send credentials and the matching
`X-CSRF-TOKEN` header for `POST`, `PUT`, `PATCH`, and `DELETE` requests. The
CSRF values are provided in the non-HttpOnly `csrf_access_token` and
`csrf_refresh_token` cookies.

## Health

### `GET /api/health`

- Auth: Public
- Request: None
- `200`: `{"data":{"status":"ok"}}`
- `Cache-Control: no-store`

## Authentication

### `POST /api/auth/login`

- Auth: Public
- Request:

  ```json
  {"email":"staff@example.com","password":"<password>"}
  ```

- `200`: Sets access and refresh cookies and returns the tokens for bearer
  clients; response is not cached:

  ```json
  {
    "data": {
      "user": {
        "id": 12,
        "name": "Staff Member",
        "email": "staff@example.com",
        "role": "User",
        "status": "Active",
        "locationIds": []
      },
      "accessToken": "<access-jwt>",
      "refreshToken": "<refresh-jwt>"
    }
  }
  ```

- `401`: Invalid credentials or inactive account.
- `422`: Missing or invalid email/password fields.
- `429`: Account temporarily locked; includes `Retry-After`.
- Other applicable statuses: `400`, `415`, `500`, `503`.

### `GET /api/auth/me`

- Auth: Access cookie or `Authorization: Bearer <access-jwt>`
- Request: None
- `200`: `{"data":{"id":12,"name":"Staff Member","email":"staff@example.com","role":"User","status":"Active","locationIds":[]}}`
- `401`: Missing, expired, revoked, or inactive-user token.
- Other applicable statuses: `500`, `503`.

### `GET /api/auth/csrf`

- Auth: Public; uses the current browser cookies when present.
- Request: None. Send credentials so the API receives its host-only CSRF cookies.
- `200`: Returns the access and refresh CSRF values for the frontend to send in
  `X-CSRF-TOKEN` on protected write requests. Missing cookies are returned as
  `null`.
- Response caching is disabled. The endpoint is available only to configured
  credentialed CORS origins.

### `POST /api/auth/change-password`

- Auth: Access cookie and CSRF token, or `Authorization: Bearer <access-jwt>`
- Request:

  ```json
  {
    "currentPassword": "<current-password>",
    "newPassword": "<new-password-at-least-6-characters>"
  }
  ```

- `200`: Changes the password hash, invalidates the user's other sessions, and
  issues fresh access and refresh cookies and bearer tokens for this session.
- `401`: Missing or invalid session, or incorrect current password.
- `422`: Missing password fields or new password shorter than 6 characters.
- Other applicable statuses: `400`, `415`, `500`, `503`.

### `POST /api/auth/refresh`

- Auth: Refresh cookie and CSRF token, or `Authorization: Bearer <refresh-jwt>`
- Request: Empty JSON object `{}` with `Content-Type: application/json`.
- `200`: Rotates both cookies and bearer tokens and returns the current user.
- `401`: Missing, expired, revoked, or inactive-user token.
- `400`, `415`: Malformed JSON or non-JSON request body.
- Other applicable statuses: `500`, `503`.

### `POST /api/auth/logout`

- Auth: Access cookie and CSRF token, or `Authorization: Bearer <access-jwt>`
- Bearer request: Include the matching `refreshToken` in the JSON body so both
  tokens can be revoked:

  ```json
  {"refreshToken":"<refresh-jwt>"}
  ```

- Cookie request: Empty JSON object `{}` with `Content-Type: application/json`.
- `200`: Revokes the active access and refresh tokens, clears auth cookies,
  and returns `{"data":{"message":"Signed out successfully."}}`.
- `401`: Missing, expired, revoked, or inactive-user token.
- `400`, `415`: Malformed JSON or non-JSON request body.
- Other applicable statuses: `500`, `503`.

## Inventory

### `GET /api/inventory/{id}/stock`

- Auth: Active administrator with an access token. User accounts receive `403`.
- Request: None. The record identifier may be numeric (for example, `128`) or
  use the `INV-000128` form.
- `200`: Returns current stock for the record's specification at its location.
  The balance is Quantity In minus Quantity Out across all dates, excluding
  soft-deleted records and entries for other specifications or locations:

  ```json
  {
    "data": {
      "quantity": 99.8,
      "unit": "BALE",
      "normalizedQuantity": 998,
      "equivalentPieces": 998,
      "packSize": 10,
      "piecesPerBale": 10,
      "display": "99.8 bales (998 pcs)",
      "locationId": "1",
      "locationName": "Eldoret Godown",
      "specificationId": "5",
      "itemName": "V SHD Cushion",
      "sizeLabel": "Quilted",
      "asOf": "2026-11-12T08:41:00Z"
    }
  }
  ```

- `packSize` is specification metadata; bale stock conversions use
  `piecesPerBale`.
- `404`: Record does not exist or has been soft-deleted.
- `Cache-Control: no-store`; the stock response is not cached.
- This endpoint does not add fields or ETags to the inventory record detail
  response.

New records derive `enteredUnit` from the saved product configuration. Bale
quantities are stored as originally entered and normalized to pieces using the
product's configured rate. The response includes the normalized transaction
quantities and the conversion snapshot used at the time:

```json
{
  "quantityIn": 5,
  "enteredUnit": "BALE",
  "piecesPerUnit": 5,
  "normalizedQuantityIn": 25
}
```

Kilogram quantities may include up to three decimal places; piece and bale
quantities must be whole numbers. Stock-out quantities are validated against
the normalized available balance.

## Inventory summary

### `GET /api/catalog/summary`

- Auth: Signed-in user
- `200`: Returns one summary for every registered product, including products
  with no transactions. Transaction totals are limited to the user's assigned
  locations. Bale totals are displayed in bales and include
  `equivalentPieces`; no totals are added across different units.
- The `totals` object includes registered, bale-based, piece-based, and
  transaction counts.

### `POST /api/catalog/items`

- Auth: Active administrator
- Request: Includes `categoryId`, `name`, and `specifications`. Optional
  `inventoryUnit` is `PCS`, `BALE`, or `KG`; `piecesPerBale` is required as a
  positive whole number when `inventoryUnit` is `BALE`.
- `201`: Creates the item with its saved inventory configuration. Omitted
  inventory configuration defaults to pieces.
- `422`: Invalid inventory unit or bale conversion configuration.

### `PATCH /api/catalog/items/{id}`

- Auth: Active administrator
- Request: May update `inventoryUnit` and `piecesPerBale`. Historical
  transaction quantities and conversion snapshots are not rewritten.
- `200`: Returns the updated item configuration.
- `422`: Invalid configuration, or an incompatible kilogram/piece unit change
  after stock transactions exist.

### `DELETE /api/catalog/items/{id}`

- Auth: Active administrator
- `200`: Permanently deletes the item and its specifications.
- `404`: Item does not exist.
- `409`: The item has inventory history, catalog requests, or another linked
  record. Deactivate the item to retain its history.

## User management

### `GET /api/locations`

- Auth: Signed-in user
- `200`: Returns active locations available to the user as
  `{"data":[{"id":1,"code":"ELD","name":"Eldoret Godown"}]}`. Administrators
  can see all active locations; other users see only their assigned locations.
- Other applicable statuses: `401`, `500`, `503`.

### `POST /api/users`

- Auth: Active administrator with a bearer access token, or cookie and access
  CSRF token in `X-CSRF-TOKEN`
- Request:

  ```json
  {
    "name": "Staff Member",
    "email": "staff@example.com",
    "role": "User",
    "locationIds": [1]
  }
  ```

- `201`: Creates the user, assigns the requested active locations, and returns
  the user and a one-time temporary password.
- `422`: Missing or invalid fields, including location IDs that are empty,
  duplicated, unknown, or inactive.
- Other applicable statuses: `401`, `403`, `409`, `500`, `503`.

### `PATCH /api/users/{id}`

- Auth: Active administrator with a bearer access token, or cookie and access
  CSRF token in `X-CSRF-TOKEN`
- Request: Any of `name`, `email`, `role`, or `status`; for example:

  ```json
  {
    "email": "new-address@example.com"
  }
  ```

- `200`: Updates the supplied fields and returns the user. Email addresses are
  validated, stored in lowercase, and must be unique.
- `404`: User does not exist.
- `409`: The primary administrator cannot be demoted or deactivated, or an
  update would remove the last active administrator.
- `422`: A supplied field is invalid or the email address is already in use.
- Other applicable statuses: `401`, `403`, `500`, `503`.

### `DELETE /api/users/{id}`

- Auth: Active administrator with a bearer access token, or cookie and access
  CSRF token in `X-CSRF-TOKEN`
- Request: None
- `200`: Deletes the user and returns `{"data":{"id":12}}`.
- `404`: User does not exist.
- `409`: The signed-in administrator or last active administrator cannot be
  deleted; users linked to historical records must be deactivated instead.
- Other applicable statuses: `401`, `403`, `500`, `503`.
