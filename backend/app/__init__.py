"""Flask application factory."""

import os

from flask import Flask, jsonify
from flask_cors import CORS
from sqlalchemy.engine import make_url

from app import models as _models  # noqa: F401
from app.auth import auth_bp, register_jwt_callbacks
from app.config import CONFIGS
from app.errors import register_error_handlers
from app.extensions import cache, db, jwt, migrate
from app.security import configure_security


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    selected_config = config_name or os.getenv("APP_ENV", "development")
    app.config.from_object(CONFIGS.get(selected_config, CONFIGS["development"]))
    app.config["APP_ENV"] = selected_config
    app.config.from_pyfile("config.py", silent=True)
    if selected_config == "production" and not all(
        app.config.get(key) for key in ("SECRET_KEY", "JWT_SECRET_KEY")
    ):
        raise RuntimeError("SECRET_KEY and JWT_SECRET_KEY must be configured.")
    if selected_config == "production":
        database_url = make_url(app.config["SQLALCHEMY_DATABASE_URI"])
        if (
            database_url.get_backend_name() != "postgresql"
            or database_url.drivername != "postgresql+psycopg"
        ):
            raise RuntimeError(
                "Production requires DATABASE_URL to use PostgreSQL with psycopg."
            )
    configure_security(app)
    register_error_handlers(app)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    register_jwt_callbacks()
    cache.init_app(app)
    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
        allow_headers=[
            "Content-Type",
            "X-CSRF-TOKEN",
            "X-Location-Id",
            "If-Match",
            "If-None-Match",
        ],
        expose_headers=["ETag", "Location", "Retry-After"],
    )
    app.register_blueprint(auth_bp)

    @app.get("/api/health", strict_slashes=False)
    def health():
        response = jsonify({"data": {"status": "ok"}})
        response.headers["Cache-Control"] = "no-store"
        return response

    return app