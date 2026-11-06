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
        return db.session.get(RevokedToken, payload["jti"]) is not None

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
    access = create_access_token(identity=identity)
    set_access_cookies(response, access)
    if refresh:
        refresh_token = create_refresh_token(identity=identity)
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
            refresh_payload = decode_token(refresh_cookie)
        except JWTExtendedException:
            refresh_payload = None
        if refresh_payload and refresh_payload.get("type") == "refresh":
            _revoke_token(refresh_payload)
    db.session.commit()
    response = jsonify({"data": {"message": "Signed out successfully."}})
    unset_jwt_cookies(response)
    return response
