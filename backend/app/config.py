"""Application configuration loaded from the process environment."""

import os
import secrets
from pathlib import Path
from typing import ClassVar

from dotenv import load_dotenv
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")


def _database_url(value: str | None, *, require_ssl: bool = False) -> str:
    if not value:
        return f"sqlite:///{BACKEND_ROOT / 'instance' / 'gosrani.db'}"
    try:
        url = make_url(value)
    except ArgumentError:
        raise ValueError(
            "DATABASE_URL must be a valid PostgreSQL or SQLite database URL."
        ) from None
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg")
    if url.get_backend_name() not in {"postgresql", "sqlite"}:
        raise ValueError("DATABASE_URL must use PostgreSQL or SQLite.")
    if (
        url.get_backend_name() == "postgresql"
        and url.drivername != "postgresql+psycopg"
    ):
        raise ValueError("PostgreSQL DATABASE_URL must use Psycopg 3.")
    if require_ssl and url.get_backend_name() == "postgresql":
        sslmode = url.query.get("sslmode")
        if sslmode is None:
            url = url.update_query_dict({"sslmode": "require"})
        elif sslmode not in {"require", "verify-ca", "verify-full"}:
            raise ValueError("Production PostgreSQL connections must use TLS.")
    return url.render_as_string(hide_password=False)


def _database_engine_options(database_url: str) -> dict[str, object]:
    """Configure a bounded, health-checked pool for PostgreSQL."""
    if make_url(database_url).get_backend_name() != "postgresql":
        return {}
    return {
        "pool_size": 5,
        "max_overflow": 5,
        "pool_timeout": 30,
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }


def _testing_database_url(value: str | None) -> str:
    return value or "sqlite:///:memory:"


def _cookie_samesite(default: str) -> str:
    return os.getenv("COOKIE_SAMESITE", default)


class BaseConfig:
    """Settings shared by all runtime environments."""

    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(32)
    JWT_ALGORITHM = "HS256"
    SQLALCHEMY_DATABASE_URI = _database_url(os.getenv("DATABASE_URL"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS: ClassVar[dict[str, object]] = _database_engine_options(
        SQLALCHEMY_DATABASE_URI
    )
    JWT_TOKEN_LOCATION: ClassVar[list[str]] = ["headers", "cookies"]
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_COOKIE_HTTPONLY = True
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_MINUTES", "15")) * 60
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv("JWT_REFRESH_HOURS", "12")) * 60 * 60
    JWT_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    JWT_COOKIE_SAMESITE = _cookie_samesite("Lax")
    JWT_COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN") or None
    JWT_ACCESS_COOKIE_PATH = "/api"
    JWT_REFRESH_COOKIE_PATH = "/api/auth"
    JWT_ACCESS_CSRF_COOKIE_PATH = "/"
    JWT_REFRESH_CSRF_COOKIE_PATH = "/"
    JWT_COOKIE_CSRF_HEADER_NAME = "X-CSRF-TOKEN"
    CORS_ORIGINS: ClassVar[list[str]] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:8443,http://127.0.0.1:8443",
        ).split(",")
        if origin.strip()
    ]
    CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT", "60"))
    CACHE_TYPE = os.getenv("CACHE_TYPE", "SimpleCache")
    REDIS_URL = os.getenv("REDIS_URL")
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    LOGIN_MAX_FAILURES = int(os.getenv("LOGIN_MAX_FAILURES", "5"))
    LOGIN_LOCK_MINUTES = int(os.getenv("LOGIN_LOCK_MINUTES", "15"))
    ASSISTANT_HOURLY_LIMIT = int(os.getenv("ASSISTANT_HOURLY_LIMIT", "30"))
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    JSON_SORT_KEYS = True


class DevelopmentConfig(BaseConfig):
    """Local development settings."""

    DEBUG = True


class TestingConfig(BaseConfig):
    """Fast test settings using an in-memory database and no cache."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = _testing_database_url(os.getenv("TEST_DATABASE_URL"))
    SQLALCHEMY_ENGINE_OPTIONS: ClassVar[dict[str, object]] = {}
    JWT_TOKEN_LOCATION: ClassVar[list[str]] = ["headers", "cookies"]
    SECRET_KEY = "testing-only-secret"
    JWT_SECRET_KEY = "testing-only-jwt-secret-with-at-least-32-bytes"
    JWT_COOKIE_SECURE = False
    CACHE_TYPE = "NullCache"


class ProductionConfig(BaseConfig):
    """Production settings."""

    DEBUG = False
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_SAMESITE = _cookie_samesite("None")
    SQLALCHEMY_DATABASE_URI = _database_url(os.getenv("DATABASE_URL"), require_ssl=True)
    SQLALCHEMY_ENGINE_OPTIONS: ClassVar[dict[str, object]] = _database_engine_options(
        SQLALCHEMY_DATABASE_URI
    )


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
