"""Initial database seed command tests."""

from sqlalchemy import func, select
from werkzeug.security import check_password_hash

from app.extensions import db
from app.models import (
    Category,
    Item,
    Location,
    Specification,
    User,
    UserLocation,
    UserRole,
    UserStatus,
)


def configure_seed_environment(monkeypatch, *, email="admin@example.com"):
    monkeypatch.setenv("SEED_ADMIN_EMAIL", email)
    monkeypatch.setenv("SEED_ADMIN_NAME", "Initial Admin")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "long-enough-seed-password")
    monkeypatch.setenv("DEFAULT_LOCATION_CODE", "ELD")
    monkeypatch.setenv("DEFAULT_LOCATION_NAME", "Eldoret Godown")


def invoke_seed(app):
    return app.test_cli_runner().invoke(args=["seed"])


def test_seed_creates_admin_location_and_catalog(app, monkeypatch):
    configure_seed_environment(monkeypatch)

    result = invoke_seed(app)

    assert result.exit_code == 0, result.output
    assert "admins added=1" in result.output
    assert "locations added=1" in result.output
    with app.app_context():
        admin = db.session.scalar(
            select(User).where(User.email == "admin@example.com")
        )
        assert admin is not None
        assert admin.role == UserRole.ADMIN
        assert admin.status == UserStatus.ACTIVE
        assert admin.name == "Initial Admin"
        assert check_password_hash(
            admin.password_hash, "long-enough-seed-password"
        )
        location = db.session.scalar(
            select(Location).where(Location.code == "ELD")
        )
        assert location is not None
        assert location.name == "Eldoret Godown"
        assert db.session.get(UserLocation, (admin.id, location.id)) is not None
        assert db.session.scalar(select(func.count(Category.id))) == 10
        assert db.session.scalar(select(func.count(Item.id))) == 16
        assert db.session.scalar(select(func.count(Specification.id))) == 34

        fibre = db.session.scalar(select(Item).where(Item.name == "Fibre"))
        assert fibre is not None
        assert fibre.unit.value == "KG"
        assert [spec.label for spec in fibre.specifications] == ["Standard"]

        sofa = db.session.scalar(
            select(Category).where(Category.name == "Sofa Sets")
        )
        assert sofa is not None
        assert db.session.scalar(
            select(Item.id).where(Item.category_id == sofa.id)
        ) is None


def test_seed_is_idempotent_and_does_not_reset_admin_credentials(app, monkeypatch):
    configure_seed_environment(monkeypatch)
    first = invoke_seed(app)
    assert first.exit_code == 0, first.output

    with app.app_context():
        admin = db.session.scalar(
            select(User).where(User.email == "admin@example.com")
        )
        assert admin is not None
        old_hash = admin.password_hash

    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "a-different-long-password")
    monkeypatch.setenv("SEED_ADMIN_NAME", "Changed Name")
    second = invoke_seed(app)

    assert second.exit_code == 0, second.output
    assert "admins added=0" in second.output
    assert "categories added=0" in second.output
    with app.app_context():
        admin = db.session.scalar(
            select(User).where(User.email == "admin@example.com")
        )
        assert admin is not None
        assert admin.password_hash == old_hash
        assert admin.name == "Initial Admin"
        assert db.session.scalar(select(func.count(Category.id))) == 10
        assert db.session.scalar(select(func.count(Item.id))) == 16
        assert db.session.scalar(select(func.count(Specification.id))) == 34


def test_seed_refuses_to_promote_existing_non_admin_and_rolls_back(app, monkeypatch):
    configure_seed_environment(monkeypatch)
    existing = User(
        name="Existing User",
        email="admin@example.com",
        password_hash="already-hashed",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )
    with app.app_context():
        db.session.add(existing)
        db.session.commit()

    result = invoke_seed(app)

    assert result.exit_code != 0
    assert "not an active Admin" in result.output
    with app.app_context():
        assert db.session.scalar(select(func.count(Category.id))) == 0
        user = db.session.scalar(
            select(User).where(User.email == "admin@example.com")
        )
        assert user is not None
        assert user.role == UserRole.USER


def test_seed_requires_strong_admin_password(app, monkeypatch):
    configure_seed_environment(monkeypatch)
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "short")

    result = invoke_seed(app)

    assert result.exit_code != 0
    assert "at least 12 characters" in result.output
    with app.app_context():
        assert db.session.scalar(select(func.count(User.id))) == 0
