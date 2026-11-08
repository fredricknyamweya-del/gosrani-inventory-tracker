"""Administrator user-management endpoint tests."""

from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import (
    AuditAction,
    AuditEntity,
    AuditLog,
    Location,
    User,
    UserLocation,
    UserRole,
)


def create_user(name: str, email: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash("correct-horse"),
        role=role,
    )
    db.session.add(user)
    db.session.commit()
    return user


def authenticate(client, user: User) -> str:
    response = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "correct-horse"},
    )
    assert response.status_code == 200
    return client.get_cookie("csrf_access_token", path="/").value


def test_admin_can_delete_user_and_their_location_assignments(client, app):
    admin = create_user("Admin", "admin@example.com", UserRole.ADMIN)
    target = create_user("Staff", "staff@example.com")
    location = Location(code="MAIN", name="Main warehouse")
    db.session.add(location)
    db.session.flush()
    db.session.add(UserLocation(user_id=target.id, location_id=location.id))
    db.session.commit()
    csrf_token = authenticate(client, admin)

    response = client.delete(
        f"/api/users/{target.id}",
        headers={"X-CSRF-TOKEN": csrf_token},
    )

    assert response.status_code == 200
    assert response.json["data"] == {"id": target.id}
    with app.app_context():
        assert db.session.get(User, target.id) is None
        assert db.session.get(UserLocation, (target.id, location.id)) is None
        deletion_audit = db.session.scalar(
            db.select(AuditLog).where(
                AuditLog.entity_type == AuditEntity.USER,
                AuditLog.entity_id == target.id,
                AuditLog.action == AuditAction.DELETE,
            )
        )
        assert deletion_audit is not None
        assert deletion_audit.actor_id == admin.id


def test_admin_cannot_delete_primary_admin(client, app):
    admin = create_user("Admin", "admin@example.com", UserRole.ADMIN)
    primary_admin = create_user(
        "Gosrani Office-Primary Admin",
        "primary@example.com",
        UserRole.ADMIN,
    )
    primary_admin.is_primary_admin = True
    db.session.commit()
    csrf_token = authenticate(client, admin)

    response = client.delete(
        f"/api/users/{primary_admin.id}",
        headers={"X-CSRF-TOKEN": csrf_token},
    )

    assert response.status_code == 409
    assert response.json["code"] == "primary_admin_protected"
    with app.app_context():
        assert db.session.get(User, primary_admin.id) is not None


def test_admin_cannot_demote_or_deactivate_primary_admin(client):
    admin = create_user("Admin", "admin@example.com", UserRole.ADMIN)
    primary_admin = create_user(
        "Gosrani Office-Primary Admin",
        "primary@example.com",
        UserRole.ADMIN,
    )
    primary_admin.is_primary_admin = True
    db.session.commit()
    csrf_token = authenticate(client, admin)

    for changes in ({"role": "User"}, {"status": "Inactive"}):
        response = client.patch(
            f"/api/users/{primary_admin.id}",
            headers={"X-CSRF-TOKEN": csrf_token},
            json=changes,
        )

        assert response.status_code == 409
        assert response.json["code"] == "primary_admin_protected"

    assert primary_admin.role == UserRole.ADMIN
    assert primary_admin.status.value == "Active"


def test_admin_can_list_active_locations(client):
    admin = create_user("Admin", "admin@example.com", UserRole.ADMIN)
    active_location = Location(code="MAIN", name="Main warehouse")
    inactive_location = Location(
        code="OLD", name="Old warehouse", active=False
    )
    db.session.add_all([active_location, inactive_location])
    db.session.commit()
    authenticate(client, admin)

    response = client.get("/api/locations")

    assert response.status_code == 200
    assert response.json["data"] == [
        {
            "id": active_location.id,
            "code": active_location.code,
            "name": active_location.name,
        }
    ]


def test_admin_can_create_user_with_selected_location(client, app):
    admin = create_user("Admin", "admin@example.com", UserRole.ADMIN)
    location = Location(code="MAIN", name="Main warehouse")
    db.session.add(location)
    db.session.commit()
    csrf_token = authenticate(client, admin)

    response = client.post(
        "/api/users",
        headers={"X-CSRF-TOKEN": csrf_token},
        json={
            "name": "Staff",
            "email": "staff@example.com",
            "role": "User",
            "locationIds": [location.id],
        },
    )

    assert response.status_code == 201
    user_id = response.json["data"]["user"]["id"]
    assert response.json["data"]["user"]["locationIds"] == [location.id]
    with app.app_context():
        assert db.session.get(UserLocation, (user_id, location.id)) is not None


def test_admin_can_update_user_email(client, app):
    admin = create_user("Admin", "admin@example.com", UserRole.ADMIN)
    target = create_user("Staff", "staff@example.com")
    csrf_token = authenticate(client, admin)

    response = client.patch(
        f"/api/users/{target.id}",
        headers={"X-CSRF-TOKEN": csrf_token},
        json={"email": "New.Staff@example.com"},
    )

    assert response.status_code == 200
    assert response.json["data"]["email"] == "new.staff@example.com"
    with app.app_context():
        updated_user = db.session.get(User, target.id)
        assert updated_user.email == "new.staff@example.com"
        update_audit = db.session.scalar(
            db.select(AuditLog).where(
                AuditLog.entity_type == AuditEntity.USER,
                AuditLog.entity_id == target.id,
                AuditLog.action == AuditAction.UPDATE,
            )
        )
        assert update_audit is not None
        assert update_audit.before["email"] == "staff@example.com"
        assert update_audit.after["email"] == "new.staff@example.com"


def test_admin_cannot_update_user_email_to_an_existing_address(client):
    admin = create_user("Admin", "admin@example.com", UserRole.ADMIN)
    target = create_user("Staff", "staff@example.com")
    another_user = create_user("Another Staff", "another@example.com")
    csrf_token = authenticate(client, admin)

    response = client.patch(
        f"/api/users/{target.id}",
        headers={"X-CSRF-TOKEN": csrf_token},
        json={"email": another_user.email},
    )

    assert response.status_code == 422
    assert response.json["errors"][0]["field"] == "email"
    assert target.email == "staff@example.com"


def test_create_user_rejects_inactive_location(client):
    admin = create_user("Admin", "admin@example.com", UserRole.ADMIN)
    location = Location(code="OLD", name="Old warehouse", active=False)
    db.session.add(location)
    db.session.commit()
    csrf_token = authenticate(client, admin)

    response = client.post(
        "/api/users",
        headers={"X-CSRF-TOKEN": csrf_token},
        json={
            "name": "Staff",
            "email": "staff@example.com",
            "locationIds": [location.id],
        },
    )

    assert response.status_code == 422
    assert response.json["errors"][0]["field"] == "locationIds"


def test_admin_cannot_delete_self(client):
    admin = create_user("Admin", "admin@example.com", UserRole.ADMIN)
    csrf_token = authenticate(client, admin)

    response = client.delete(
        f"/api/users/{admin.id}",
        headers={"X-CSRF-TOKEN": csrf_token},
    )

    assert response.status_code == 409
    assert response.json["code"] == "user_self_delete"


def test_user_with_historical_audit_references_cannot_be_deleted(client, app):
    admin = create_user("Admin", "admin@example.com", UserRole.ADMIN)
    target = create_user("Staff", "staff@example.com")
    db.session.add(
        AuditLog(
            entity_type=AuditEntity.USER,
            entity_id=target.id,
            action=AuditAction.UPDATE,
            actor_id=target.id,
        )
    )
    db.session.commit()
    csrf_token = authenticate(client, admin)

    response = client.delete(
        f"/api/users/{target.id}",
        headers={"X-CSRF-TOKEN": csrf_token},
    )

    assert response.status_code == 409
    assert response.json["code"] == "user_has_records"
    with app.app_context():
        assert db.session.get(User, target.id) is not None
        assert db.session.scalar(
            db.select(db.func.count()).select_from(AuditLog).where(
                AuditLog.actor_id == target.id
            )
        ) == 1
