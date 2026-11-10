"""Read-only inventory assistant endpoint tests."""

import json
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.assistant import _normalized, _resolve_catalog_entity
from app.models import (
    AssistantQuery,
    Category,
    EnteredUnit,
    InventoryRecord,
    Item,
    Location,
    RecordStatus,
    Specification,
    User,
    UserLocation,
    UserRole,
)


def _create_user(role: UserRole) -> User:
    user = User(
        name="Inventory Admin",
        email=f"{role.value.lower()}@example.com",
        password_hash=generate_password_hash("test-password"),
        role=role,
    )
    db.session.add(user)
    db.session.flush()
    return user


def _authorization(user: User) -> dict[str, str]:
    token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}


def test_assistant_normalizes_dimensions_units_punctuation_and_plural_names():
    assert _normalized("  4 X 6, 4*6, 4 × 6  ") == "4x6 4x6 4x6"
    assert _normalized("BLS bales pcs pieces KGS kilograms") == (
        "bale bale pc pc kg kg"
    )
    assert _normalized("BEDCOVERS") == "bedcovers"


def test_assistant_resolves_partial_names_and_synonyms_without_guessing():
    categories = [(1, "Bedcovers"), (2, "Bedding")]
    items = [(1, "Pillow 600g"), (2, "Pillow 700g")]

    match, suggestions = _resolve_catalog_entity("bed covers", categories, "categories")
    assert match == categories[0]
    assert suggestions == []

    match, suggestions = _resolve_catalog_entity("Pillows", items, "items")
    assert match is None
    assert suggestions == ["Pillow 600g", "Pillow 700g"]


def test_assistant_requires_authentication(client):
    response = client.post("/api/assistant/query", json={"question": "show stock"})

    assert response.status_code == 401


def test_assistant_returns_matching_records_and_audits_query(client):
    user = _create_user(UserRole.ADMIN)
    location = Location(code="ELD", name="Eldoret")
    category = Category(name="Bedding")
    db.session.add_all([location, category])
    db.session.flush()
    item = Item(category_id=category.id, name="Vivo Mattress")
    db.session.add(item)
    db.session.flush()
    specification = Specification(item_id=item.id, label="72*60*6", is_default=True)
    db.session.add(specification)
    db.session.flush()
    db.session.add_all(
        [
            UserLocation(user_id=user.id, location_id=location.id),
            InventoryRecord(
                location_id=location.id,
                record_date=date(2026, 11, 5),
                specification_id=specification.id,
                qty_in=Decimal(10),
                qty_out=Decimal(2),
                entered_unit=EnteredUnit.PCS,
                details="Supplier delivery",
                status=RecordStatus.LOCKED,
                created_by=user.id,
            ),
        ]
    )
    db.session.commit()

    response = client.post(
        "/api/assistant/query",
        json={"question": "How much Vivo Mattress (72*60*6) is in stock?"},
        headers=_authorization(user),
    )

    assert response.status_code == 200
    assert response.json["data"]["answer"] == (
        "Recorded stock for Vivo Mattress (72*60*6) is 8."
    )
    assert response.json["data"]["records"][0]["details"] == "Supplier delivery"
    assert response.json["data"]["totalMatches"] == 1
    audit = db.session.query(AssistantQuery).one()
    assert audit.user_id == user.id
    assert audit.result_count == 1


def test_assistant_limits_stock_to_assigned_locations(client):
    user = _create_user(UserRole.ADMIN)
    location = Location(code="ELD", name="Eldoret")
    other_location = Location(code="NAK", name="Nakuru")
    category = Category(name="Bedding")
    db.session.add_all([location, other_location, category])
    db.session.flush()
    item = Item(category_id=category.id, name="Vivo Mattress")
    db.session.add(item)
    db.session.flush()
    specification = Specification(item_id=item.id, label="72*60*6", is_default=True)
    db.session.add(specification)
    db.session.flush()
    db.session.add_all(
        [
            UserLocation(user_id=user.id, location_id=location.id),
            InventoryRecord(
                location_id=location.id,
                record_date=date(2026, 11, 5),
                specification_id=specification.id,
                qty_in=Decimal(10),
                entered_unit=EnteredUnit.PCS,
                status=RecordStatus.LOCKED,
                created_by=user.id,
            ),
            InventoryRecord(
                location_id=other_location.id,
                record_date=date(2026, 11, 5),
                specification_id=specification.id,
                qty_in=Decimal(100),
                entered_unit=EnteredUnit.PCS,
                status=RecordStatus.LOCKED,
                created_by=user.id,
            ),
        ]
    )
    db.session.commit()

    response = client.post(
        "/api/assistant/query",
        json={"question": "How much Vivo Mattress (72*60*6) is in stock?"},
        headers=_authorization(user),
    )

    assert response.status_code == 200
    assert response.json["data"]["answer"] == (
        "Recorded stock for Vivo Mattress (72*60*6) is 10."
    )


def test_assistant_queries_item_stock_across_all_specifications(client):
    user = _create_user(UserRole.ADMIN)
    location = Location(code="ELD", name="Eldoret")
    other_location = Location(code="NAK", name="Nakuru")
    category = Category(name="Mattresses")
    db.session.add_all([location, other_location, category])
    db.session.flush()
    item = Item(category_id=category.id, name="HDF")
    db.session.add(item)
    db.session.flush()
    smaller_specification = Specification(
        item_id=item.id, label="36x4", is_default=True
    )
    larger_specification = Specification(item_id=item.id, label="48x4")
    db.session.add_all([smaller_specification, larger_specification])
    db.session.flush()
    db.session.add_all(
        [
            UserLocation(user_id=user.id, location_id=location.id),
            InventoryRecord(
                location_id=location.id,
                record_date=date(2026, 11, 5),
                specification_id=smaller_specification.id,
                qty_in=Decimal(12),
                qty_out=Decimal(2),
                entered_unit=EnteredUnit.PCS,
                status=RecordStatus.LOCKED,
                created_by=user.id,
            ),
            InventoryRecord(
                location_id=location.id,
                record_date=date(2026, 11, 5),
                specification_id=larger_specification.id,
                qty_in=Decimal(8),
                entered_unit=EnteredUnit.PCS,
                status=RecordStatus.LOCKED,
                created_by=user.id,
            ),
            InventoryRecord(
                location_id=other_location.id,
                record_date=date(2026, 11, 5),
                specification_id=larger_specification.id,
                qty_in=Decimal(100),
                entered_unit=EnteredUnit.PCS,
                status=RecordStatus.LOCKED,
                created_by=user.id,
            ),
        ]
    )
    db.session.commit()

    response = client.post(
        "/api/assistant/query",
        json={"question": "How much HDF is in stock across all sizes?"},
        headers=_authorization(user),
    )

    assert response.status_code == 200
    assert response.json["data"]["answer"] == (
        "Recorded stock for HDF is 18 across its specifications."
    )


def test_assistant_enforces_hourly_limit(client, app):
    app.config["ASSISTANT_HOURLY_LIMIT"] = 1
    user = _create_user(UserRole.ADMIN)
    db.session.commit()
    headers = _authorization(user)

    first = client.post(
        "/api/assistant/query",
        json={"question": "show unknown inventory"},
        headers=headers,
    )
    second = client.post(
        "/api/assistant/query",
        json={"question": "show unknown inventory"},
        headers=headers,
    )

    assert first.status_code == 200
    assert second.status_code == 429


def test_assistant_rejects_non_admin_users(client):
    user = _create_user(UserRole.USER)
    db.session.commit()

    response = client.post(
        "/api/assistant/query",
        json={"question": "show stock"},
        headers=_authorization(user),
    )

    assert response.status_code == 403


def test_assistant_validates_question_length(client):
    user = _create_user(UserRole.ADMIN)
    db.session.commit()

    response = client.post(
        "/api/assistant/query",
        json={"question": "x" * 501},
        headers=_authorization(user),
    )

    assert response.status_code == 422
    assert response.json["errors"][0]["field"] == "question"


def test_assistant_uses_openai_to_phrase_database_results(client, app, monkeypatch):
    user = _create_user(UserRole.ADMIN)
    db.session.commit()
    app.config["OPENAI_API_KEY"] = "test-api-key"
    sdk_client = Mock()
    sdk_client.responses.create.return_value = SimpleNamespace(
        output_text="There are no matching inventory records."
    )
    openai_factory = Mock(return_value=sdk_client)
    monkeypatch.setattr("app.assistant.OpenAI", openai_factory)

    response = client.post(
        "/api/assistant/query",
        json={"question": "show unknown inventory"},
        headers=_authorization(user),
    )

    assert response.status_code == 200
    assert (
        response.json["data"]["answer"]
        == "There are no matching inventory records."
    )
    openai_factory.assert_called_once_with(
        api_key="test-api-key", timeout=20.0, max_retries=0
    )
    request_payload = json.loads(sdk_client.responses.create.call_args.kwargs["input"])
    assert request_payload["question"] == "show unknown inventory"
    assert request_payload["totalMatches"] == 0
    assert request_payload["records"] == []


def test_assistant_reports_openai_failure(client, app, monkeypatch):
    user = _create_user(UserRole.ADMIN)
    db.session.commit()
    app.config["OPENAI_API_KEY"] = "test-api-key"
    sdk_client = Mock()
    sdk_client.responses.create.return_value = SimpleNamespace(output_text="")
    monkeypatch.setattr("app.assistant.OpenAI", Mock(return_value=sdk_client))

    response = client.post(
        "/api/assistant/query",
        json={"question": "show unknown inventory"},
        headers=_authorization(user),
    )

    assert response.status_code == 503
    assert response.json["message"] == (
        "The AI assistant is temporarily unavailable. Please try again."
    )
