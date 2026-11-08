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
    monkeypatch.setenv("SEED_ADMIN_NAME", "sytsem admin")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "seedpw")
    monkeypatch.setenv("DEFAULT_LOCATION_CODE", "ELD")
    monkeypatch.setenv("DEFAULT_LOCATION_NAME", "Gosrani Technical Office")


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
        assert admin.name == "sytsem admin"
        assert admin.is_primary_admin is True
        assert check_password_hash(
            admin.password_hash, "seedpw"
        )
        location = db.session.scalar(
            select(Location).where(Location.code == "ELD")
        )
        assert location is not None
        assert location.name == "Gosrani Technical Office"
        assert db.session.get(UserLocation, (admin.id, location.id)) is not None
        assert db.session.scalar(select(func.count(Category.id))) == 10
        assert db.session.scalar(select(func.count(Item.id))) == 16
        assert db.session.scalar(select(func.count(Specification.id))) == 34

        fibre = db.session.scalar(select(Item).where(Item.name == "Fibre"))
        assert fibre is not None
        assert fibre.unit.value == "KG"
        fibre_spec = db.session.scalar(
            select(Specification).where(Specification.item_id == fibre.id)
        )
        assert fibre_spec is not None
        assert fibre_spec.label == "Standard"

        sofa = db.session.scalar(
            select(Category).where(Category.name == "Sofa Sets")
        )
        assert sofa is not None
        assert db.session.scalar(
            select(Item.id).where(Item.category_id == sofa.id)
        ) is None


def test_seed_defaults_to_requested_primary_admin_and_location_names(app, monkeypatch):
    configure_seed_environment(monkeypatch)
    monkeypatch.delenv("SEED_ADMIN_NAME")
    monkeypatch.delenv("DEFAULT_LOCATION_NAME")

    result = invoke_seed(app)

    assert result.exit_code == 0, result.output
    with app.app_context():
        admin = db.session.scalar(
            select(User).where(User.email == "admin@example.com")
        )
        location = db.session.scalar(select(Location).where(Location.code == "ELD"))
        assert admin is not None
        assert admin.name == "Gosrani Office-Primary Admin"
        assert admin.is_primary_admin is True
        assert location is not None
        assert location.name == "Gosrani Technical Office"


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
    monkeypatch.setenv("SEED_ADMIN_NAME", "Gosrani Office-Primary Admin")
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
        assert admin.name == "Gosrani Office-Primary Admin"
        assert admin.is_primary_admin is True
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
    assert "at least 6 characters" in result.output
    with app.app_context():
        assert db.session.scalar(select(func.count(User.id))) == 0


def test_seed_creates_users_with_hashed_one_time_passwords(app, monkeypatch):
    configure_seed_environment(monkeypatch)

    result = app.test_cli_runner().invoke(
        args=[
            "seed",
            "--user-email",
            "warehouse1@example.com",
            "--user-email",
            "warehouse2@example.com",
        ]
    )

    assert result.exit_code == 0, result.output
    assert "users added=2" in result.output
    credentials = {}
    for line in result.output.splitlines():
        if line.startswith("New User login: "):
            email, password = line.removeprefix("New User login: ").split(" / ", 1)
            credentials[email] = password

    assert set(credentials) == {
        "warehouse1@example.com",
        "warehouse2@example.com",
    }
    with app.app_context():
        location = db.session.scalar(select(Location).where(Location.code == "ELD"))
        assert location is not None
        for email, password in credentials.items():
            user = db.session.scalar(select(User).where(User.email == email))
            assert user is not None
            assert user.role == UserRole.USER
            assert user.status == UserStatus.ACTIVE
            assert user.password_hash != password
            assert check_password_hash(user.password_hash, password)
            assert db.session.get(UserLocation, (user.id, location.id)) is not None
