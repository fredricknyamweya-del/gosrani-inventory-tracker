"""Flask application factory."""

import os

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import CONFIGS
from app.extensions import cache, db, jwt, migrate


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    selected_config = config_name or os.getenv("APP_ENV", "development")
    app.config.from_object(CONFIGS.get(selected_config, CONFIGS["development"]))
    app.config.from_pyfile("config.py", silent=True)
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_port=1,
        x_prefix=1,
    )

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