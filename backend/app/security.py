"""Request validation and security response headers."""

from uuid import uuid4

from flask import Flask, g, request
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import BadRequest

from app.errors import error_response

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def configure_security(app: Flask) -> None:
    """Apply proxy handling, JSON body requirements, and security headers."""
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_port=1,
        x_prefix=1,
    )
    app.url_map.strict_slashes = False

    @app.before_request
    def set_request_id_and_validate_body():
        g.request_id = str(uuid4())
        is_api_request = request.path == "/api" or request.path.startswith("/api/")
        if not is_api_request or request.method not in UNSAFE_METHODS:
            return None

        body = request.get_data(cache=True)
        if not body:
            return None
        if not request.is_json:
            return error_response(415)
        try:
            request.get_json(cache=True)
        except BadRequest:
            return error_response(
                400,
                "The request body contains malformed JSON.",
                "malformed_json",
            )
        return None

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        if app.config.get("APP_ENV") == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response
