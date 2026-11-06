"""Shared helpers for database-backed API routes."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from flask_jwt_extended import get_jwt_identity
from sqlalchemy import select

from app.extensions import db
from app.models import AuditAction, AuditEntity, AuditLog, User, UserLocation


class ApiValidationError(Exception):
    """A field-level request validation error."""

    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field


def current_user() -> User:
    """Return the user attached to the authenticated JWT."""
    return db.session.get(User, int(get_jwt_identity()))


def user_location_ids(user_id: int) -> list[int]:
    """Return the locations assigned to a user."""
    return list(
        db.session.scalars(
            select(UserLocation.location_id)
            .where(UserLocation.user_id == user_id)
            .order_by(UserLocation.location_id)
        )
    )


def audit(
    entity_type: AuditEntity,
    entity_id: int,
    action: AuditAction,
    actor_id: int,
    before: dict[str, Any] | list[Any] | None = None,
    after: dict[str, Any] | list[Any] | None = None,
) -> None:
    """Add an audit record in the current transaction."""
    db.session.add(
        AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_id=actor_id,
            before=before,
            after=after,
        )
    )


def json_number(value: Decimal | None) -> float | None:
    """Convert persisted decimal quantities into JSON numbers."""
    return float(value) if value is not None else None


def iso_datetime(value: datetime | None) -> str | None:
    """Format database timestamps as UTC ISO 8601 strings."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
