"""Tests for product-specific bale inventory and catalogue summaries."""

from datetime import date

from flask_jwt_extended import create_access_token
from sqlalchemy import select

from app.extensions import db
from app.models import (
    Category,
    InventoryUnit,
    Item,
    Location,
    Specification,
    User,
    UserLocation,
    UserRole,
)


def create_case(*, inventory_unit=InventoryUnit.BALE, pieces_per_bale=5):
    admin = User(
        name="Inventory Admin",
        email="admin@example.com",
        password_hash="not-a-real-password-hash",
        role=UserRole.ADMIN,
    )
    user = User(
        name="Inventory User",
        email="user@example.com",
        password_hash="not-a-real-password-hash",
        role=UserRole.USER,
    )
    location = Location(code="ELD", name="Eldoret Godown")
    category = Category(name="Bedding")
    db.session.add_all([admin, user, location, category])
    db.session.flush()
    item = Item(
        category_id=category.id,
        name="Configured Duvet",
        inventory_unit=inventory_unit,
        pieces_per_bale=pieces_per_bale,
    )
    ordinary_item = Item(
        category_id=category.id,
        name="Pillow Kiss Case",
        inventory_unit=InventoryUnit.PCS,
    )
    db.session.add_all([item, ordinary_item])
    db.session.flush()
    specification = Specification(item_id=item.id, label="4x6")
    ordinary_specification = Specification(
        item_id=ordinary_item.id, label="Standard"
    )
    db.session.add_all([specification, ordinary_specification])
    db.session.add_all(
        [
            UserLocation(user_id=admin.id, location_id=location.id),
            UserLocation(user_id=user.id, location_id=location.id),
        ]
    )
    db.session.commit()
    return admin, user, location, category, item, specification, ordinary_item, ordinary_specification


def authorization(user):
    token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}


def transaction_payload(item_name, size, **overrides):
    return {
        "date": date.today().isoformat(),
        "category": "Bedding",
        "item": item_name,
        "size": size,
        "quantityIn": 1,
        "handledBy": "Stock handler",
        **overrides,
    }


def test_bale_transactions_normalize_and_keep_the_original_unit(client):
    admin, _, _, _, _, specification, _, _ = create_case()

    received = client.post(
        "/api/inventory",
        json=transaction_payload("Configured Duvet", "4x6", quantityIn=5),
        headers=authorization(admin),
    )

    assert received.status_code == 201
    record = received.json["data"][0]
    assert record["quantityIn"] == 5
    assert record["enteredUnit"] == "BALE"
    assert record["piecesPerUnit"] == 5
    assert record["normalizedQuantityIn"] == 25

    issued = client.post(
        "/api/inventory",
        json=transaction_payload(
            "Configured Duvet",
            "4x6",
            quantityIn=None,
            quantityOut=2,
            enteredUnit="BALE",
        ),
        headers=authorization(admin),
    )
    assert issued.status_code == 201
    assert issued.json["data"][0]["normalizedQuantityOut"] == 10

    stock = client.get(
        f"/api/inventory/{record['id']}/stock",
        headers=authorization(admin),
    )
    assert stock.status_code == 200
    assert stock.json["data"]["unit"] == "BALE"
    assert stock.json["data"]["quantity"] == 3
    assert stock.json["data"]["equivalentPieces"] == 15
    assert stock.json["data"]["display"] == "3 bales"

    persisted = db.session.get(Specification, specification.id)
    assert persisted is not None


def test_bale_unit_is_enforced_and_stock_out_cannot_exceed_balance(client):
    admin, _, _, _, _, _, _, _ = create_case()
    received = client.post(
        "/api/inventory",
        json=transaction_payload("Configured Duvet", "4x6", quantityIn=1),
        headers=authorization(admin),
    )
    assert received.status_code == 201

    wrong_unit = client.post(
        "/api/inventory",
        json=transaction_payload(
            "Configured Duvet",
            "4x6",
            quantityIn=None,
            quantityOut=1,
            enteredUnit="PCS",
        ),
        headers=authorization(admin),
    )
    assert wrong_unit.status_code == 422
    assert "configured for BALE" in wrong_unit.json["errors"][0]["message"]

    excess = client.post(
        "/api/inventory",
        json=transaction_payload(
            "Configured Duvet",
            "4x6",
            quantityIn=None,
            quantityOut=2,
            enteredUnit="BALE",
        ),
        headers=authorization(admin),
    )
    assert excess.status_code == 422
    assert "available stock" in excess.json["errors"][0]["message"]


def test_catalogue_summary_includes_products_without_entries_and_converts_bales(client):
    admin, user, _, _, _, _, ordinary_item, _ = create_case()
    response = client.post(
        "/api/inventory",
        json=transaction_payload("Configured Duvet", "4x6", quantityIn=3),
        headers=authorization(admin),
    )
    assert response.status_code == 201

    summary = client.get(
        "/api/catalog/summary",
        headers=authorization(user),
    )

    assert summary.status_code == 200
    products = {row["productName"]: row for row in summary.json["data"]["products"]}
    assert products["Configured Duvet"]["totalStockIn"] == 3
    assert products["Configured Duvet"]["remainingStock"] == 3
    assert products["Configured Duvet"]["equivalentPieces"] == 15
    assert products["Configured Duvet"]["piecesPerBale"] == 5
    assert products["Configured Duvet"]["totalEntries"] == 1
    assert products["Pillow Kiss Case"]["remainingStock"] == 0
    assert products["Pillow Kiss Case"]["inventoryUnit"] == "PCS"
    assert summary.json["data"]["totals"]["registeredProducts"] == 2
    assert ordinary_item.inventory_unit == InventoryUnit.PCS


def test_admin_must_configure_pillow_conversion_and_users_cannot_edit_it(client):
    admin, user, _, category, _, _, _, _ = create_case(
        inventory_unit=InventoryUnit.PCS,
        pieces_per_bale=None,
    )
    pillow = Item(
        category_id=category.id,
        name="Pillow",
        inventory_unit=InventoryUnit.PCS,
    )
    db.session.add(pillow)
    db.session.flush()
    pillow_specification = Specification(item_id=pillow.id, label="Standard")
    db.session.add(pillow_specification)
    db.session.commit()

    invalid_update = client.patch(
        f"/api/catalog/items/{pillow.id}",
        json={"inventoryUnit": "BALE"},
        headers=authorization(admin),
    )
    assert invalid_update.status_code == 422

    forbidden_update = client.patch(
        f"/api/catalog/items/{pillow.id}",
        json={"inventoryUnit": "BALE", "piecesPerBale": 10},
        headers=authorization(user),
    )
    assert forbidden_update.status_code == 403

    configured = client.patch(
        f"/api/catalog/items/{pillow.id}",
        json={"inventoryUnit": "BALE", "piecesPerBale": 10},
        headers=authorization(admin),
    )
    assert configured.status_code == 200
    assert configured.json["data"]["inventoryUnit"] == "BALE"
    assert configured.json["data"]["piecesPerBale"] == 10

    transaction = client.post(
        "/api/inventory",
        json=transaction_payload("Pillow", "Standard", quantityIn=2),
        headers=authorization(user),
    )
    assert transaction.status_code == 201
    assert transaction.json["data"][0]["enteredUnit"] == "BALE"
    assert transaction.json["data"][0]["normalizedQuantityIn"] == 20


def test_catalog_create_requires_positive_whole_bale_rate(client):
    admin, _, _, category, _, _, _, _ = create_case()
    request_body = {
        "categoryId": str(category.id),
        "name": "New bale product",
        "specifications": ["Standard"],
        "inventoryUnit": "BALE",
        "piecesPerBale": 0,
    }

    rejected = client.post(
        "/api/catalog/items",
        json=request_body,
        headers=authorization(admin),
    )
    assert rejected.status_code == 422

    request_body["piecesPerBale"] = 4
    created = client.post(
        "/api/catalog/items",
        json=request_body,
        headers=authorization(admin),
    )
    assert created.status_code == 201
    assert created.json["data"]["inventoryUnit"] == "BALE"
    assert created.json["data"]["piecesPerBale"] == 4


def test_catalogue_summary_is_location_scoped(client):
    admin, user, location, category, item, specification, _, _ = create_case()
    unassigned_location = Location(code="NAK", name="Nakuru Godown")
    db.session.add(unassigned_location)
    db.session.flush()
    db.session.add(
        UserLocation(user_id=admin.id, location_id=unassigned_location.id)
    )
    from app.models import InventoryRecord, RecordStatus

    db.session.add(
        InventoryRecord(
            location_id=unassigned_location.id,
            record_date=date.today(),
            specification_id=specification.id,
            qty_in=2,
            qty_out=None,
            entered_unit="BALE",
            pieces_per_unit=5,
            qty_in_normalized=10,
            qty_out_normalized=None,
            handled_by="Admin",
            status=RecordStatus.SAVED,
            created_by=admin.id,
        )
    )
    db.session.commit()

    response = client.get(
        "/api/catalog/summary",
        headers=authorization(user),
    )

    assert response.status_code == 200
    configured = next(
        row
        for row in response.json["data"]["products"]
        if row["productName"] == item.name
    )
    assert configured["remainingStock"] == 0
    assert configured["totalEntries"] == 0
