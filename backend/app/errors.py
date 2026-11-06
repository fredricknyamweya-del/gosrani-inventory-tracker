"""JSON error responses for the API."""

import logging
from collections.abc import Mapping, Sequence

from flask import Flask, current_app, g, jsonify, request
from werkzeug.exceptions import BadRequest, HTTPException

logger = logging.getLogger(__name__)

HTTP_ERRORS = {
    400: ("bad_request", "The request could not be understood."),
    401: ("unauthorized", "Authentication is required."),
    403: ("forbidden", "You do not have permission to perform this action."),
    404: ("not_found", "The requested resource was not found."),
    405: ("method_not_allowed", "This method is not allowed for this resource."),
    409: ("conflict", "The request conflicts with the current resource state."),
    412: ("precondition_failed", "The resource has changed. Refresh and try again."),
    413: ("request_too_large", "The request body is too large."),
    415: ("unsupported_media_type", "Request bodies must use application/json."),
    422: ("validation_error", "Some submitted values are invalid."),
    429: ("rate_limited", "Too many requests. Please try again later."),
    500: ("internal_server_error", "An unexpected error occurred."),
    503: ("service_unavailable", "The service is temporarily unavailable."),
}


def error_response(
    status: int,
    message: str | None = None,
    code: str | None = None,
    errors: Sequence[Mapping[str, str]] | None = None,
    headers: Mapping[str, str] | None = None,
):
    """Build the standard API error envelope."""
    default_code, default_message = HTTP_ERRORS.get(
        status, ("http_error", "The request could not be completed.")
    )
    body = {
        "message": message or default_message,
        "code": code or default_code,
    }
    if errors is not None:
        body["errors"] = list(errors)
    response = jsonify(body)
    response.status_code = status
    for key, value in (headers or {}).items():
        response.headers[key] = value
    if status == 429 and "Retry-After" not in response.headers:
        response.headers["Retry-After"] = "60"
    request_id = getattr(g, "request_id", None)
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


def validation_error(
    errors: Sequence[Mapping[str, str]],
    message: str = "Some submitted values are invalid.",
):
    """Build a field-specific 422 response."""
    return error_response(
        422,
        message=message,
        code="validation_error",
        errors=errors,
    )


def register_error_handlers(app: Flask) -> None:
    """Register consistent API error handlers."""

    @app.errorhandler(BadRequest)
    def handle_bad_request(_error: BadRequest):
        return error_response(
            400,
            "The request body contains malformed JSON.",
            "malformed_json",
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        status = error.code or 500
        code, message = HTTP_ERRORS.get(
            status, ("http_error", "The request could not be completed.")
        )
        headers = {}
        if status == 429:
            retry_after = getattr(error, "retry_after", None)
            if retry_after is not None:
                headers["Retry-After"] = str(retry_after)
        return error_response(
            status,
            message=message,
            code=code,
            errors=[] if status == 422 else None,
            headers=headers,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_exception(_error: Exception):
        request_id = getattr(g, "request_id", "unknown")
        current_app.logger.error("Unhandled API error (request_id=%s)", request_id)
        return error_response(500)

    app.logger.addHandler(logging.NullHandler())

    @app.after_request
    def add_error_request_id(response):
        request_id = getattr(g, "request_id", None)
        if request_id:
            response.headers["X-Request-ID"] = request_id
        return response
