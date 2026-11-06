# API

All responses use JSON. Successful responses are wrapped in `data`; list
responses also include pagination metadata. Error responses contain `message`
and `code`, with `errors` included for validation failures. Dates use
`YYYY-MM-DD`; timestamps are UTC ISO 8601.

Authentication uses short-lived HS256 JWTs in HttpOnly cookies. The browser
must send credentials and the matching `X-CSRF-TOKEN` header for
cookie-authenticated `POST`, `PUT`, `PATCH`, and `DELETE` requests. The CSRF
values are provided in the non-HttpOnly `csrf_access_token` and
`csrf_refresh_token` cookies. Do not store JWTs in local storage.

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

- `200`: Sets access and refresh cookies; body:

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
      }
    }
  }
  ```

- `401`: Invalid credentials or inactive account.
- `422`: Missing or invalid email/password fields.
- `429`: Account temporarily locked; includes `Retry-After`.
- Other applicable statuses: `400`, `415`, `500`, `503`.

### `GET /api/auth/me`

- Auth: Access cookie
- Request: None
- `200`: `{"data":{"id":12,"name":"Staff Member","email":"staff@example.com","role":"User","status":"Active","locationIds":[]}}`
- `401`: Missing, expired, revoked, or inactive-user token.
- Other applicable statuses: `500`, `503`.

### `POST /api/auth/change-password`

- Auth: Access cookie and access CSRF token in `X-CSRF-TOKEN`
- Request:

  ```json
  {
    "currentPassword": "<current-password>",
    "newPassword": "<new-password-at-least-12-characters>"
  }
  ```

- `200`: Changes the password hash, invalidates the user's other sessions, and
  issues fresh access and refresh cookies for this session.
- `401`: Missing or invalid session, or incorrect current password.
- `422`: Missing password fields or new password shorter than 12 characters.
- Other applicable statuses: `400`, `415`, `500`, `503`.

### `POST /api/auth/refresh`

- Auth: Refresh cookie and refresh CSRF token in `X-CSRF-TOKEN`
- Request: Empty JSON object `{}` with `Content-Type: application/json`.
- `200`: Rotates both cookies and returns the current user:
  `{"data":{"user":{"id":12,"name":"Staff Member","email":"staff@example.com","role":"User","status":"Active","locationIds":[]}}}`
- `401`: Missing, expired, revoked, or inactive-user token.
- `400`, `415`: Malformed JSON or non-JSON request body.
- Other applicable statuses: `500`, `503`.

### `POST /api/auth/logout`

- Auth: Access cookie and access CSRF token in `X-CSRF-TOKEN`
- Request: Empty JSON object `{}` with `Content-Type: application/json`.
- `200`: Revokes the active access and refresh tokens, clears auth cookies,
  and returns `{"data":{"message":"Signed out successfully."}}`.
- `401`: Missing, expired, revoked, or inactive-user token.
- `400`, `415`: Malformed JSON or non-JSON request body.
- Other applicable statuses: `500`, `503`.

## User management

### `DELETE /api/users/{id}`

- Auth: Active administrator and access CSRF token in `X-CSRF-TOKEN`
- Request: None
- `200`: Deletes the user and returns `{"data":{"id":12}}`.
- `404`: User does not exist.
- `409`: The signed-in administrator or last active administrator cannot be
  deleted; users linked to historical records must be deactivated instead.
- Other applicable statuses: `401`, `403`, `500`, `503`.
