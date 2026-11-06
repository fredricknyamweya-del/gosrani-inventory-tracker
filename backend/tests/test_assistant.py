"""Read-only inventory assistant endpoint tests."""

from datetime import date
from decimal import Decimal

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app.extensions import db
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
