"""Authentication routes and JWT lifecycle handlers."""

from datetime import UTC, datetime

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
)
from flask_jwt_extended.exceptions import JWTExtendedException
from werkzeug.security import check_password_hash, generate_password_hash

from app.auth_service import authenticate
from app.errors import error_response, validation_error
from app.extensions import db, jwt
from app.models import RevokedToken, User, UserStatus
from app.users import find_user_by_id, public_user
from app.validators import validate_login_payload

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def register_jwt_callbacks() -> None:
    """Reject revoked JWTs and resolve active users from the database."""

    @jwt.token_in_blocklist_loader
    def token_is_revoked(_header: dict, payload: dict) -> bool:
        if db.session.get(RevokedToken, payload["jti"]) is not None:
            return True
        user = db.session.get(User, int(payload["sub"]))
        return user is None or payload.get("auth_version", 0) != user.auth_version

    @jwt.user_lookup_loader
    def load_active_user(_header: dict, payload: dict) -> User | None:
        user = find_user_by_id(int(payload["sub"]))
        if user is None or user.status != UserStatus.ACTIVE:
            return None
        return user

    @jwt.user_lookup_error_loader
    def active_user_required(_header: dict, _payload: dict):
        return error_response(401, "Authentication is required.", "unauthorized")

    @jwt.unauthorized_loader
    def missing_token(_reason: str):
        return error_response(401, "Authentication is required.", "unauthorized")

    @jwt.invalid_token_loader
    def invalid_token(_reason: str):
        return error_response(401, "The session is invalid. Please sign in again.", "invalid_token")

    @jwt.expired_token_loader
    def expired_token(_header: dict, _payload: dict):
        return error_response(401, "The session has expired. Please sign in again.", "token_expired")

    @jwt.revoked_token_loader
    def revoked_token(_header: dict, _payload: dict):
        return error_response(401, "The session has ended. Please sign in again.", "token_revoked")


def _set_auth_cookies(response, user: User, refresh: bool = True):
    identity = str(user.id)
    additional_claims = {"auth_version": user.auth_version}
    access = create_access_token(
        identity=identity, additional_claims=additional_claims
    )
    set_access_cookies(response, access)
    if refresh:
        refresh_token = create_refresh_token(
            identity=identity, additional_claims=additional_claims
        )
        set_refresh_cookies(response, refresh_token)
    return response


def _revoke_token(payload: dict) -> None:
    if db.session.get(RevokedToken, payload["jti"]) is not None:
        return
    db.session.add(
        RevokedToken(
            jti=payload["jti"],
            token_type=payload["type"],
            user_id=int(payload["sub"]),
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
        )
    )


@auth_bp.post("/login")
def login():
    """Authenticate credentials and issue access/refresh cookies."""
    payload = request.get_json(silent=True)
    errors = validate_login_payload(payload)
    if errors:
        return validation_error(errors)

    lock_seconds = current_app.config["LOGIN_LOCK_MINUTES"] * 60
    status, user, retry_after = authenticate(
        payload["email"].strip().lower(),
        payload["password"],
        current_app.config["LOGIN_MAX_FAILURES"],
        lock_seconds,
    )
    if status == "locked":
        return error_response(
            429,
            "The account is temporarily locked. Try again later.",
            "account_locked",
            headers={"Retry-After": str(retry_after)},
        )
    if user is None:
        return error_response(401, "Invalid email or password.", "invalid_credentials")

    response = jsonify({"data": {"user": public_user(user)}})
    response.status_code = 200
    return _set_auth_cookies(response, user)


@auth_bp.get("/me")
@jwt_required()
def me():
    """Return the authenticated user's current database-backed profile."""
    user = find_user_by_id(int(get_jwt_identity()))
    if user is None or user.status != UserStatus.ACTIVE:
        return error_response(401, "Authentication is required.", "unauthorized")
    return jsonify({"data": public_user(user)})


@auth_bp.post("/change-password")
@jwt_required()
def change_password():
    """Change the authenticated user's password and invalidate older sessions."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return validation_error([{"field": "body", "message": "A JSON object is required."}])

    errors = []
    current_password = payload.get("currentPassword")
    new_password = payload.get("newPassword")
    if not isinstance(current_password, str) or not current_password:
        errors.append(
            {"field": "currentPassword", "message": "Current password is required."}
        )
    if not isinstance(new_password, str) or not new_password:
        errors.append(
            {"field": "newPassword", "message": "New password is required."}
        )
    elif len(new_password) < 12:
        errors.append(
            {
                "field": "newPassword",
                "message": "New password must contain at least 12 characters.",
            }
        )
    if errors:
        return validation_error(errors)

    user = find_user_by_id(int(get_jwt_identity()))
    if user is None or user.status != UserStatus.ACTIVE:
        return error_response(401, "Authentication is required.", "unauthorized")
    if not check_password_hash(user.password_hash, current_password):
        return error_response(401, "Current password is incorrect.", "invalid_credentials")
    if check_password_hash(user.password_hash, new_password):
        return validation_error(
            [
                {
                    "field": "newPassword",
                    "message": "Choose a password different from your current password.",
                }
            ]
        )

    user.password_hash = generate_password_hash(new_password)
    user.auth_version += 1
    user.failed_logins = 0
    user.locked_until = None
    db.session.commit()

    response = jsonify({"data": {"message": "Password changed successfully."}})
    return _set_auth_cookies(response, user)


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    """Rotate a refresh token and issue a new access token."""
    old_payload = get_jwt()
    user = find_user_by_id(int(get_jwt_identity()))
    if user is None or user.status != UserStatus.ACTIVE:
        return error_response(401, "Authentication is required.", "unauthorized")
    _revoke_token(old_payload)
    db.session.commit()
    response = jsonify({"data": {"user": public_user(user)}})
    return _set_auth_cookies(response, user)


@auth_bp.post("/logout")
@jwt_required()
def logout():
    """Revoke the current access and refresh tokens and clear auth cookies."""
    access_payload = get_jwt()
    _revoke_token(access_payload)
    refresh_cookie = request.cookies.get(current_app.config["JWT_REFRESH_COOKIE_NAME"])
    if refresh_cookie:
        try:
            refresh_payload = decode_token(refresh_cookie, allow_expired=True)
        except JWTExtendedException:
            refresh_payload = None
        if refresh_payload and refresh_payload.get("type") == "refresh":
            _revoke_token(refresh_payload)
    db.session.commit()
    response = jsonify({"data": {"message": "Signed out successfully."}})
    unset_jwt_cookies(response)
    return response
