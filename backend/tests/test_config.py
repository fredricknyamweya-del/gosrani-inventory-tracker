"""Database URL and PostgreSQL configuration tests."""

import pytest
from sqlalchemy.engine import make_url

from app.config import ProductionConfig, _database_engine_options, _database_url


@pytest.mark.parametrize(
    "database_url",
    [
        "postgres://user:secret@db.example.test:5432/inventory",
        "postgresql://user:secret@db.example.test:5432/inventory",
        "postgresql+psycopg://user:secret@db.example.test:5432/inventory",
    ],
)
def test_postgres_urls_use_psycopg(database_url):
    normalized = make_url(_database_url(database_url))

    assert normalized.drivername == "postgresql+psycopg"
    assert normalized.username == "user"
    assert normalized.password == "secret"
    assert normalized.host == "db.example.test"
    assert normalized.database == "inventory"


def test_production_postgres_url_requires_tls_when_not_specified():
    normalized = make_url(
        _database_url(
            "postgresql://user:secret@db.example.test/inventory",
            require_ssl=True,
        )
    )

    assert normalized.query["sslmode"] == "require"


def test_production_postgres_url_preserves_explicit_tls_mode():
    normalized = make_url(
        _database_url(
            "postgresql://user:secret@db.example.test/inventory?sslmode=verify-full",
            require_ssl=True,
        )
    )

    assert normalized.query["sslmode"] == "verify-full"


def test_pool_settings_are_bounded_and_only_applied_to_postgres():
    options = _database_engine_options(
        "postgresql+psycopg://user:secret@db.example.test/inventory"
    )

    assert options == {
        "pool_size": 5,
        "max_overflow": 5,
        "pool_timeout": 30,
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }
    assert _database_engine_options("sqlite:///:memory:") == {}


def test_production_refuses_sqlite_database(monkeypatch):
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "s" * 32)
    monkeypatch.setattr(ProductionConfig, "JWT_SECRET_KEY", "j" * 32)
    monkeypatch.setattr(
        ProductionConfig, "SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:"
    )

    from app import create_app

    with pytest.raises(RuntimeError, match="Production requires DATABASE_URL"):
        create_app("production")
