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
