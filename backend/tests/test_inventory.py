"""Tests for inventory record validation."""

from datetime import date, datetime
from decimal import Decimal

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.inventory import _resolve_record
from app.models import (
    Category,
    EnteredUnit,
    InventoryRecord,
    Item,
    Location,
    RecordStatus,
    Specification,
    StockUnit,
    User,
    UserLocation,
    UserRole,
)


def inventory_payload(handled_by="Stock handler"):
    return {
        "date": date.today().isoformat(),
        "category": "Bedding",
        "item": "Duvet",
        "size": "4x6",
        "quantityIn": 4,
        "handledBy": handled_by,
    }


def create_catalog():
    category = Category(name="Bedding")
    db.session.add(category)
    db.session.flush()
    item = Item(category_id=category.id, name="Duvet")
    db.session.add(item)
    db.session.flush()
    db.session.add(Specification(item_id=item.id, label="4x6"))
    db.session.commit()


def create_stock_case(*, unit=StockUnit.PCS, pack_size=None):
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
    other_location = Location(code="NAK", name="Nakuru Godown")
    category = Category(name="Cushions")
    db.session.add_all([admin, user, location, other_location, category])
    db.session.flush()
    item = Item(category_id=category.id, name="V SHD Cushion", unit=unit)
    db.session.add(item)
    db.session.flush()
    specification = Specification(
        item_id=item.id,
        label="Quilted",
        pack_size=pack_size,
    )
    other_specification = Specification(item_id=item.id, label="Plain")
    db.session.add_all([specification, other_specification])
    db.session.flush()
    db.session.add_all([
        UserLocation(user_id=admin.id, location_id=location.id),
        UserLocation(user_id=user.id, location_id=location.id),
    ])
    db.session.commit()
    return admin, user, location, other_location, item, specification, other_specification


def add_record(user, location, specification, *, quantity_in=None, quantity_out=None, deleted_at=None, record_date=None):
    record = InventoryRecord(
        location_id=location.id,
        record_date=record_date or date.today(),
        specification_id=specification.id,
        qty_in=Decimal(str(quantity_in)) if quantity_in is not None else None,
        qty_out=Decimal(str(quantity_out)) if quantity_out is not None else None,
        entered_unit=EnteredUnit.PCS,
        status=RecordStatus.LOCKED,
        created_by=user.id,
        deleted_at=deleted_at,
    )
    db.session.add(record)
    db.session.flush()
    return record


def authorization(user):
    token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}


def test_inventory_validation_requires_a_handler_name(app):
    create_catalog()

    values, errors = _resolve_record(inventory_payload(handled_by="  "))

    assert values is None
    assert errors == [{
        "field": "handledBy",
        "message": "The name of the person who handled the stock is required.",
    }]


def test_inventory_validation_normalizes_handler_name(app):
    create_catalog()

    values, errors = _resolve_record(inventory_payload(handled_by="  Stock handler  "))

    assert errors == []
    assert values["handledBy"] == "Stock handler"


def test_stock_endpoint_scopes_totals_to_record_location_and_specification(client):
    admin, _, location, other_location, _, specification, other_specification = create_stock_case(pack_size=10)
    record = add_record(
        admin,
        location,
        specification,
        quantity_in=800,
        record_date=date(2020, 1, 1),
    )
    add_record(admin, location, specification, quantity_in=200, record_date=date(2026, 11, 12))
    add_record(admin, location, specification, quantity_out=300, record_date=date(2019, 1, 1))
    add_record(
        admin,
        location,
        specification,
        quantity_in=500,
        deleted_at=datetime(2026, 1, 1),
    )
    add_record(admin, other_location, specification, quantity_in=10_000)
    add_record(admin, location, other_specification, quantity_in=9_000)
    db.session.commit()

    response = client.get(
        f"/api/inventory/INV-{record.id:06d}/stock",
        headers=authorization(admin),
    )

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json["data"] == {
        "quantity": 700.0,
        "unit": "PCS",
        "packSize": 10,
        "display": "70 bales",
        "locationId": str(location.id),
        "locationName": "Eldoret Godown",
        "specificationId": str(specification.id),
        "itemName": "V SHD Cushion",
        "sizeLabel": "Quilted",
        "asOf": response.json["data"]["asOf"],
    }
    assert response.json["data"]["asOf"].endswith("Z")


def test_stock_endpoint_formats_packs_kilograms_negative_and_zero(client):
    admin, _, location, _, item, specification, plain_specification = create_stock_case(pack_size=10)
    record = add_record(admin, location, specification, quantity_in=998)
    db.session.commit()
    response = client.get(
        f"/api/inventory/{record.id}/stock",
        headers=authorization(admin),
    )
    assert response.json["data"]["display"] == "99 bales + 8 pcs"

    kg_item = Item(category_id=item.category_id, name="Cotton", unit=StockUnit.KG)
    db.session.add(kg_item)
    db.session.flush()
    kg_specification = Specification(
        item_id=kg_item.id,
        label="One kg",
        pack_size=None,
    )
    db.session.add(kg_specification)
    db.session.flush()
    kg_record = add_record(admin, location, kg_specification, quantity_in=22_816)
    db.session.commit()
    kg_response = client.get(
        f"/api/inventory/{kg_record.id}/stock",
        headers=authorization(admin),
    )
    assert kg_response.json["data"]["display"] == "22,816 kg"

    kg_record.qty_out = Decimal("22,916")
    db.session.commit()
    negative_response = client.get(
        f"/api/inventory/{kg_record.id}/stock",
        headers=authorization(admin),
    )
    assert negative_response.json["data"]["quantity"] == -100.0
    assert negative_response.json["data"]["display"] == "-100 kg"

    zero_record = add_record(admin, location, plain_specification, quantity_in=100)
    add_record(admin, location, plain_specification, quantity_out=100)
    db.session.commit()
    zero_response = client.get(
        f"/api/inventory/{zero_record.id}/stock",
        headers=authorization(admin),
    )
    assert zero_response.json["data"]["quantity"] == 0.0
    assert zero_response.json["data"]["display"] == "0 PCS"


def test_stock_endpoint_restricts_users_and_hides_unknown_or_deleted_records(client):
    admin, user, location, _, _, specification, _ = create_stock_case()
    record = add_record(admin, location, specification, quantity_in=10)
    deleted_record = add_record(
        admin,
        location,
        specification,
        quantity_in=10,
        deleted_at=datetime.now(),
    )
    db.session.commit()

    forbidden = client.get(
        f"/api/inventory/{record.id}/stock",
        headers=authorization(user),
    )
    assert forbidden.status_code == 403
    assert forbidden.headers["Cache-Control"] == "no-store"

    for identifier in (record.id + 1000, f"INV-{deleted_record.id:06d}", "INV-999999"):
        missing = client.get(
            f"/api/inventory/{identifier}/stock",
            headers=authorization(admin),
        )
        assert missing.status_code == 404
        assert missing.headers["Cache-Control"] == "no-store"


def test_record_detail_response_remains_unchanged(client):
    admin, _, location, _, _, specification, _ = create_stock_case()
    record = add_record(admin, location, specification, quantity_in=10)
    db.session.commit()

    response = client.get(
        f"/api/inventory/{record.id}",
        headers=authorization(admin),
    )

    assert response.status_code == 200
    assert set(response.json["data"]) == {
        "id",
        "locationId",
        "date",
        "category",
        "item",
        "size",
        "quantityIn",
        "quantityOut",
        "handledBy",
        "enteredUnit",
        "details",
        "addedBy",
        "modifiedBy",
        "createdAt",
        "status",
    }
    assert "stock" not in response.json["data"]
    assert response.headers.get("ETag") is None
