"""Authentication and JWT lifecycle tests."""

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import User, UserRole, UserStatus


def create_user(
    email: str = "staff@example.com",
    password: str = "correct-horse",
    status: UserStatus = UserStatus.ACTIVE,
) -> User:
    user = User(
        name="Staff Member",
        email=email,
        password_hash=generate_password_hash(password),
        role=UserRole.USER,
        status=status,
    )
    db.session.add(user)
    db.session.commit()
    return user


def test_login_sets_jwt_cookies_and_me_reads_current_user(client, app):
    user = create_user()

    response = client.post(
        "/api/auth/login",
        json={"email": " STAFF@example.com ", "password": "correct-horse"},
    )

    assert response.status_code == 200
    assert response.json["data"]["user"]["id"] == user.id
    assert "password" not in response.json["data"]["user"]
    assert "passwordHash" not in response.json["data"]["user"]
    access_cookie = client.get_cookie("access_token_cookie", path="/api")
    refresh_cookie = client.get_cookie("refresh_token_cookie", path="/api/auth")
    access_csrf_cookie = client.get_cookie("csrf_access_token", path="/")
    refresh_csrf_cookie = client.get_cookie("csrf_refresh_token", path="/")
    assert access_cookie and access_cookie.http_only
    assert refresh_cookie and refresh_cookie.http_only
    assert access_csrf_cookie and not access_csrf_cookie.http_only
    assert refresh_csrf_cookie and not refresh_csrf_cookie.http_only

    csrf_response = client.get("/api/auth/csrf")
    assert csrf_response.status_code == 200
    assert csrf_response.headers["Cache-Control"] == "no-store"
    assert csrf_response.json["data"] == {
        "accessToken": access_csrf_cookie.value,
        "refreshToken": refresh_csrf_cookie.value,
    }

    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json["data"]["email"] == "staff@example.com"

    with app.app_context():
        persisted = db.session.get(User, user.id)
        assert persisted is not None
        assert persisted.failed_logins == 0
        assert persisted.last_login_at is not None


def test_csrf_endpoint_returns_null_without_auth_cookies(client):
    response = client.get("/api/auth/csrf")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json["data"] == {
        "accessToken": None,
        "refreshToken": None,
    }


def test_login_validation_ignores_unknown_fields(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "bad", "password": "", "role": "Admin"},
    )

    assert response.status_code == 422
    assert response.json["code"] == "validation_error"
    assert {error["field"] for error in response.json["errors"]} == {
        "email",
        "password",
    }


def test_invalid_login_increments_failure_count_then_locks_account(client, app):
    user = create_user()
    app.config["LOGIN_MAX_FAILURES"] = 2
    app.config["LOGIN_LOCK_MINUTES"] = 1

    first = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "incorrect"},
    )
    second = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "incorrect"},
    )

    assert first.status_code == 401
    assert second.status_code == 429
    assert int(second.headers["Retry-After"]) > 0
    with app.app_context():
        persisted = db.session.get(User, user.id)
        assert persisted is not None
        assert persisted.failed_logins == 2
        assert persisted.locked_until is not None


def test_inactive_user_cannot_login(client):
    create_user(status=UserStatus.INACTIVE)

    response = client.post(
        "/api/auth/login",
        json={"email": "staff@example.com", "password": "correct-horse"},
    )

    assert response.status_code == 401
    assert response.json["code"] == "invalid_credentials"


def test_refresh_rotates_tokens_and_logout_revokes_them(client):
    create_user()
    login_response = client.post(
        "/api/auth/login",
        json={"email": "staff@example.com", "password": "correct-horse"},
    )
    assert login_response.status_code == 200

    old_refresh = client.get_cookie("refresh_token_cookie", path="/api/auth").value
    refresh_csrf = client.get_cookie("csrf_refresh_token", path="/").value
    refreshed = client.post(
        "/api/auth/refresh",
        json={},
        headers={"X-CSRF-TOKEN": refresh_csrf},
    )

    assert refreshed.status_code == 200
    assert (
        client.get_cookie("refresh_token_cookie", path="/api/auth").value
        != old_refresh
    )

    access_csrf = client.get_cookie("csrf_access_token", path="/").value
    logout_response = client.post(
        "/api/auth/logout",
        json={},
        headers={"X-CSRF-TOKEN": access_csrf},
    )
    assert logout_response.status_code == 200
    assert client.get_cookie("access_token_cookie", path="/api") is None
    assert client.get_cookie("refresh_token_cookie", path="/api/auth") is None

    unauthenticated = client.get("/api/auth/me")
    assert unauthenticated.status_code == 401


def test_refresh_rejects_a_rotated_token(client):
    create_user()
    client.post(
        "/api/auth/login",
        json={"email": "staff@example.com", "password": "correct-horse"},
    )
    old_refresh = client.get_cookie("refresh_token_cookie", path="/api/auth").value
    old_csrf = client.get_cookie("csrf_refresh_token", path="/").value
    client.post(
        "/api/auth/refresh",
        json={},
        headers={"X-CSRF-TOKEN": old_csrf},
    )

    client.set_cookie("refresh_token_cookie", old_refresh, path="/api/auth")
    client.set_cookie("csrf_refresh_token", old_csrf, path="/")
    replay = client.post(
        "/api/auth/refresh",
        json={},
        headers={"X-CSRF-TOKEN": old_csrf},
    )

    assert replay.status_code == 401
    assert replay.json["code"] == "token_revoked"


def test_user_deactivation_invalidates_existing_access_cookie(client, app):
    user = create_user()
    client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "correct-horse"},
    )
    with app.app_context():
        persisted = db.session.get(User, user.id)
        assert persisted is not None
        persisted.status = UserStatus.INACTIVE
        db.session.commit()

    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_change_password_updates_hash_and_invalidates_other_sessions(
    client, app
):
    user = create_user()
    assert client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "correct-horse"},
    ).status_code == 200
    old_access_token = client.get_cookie(
        "access_token_cookie", path="/api"
    ).value
    csrf_token = client.get_cookie("csrf_access_token", path="/").value

    response = client.post(
        "/api/auth/change-password",
        json={
            "currentPassword": "correct-horse",
            "newPassword": "newpwd",
        },
        headers={"X-CSRF-TOKEN": csrf_token},
    )

    assert response.status_code == 200
    assert response.json["data"]["message"] == "Password changed successfully."
    assert client.get_cookie("access_token_cookie", path="/api").value != old_access_token
    assert client.get("/api/auth/me").status_code == 200

    stale_client = app.test_client()
    stale_client.set_cookie("access_token_cookie", old_access_token, path="/api")
    stale_response = stale_client.get("/api/auth/me")
    assert stale_response.status_code == 401
    assert stale_response.json["code"] == "token_revoked"

    with app.app_context():
        persisted = db.session.get(User, user.id)
        assert persisted is not None
        assert persisted.auth_version == 1
        assert persisted.password_hash != "newpwd"
        assert check_password_hash(
            persisted.password_hash, "newpwd"
        )

    assert client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "correct-horse"},
    ).status_code == 401
    assert client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "newpwd"},
    ).status_code == 200


def test_change_password_rejects_wrong_current_password(client, app):
    user = create_user()
    client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "correct-horse"},
    )
    csrf_token = client.get_cookie("csrf_access_token", path="/").value

    response = client.post(
        "/api/auth/change-password",
        json={
            "currentPassword": "incorrect",
            "newPassword": "a-new-strong-password",
        },
        headers={"X-CSRF-TOKEN": csrf_token},
    )

    assert response.status_code == 401
    assert response.json["code"] == "invalid_credentials"
    assert client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "correct-horse"},
    ).status_code == 200


def test_change_password_requires_minimum_length(client):
    create_user()
    client.post(
        "/api/auth/login",
        json={"email": "staff@example.com", "password": "correct-horse"},
    )
    csrf_token = client.get_cookie("csrf_access_token", path="/").value

    response = client.post(
        "/api/auth/change-password",
        json={"currentPassword": "correct-horse", "newPassword": "short"},
        headers={"X-CSRF-TOKEN": csrf_token},
    )

    assert response.status_code == 422
    assert response.json["code"] == "validation_error"
    assert response.json["errors"][0]["field"] == "newPassword"
