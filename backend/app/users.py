"""User lookup, serialization, and administrator account endpoints."""

import re
import secrets
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app.api_utils import ApiValidationError, audit, current_user, iso_datetime, user_location_ids
from app.errors import error_response, validation_error
from app.extensions import db
from app.models import (
    AuditAction,
    AuditEntity,
    User,
    UserLocation,
    UserRole,
    UserStatus,
)

users_bp = Blueprint("users", __name__, url_prefix="/api/users")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def find_user_by_email(email: str) -> User | None:
    """Find an account using the case-insensitive email identity."""
    return db.session.scalar(
        select(User).where(func.lower(User.email) == email.lower())
    )


def find_user_by_id(user_id: int) -> User | None:
    """Load a user from the current database state."""
    return db.session.scalar(
        select(User).where(User.id == user_id).execution_options(populate_existing=True)
    )


def public_user(user: User) -> dict[str, object]:
    """Serialize a user without exposing credential or lockout fields."""
    location_ids = db.session.scalars(
        select(UserLocation.location_id).where(UserLocation.user_id == user.id)
    ).all()
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.value,
        "status": user.status.value,
        "locationIds": sorted(location_ids),
        "createdAt": iso_datetime(user.created_at),
    }


def _require_admin():
    user = current_user()
    if user.role != UserRole.ADMIN:
        return None, error_response(403)
    return user, None


def _required_text(payload: dict, key: str, label: str, maximum: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ApiValidationError(key, f"{label} is required.")
    value = value.strip()
    if len(value) > maximum:
        raise ApiValidationError(key, f"{label} must be {maximum} characters or fewer.")
    return value


@users_bp.get("")
@jwt_required()
def list_users():
    _, denied = _require_admin()
    if denied:
        return denied
    users = db.session.scalars(select(User).order_by(User.name, User.id)).all()
    return jsonify({"data": [public_user(user) for user in users]})


@users_bp.post("")
@jwt_required()
def create_user():
    actor, denied = _require_admin()
    if denied:
        return denied
    payload = request.get_json()
    if not isinstance(payload, dict):
        return validation_error([{"field": "body", "message": "A JSON object is required."}])
    try:
        name = _required_text(payload, "name", "Name", 120)
        email = _required_text(payload, "email", "Email", 254).lower()
        if not EMAIL_PATTERN.fullmatch(email):
            raise ApiValidationError("email", "Enter a valid email address.")
        if db.session.scalar(select(User.id).where(func.lower(User.email) == email)):
            raise ApiValidationError("email", "A user with this email already exists.")
        try:
            role = UserRole(payload.get("role", UserRole.USER.value))
        except (TypeError, ValueError):
            raise ApiValidationError("role", "Role must be Admin or User.") from None

        temporary_password = secrets.token_urlsafe(15)
        new_user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(temporary_password),
            role=role,
            status=UserStatus.ACTIVE,
        )
        db.session.add(new_user)
        db.session.flush()
        for location_id in user_location_ids(actor.id):
            db.session.add(UserLocation(user_id=new_user.id, location_id=location_id))
        audit(
            AuditEntity.USER,
            new_user.id,
            AuditAction.CREATE,
            actor.id,
            after={"name": name, "email": email, "role": role.value, "status": "Active"},
        )
        db.session.commit()
    except ApiValidationError as error:
        db.session.rollback()
        return validation_error([{"field": error.field, "message": str(error)}])
    except IntegrityError:
        db.session.rollback()
        return error_response(409, "A user with this email already exists.", "user_conflict")
    return jsonify({
        "data": {
            "user": public_user(new_user),
            "temporaryPassword": temporary_password,
        }
    }), 201


@users_bp.patch("/<int:user_id>")
@jwt_required()
def update_user(user_id: int):
    actor, denied = _require_admin()
    if denied:
        return denied
    target = db.session.get(User, user_id)
    if target is None:
        return error_response(404, "User not found.", "not_found")
    payload = request.get_json()
    if not isinstance(payload, dict):
        return validation_error([{"field": "body", "message": "A JSON object is required."}])

    before = public_user(target)
    try:
        if "name" in payload:
            target.name = _required_text(payload, "name", "Name", 120)
        if "email" in payload:
            email = _required_text(payload, "email", "Email", 254).lower()
            if not EMAIL_PATTERN.fullmatch(email):
                raise ApiValidationError("email", "Enter a valid email address.")
            if db.session.scalar(
                select(User.id).where(func.lower(User.email) == email, User.id != target.id)
            ):
                raise ApiValidationError("email", "A user with this email already exists.")
            target.email = email
        if "role" in payload:
            try:
                target.role = UserRole(payload["role"])
            except (TypeError, ValueError):
                raise ApiValidationError("role", "Role must be Admin or User.") from None
        if "status" in payload:
            try:
                target.status = UserStatus(payload["status"])
            except (TypeError, ValueError):
                raise ApiValidationError("status", "Status must be Active or Inactive.") from None

        if target.role != UserRole.ADMIN or target.status != UserStatus.ACTIVE:
            active_admin_count = db.session.scalar(
                select(func.count()).select_from(User).where(
                    User.role == UserRole.ADMIN,
                    User.status == UserStatus.ACTIVE,
                )
            ) or 0
            if before["role"] == UserRole.ADMIN.value and before["status"] == UserStatus.ACTIVE.value and active_admin_count <= 1:
                raise ApiValidationError("role", "At least one active administrator must remain.")

        after = public_user(target)
        audit(AuditEntity.USER, target.id, AuditAction.UPDATE, actor.id, before=before, after=after)
        db.session.commit()
    except ApiValidationError as error:
        db.session.rollback()
        return validation_error([{"field": error.field, "message": str(error)}])
    except IntegrityError:
        db.session.rollback()
        return error_response(409, "A user with this email already exists.", "user_conflict")
    return jsonify({"data": public_user(target)})
