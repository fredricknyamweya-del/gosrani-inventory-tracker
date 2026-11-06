"""Application configuration loaded from the process environment."""

import os
import secrets
from pathlib import Path
from typing import ClassVar

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT / ".env")


def _database_url(value: str | None) -> str:
    if not value:
        return f"sqlite:///{BACKEND_ROOT / 'instance' / 'gosrani.db'}"
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    return value


class BaseConfig:
    """Settings shared by all runtime environments."""

    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(32)
    JWT_ALGORITHM = "HS256"
    SQLALCHEMY_DATABASE_URI = _database_url(os.getenv("DATABASE_URL"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS: ClassVar[dict[str, object]] = (
        {}
        if SQLALCHEMY_DATABASE_URI.startswith("sqlite:")
        else {
            "pool_size": 5,
            "max_overflow": 5,
            "pool_pre_ping": True,
            "pool_recycle": 1800,
            "connect_args": {"sslmode": "require"},
        }
    )
    JWT_TOKEN_LOCATION: ClassVar[list[str]] = ["cookies"]
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_COOKIE_HTTPONLY = True
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_MINUTES", "15")) * 60
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv("JWT_REFRESH_HOURS", "12")) * 60 * 60
    JWT_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    JWT_COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")
    JWT_COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN") or None
    JWT_ACCESS_COOKIE_PATH = "/api"
    JWT_REFRESH_COOKIE_PATH = "/api/auth"
    JWT_COOKIE_CSRF_HEADER_NAME = "X-CSRF-TOKEN"
    CORS_ORIGINS: ClassVar[list[str]] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]
    CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT", "60"))
    CACHE_TYPE = os.getenv("CACHE_TYPE", "SimpleCache")
    REDIS_URL = os.getenv("REDIS_URL")
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
    LOGIN_MAX_FAILURES = int(os.getenv("LOGIN_MAX_FAILURES", "5"))
    LOGIN_LOCK_MINUTES = int(os.getenv("LOGIN_LOCK_MINUTES", "15"))
    JSON_SORT_KEYS = True


class DevelopmentConfig(BaseConfig):
    """Local development settings."""

    DEBUG = True


class TestingConfig(BaseConfig):
    """Fast test settings using an in-memory database and no cache."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_ENGINE_OPTIONS: ClassVar[dict[str, object]] = {}
    JWT_TOKEN_LOCATION: ClassVar[list[str]] = ["cookies", "headers"]
    SECRET_KEY = "testing-only-secret"
    JWT_SECRET_KEY = "testing-only-jwt-secret"
    JWT_COOKIE_SECURE = False
    CACHE_TYPE = "NullCache"


class ProductionConfig(BaseConfig):
    """Production settings."""

    DEBUG = False
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() == "true"


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
