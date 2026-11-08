"""Database URL and PostgreSQL configuration tests."""

import pytest
from sqlalchemy.engine import make_url

from app.config import (
    ProductionConfig,
    _cookie_samesite,
    _database_engine_options,
    _database_url,
    _testing_database_url,
)


@pytest.mark.parametrize("database_url", [None, ""])
def test_empty_test_database_url_uses_in_memory_sqlite(database_url):
    assert _testing_database_url(database_url) == "sqlite:///:memory:"


def test_test_database_url_preserves_configured_database():
    assert _testing_database_url("sqlite:///test.db") == "sqlite:///test.db"


def test_cookie_samesite_uses_default_and_environment_override(monkeypatch):
    monkeypatch.delenv("COOKIE_SAMESITE", raising=False)
    assert _cookie_samesite("None") == "None"

    monkeypatch.setenv("COOKIE_SAMESITE", "Lax")
    assert _cookie_samesite("None") == "Lax"


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


def test_production_postgres_url_rejects_disabled_tls():
    with pytest.raises(ValueError, match="must use TLS"):
        _database_url(
            "postgresql://user:secret@db.example.test/inventory?sslmode=disable",
            require_ssl=True,
        )


def test_unsupported_database_url_has_a_safe_error():
    with pytest.raises(ValueError, match="valid PostgreSQL or SQLite database URL"):
        _database_url("not a database URL")


def test_postgres_rejects_non_psycopg_drivers():
    with pytest.raises(ValueError, match="must use Psycopg 3"):
        _database_url("postgresql+psycopg2://user:secret@db.example.test/inventory")


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
