"""API error and request security tests."""

import pytest
from flask import abort

from app.errors import validation_error


@pytest.fixture()
def error_routes(app):
    @app.get("/api/test-errors/<int:status>")
    def raise_http_error(status):
        abort(status)

    @app.get("/api/test-errors/method")
    def method_error():
        return {"data": True}

    @app.get("/api/test-errors/validation")
    def validation_route():
        return validation_error([{"field": "email", "message": "Enter a valid email."}])

    return app.test_client()


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (400, "bad_request"),
        (401, "unauthorized"),
        (403, "forbidden"),
        (404, "not_found"),
        (409, "conflict"),
        (412, "precondition_failed"),
        (415, "unsupported_media_type"),
        (422, "validation_error"),
        (429, "rate_limited"),
        (500, "internal_server_error"),
        (503, "service_unavailable"),
    ],
)
def test_http_errors_use_standard_envelope(error_routes, status, code):
    response = error_routes.get(f"/api/test-errors/{status}")

    assert response.status_code == status
    assert set(response.json) == (
        {"message", "code", "errors"} if status == 422 else {"message", "code"}
    )
    assert response.json["code"] == code
    assert response.json["message"]
    if status == 429:
        assert response.headers["Retry-After"]


def test_method_not_allowed_uses_standard_envelope(error_routes):
    response = error_routes.post("/api/test-errors/method")

    assert response.status_code == 405
    assert response.json["code"] == "method_not_allowed"


def test_malformed_json_is_a_friendly_400(error_routes):
    response = error_routes.post(
        "/api/test-errors/400",
        data='{"broken":',
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json["code"] == "malformed_json"
    assert "JSON" in response.json["message"]


def test_non_json_body_is_rejected(error_routes):
    response = error_routes.post(
        "/api/test-errors/400",
        data="payload",
        content_type="text/plain",
    )

    assert response.status_code == 415
    assert response.json["code"] == "unsupported_media_type"


def test_validation_error_contains_field_errors(error_routes):
    response = error_routes.get("/api/test-errors/validation")

    assert response.status_code == 422
    assert response.json["errors"] == [
        {"field": "email", "message": "Enter a valid email."}
    ]


def test_security_headers_and_request_id_are_present(client):
    response = client.get("/api/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "same-origin"
    assert response.headers["X-Request-ID"]
