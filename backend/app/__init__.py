"""Flask application factory."""

import os

from flask import Flask, jsonify
from flask_cors import CORS

from app import models as _models  # noqa: F401
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
    configure_security(app)
    register_error_handlers(app)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
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

    @app.get("/api/health", strict_slashes=False)
    def health():
        response = jsonify({"data": {"status": "ok"}})
        response.headers["Cache-Control"] = "no-store"
        return response

    return app