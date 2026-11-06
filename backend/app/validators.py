"""Request payload validation helpers."""

import re
from collections.abc import Mapping

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_login_payload(
    payload: object,
) -> list[dict[str, str]]:
    """Validate login fields while ignoring unrecognized client fields."""
    if not isinstance(payload, Mapping):
        return [{"field": "body", "message": "A JSON object is required."}]

    errors = []
    email = payload.get("email")
    password = payload.get("password")
    if not isinstance(email, str) or not email.strip():
        errors.append({"field": "email", "message": "Email is required."})
    elif not EMAIL_PATTERN.fullmatch(email.strip()):
        errors.append({"field": "email", "message": "Enter a valid email address."})
    if not isinstance(password, str) or not password:
        errors.append({"field": "password", "message": "Password is required."})
    return errors
