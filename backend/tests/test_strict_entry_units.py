"""Regression tests for strict entry units and per-record bale contents."""

from datetime import date
from decimal import Decimal

from app.extensions import db
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
from flask_jwt_extended import create_access_token


def create_case(client):
    admin = User(
        name="Unit Admin",
        email="unit-admin@example.com",
        password_hash="not-a-real-password-hash",
        role=UserRole.ADMIN,
    )
    location = Location(code="ELD", name="Eldoret Godown")
    category = Category(name="Unit Test Products")
    db.session.add_all([admin, location, category])
    db.session.flush()
    bale_item = Item(
        category_id=category.id,
        name="Test Pillow",
        unit=StockUnit.PCS,
        entry_unit=EnteredUnit.BALE,
    )
    piece_item = Item(
        category_id=category.id,
        name="Test Case",
        unit=StockUnit.PCS,
        entry_unit=EnteredUnit.PCS,
    )
    kg_item = Item(
        category_id=category.id,
        name="Test Fibre",
        unit=StockUnit.KG,
        entry_unit=EnteredUnit.KG,
    )
    db.session.add_all([bale_item, piece_item, kg_item])
    db.session.flush()
    bale_spec = Specification(
        item_id=bale_item.id,
        label="Standard",
        pack_size=20,
    )
    no_standard_spec = Specification(
        item_id=bale_item.id,
        label="Custom",
        pack_size=None,
    )
    piece_spec = Specification(item_id=piece_item.id, label="Standard")
    kg_spec = Specification(item_id=kg_item.id, label="Standard")
    db.session.add_all([bale_spec, no_standard_spec, piece_spec, kg_spec])
    db.session.add(UserLocation(user_id=admin.id, location_id=location.id))
    db.session.commit()
    token = create_access_token(identity=str(admin.id))
    return {
        "authorization": {"Authorization": f"Bearer {token}"},
        "admin": admin,
        "location": location,
        "category": category,
        "bale_item": bale_item,
        "bale_spec": bale_spec,
        "no_standard_spec": no_standard_spec,
        "piece_item": piece_item,
        "piece_spec": piece_spec,
        "kg_item": kg_item,
        "kg_spec": kg_spec,
    }


def payload(item, size, **overrides):
    return {
        "date": date.today().isoformat(),
        "category": "Unit Test Products",
        "item": item,
        "size": size,
        "quantityIn": 1,
        "handledBy": "Stock handler",
        **overrides,
    }


def test_bale_entry_stores_base_pieces_and_reports_record_and_stock_displays(client):
    case = create_case(client)

    response = client.post(
        "/api/inventory",
        json=payload("Test Pillow", "Standard", quantityIn=10, piecesPerBale=20),
        headers=case["authorization"],
    )

    assert response.status_code == 201
    record = response.json["data"][0]
    assert record["quantityIn"] == 200
    assert record["normalizedQuantityIn"] == 200
    assert record["piecesPerBale"] == 20
    assert record["balesIn"] == 10
    assert record["quantityInDisplay"] == "10 bales x 20 pcs = 200 pcs"

    stock = client.get(
        f"/api/inventory/{record['id']}/stock",
        headers=case["authorization"],
    )
    assert stock.json["data"]["display"] == "10 bales (200 pcs)"
    assert stock.json["data"]["stockBales"] == 10
    assert stock.json["data"]["stockPieces"] == 200


def test_bale_entry_uses_standard_pack_and_warns_when_override_differs(client):
    case = create_case(client)

    default_response = client.post(
        "/api/inventory",
        json=payload("Test Pillow", "Standard", quantityIn=2),
        headers=case["authorization"],
    )
    assert default_response.status_code == 201
    assert default_response.json["data"][0]["piecesPerBale"] == 20

    validation = client.post(
        "/api/inventory/validate",
        json=payload(
            "Test Pillow",
            "Standard",
            quantityIn=1,
            piecesPerBale=24,
        ),
        headers=case["authorization"],
    )
    flags = validation.json["data"]["warnings"][0]["flags"]
    assert {
        "field": "piecesPerBale",
        "message": "This bale holds 24 pieces; the catalogue standard is 20.",
    } in flags


def test_bale_entry_requires_contents_without_a_standard_pack(client):
    case = create_case(client)

    response = client.post(
        "/api/inventory",
        json=payload("Test Pillow", "Custom", quantityIn=1),
        headers=case["authorization"],
    )

    assert response.status_code == 422
    assert response.json["errors"][0]["message"] == (
        "Enter how many pieces are in each bale."
    )


def test_strict_units_reject_mismatches_and_allow_kg_precision(client):
    case = create_case(client)

    bale_as_pieces = client.post(
        "/api/inventory",
        json=payload(
            "Test Pillow",
            "Standard",
            quantityIn=1,
            enteredUnit="PCS",
        ),
        headers=case["authorization"],
    )
    pieces_as_bales = client.post(
        "/api/inventory",
        json=payload(
            "Test Case",
            "Standard",
            quantityIn=1,
            enteredUnit="BALE",
        ),
        headers=case["authorization"],
    )
    kilograms = client.post(
        "/api/inventory",
        json=payload("Test Fibre", "Standard", quantityIn="22.816"),
        headers=case["authorization"],
    )

    assert bale_as_pieces.status_code == 422
    assert "Test Pillow is entered in bales." in str(bale_as_pieces.json)
    assert pieces_as_bales.status_code == 422
    assert "Test Case is entered in pieces." in str(pieces_as_bales.json)
    assert kilograms.status_code == 201
    assert kilograms.json["data"][0]["quantityIn"] == 22.816


def test_mixed_bale_sizes_report_both_stock_measures_and_edits_reconvert(client):
    case = create_case(client)

    created = client.post(
        "/api/inventory",
        json=payload("Test Pillow", "Standard", quantityIn=2, piecesPerBale=20),
        headers=case["authorization"],
    )
    record = created.json["data"][0]
    updated = client.patch(
        f"/api/inventory/{record['id']}",
        json={"quantityIn": 2, "piecesPerBale": 24},
        headers=case["authorization"],
    )
    second = client.post(
        "/api/inventory",
        json=payload("Test Pillow", "Standard", quantityIn=1, piecesPerBale=20),
        headers=case["authorization"],
    )

    assert updated.status_code == 200
    assert updated.json["data"]["quantityIn"] == 48
    assert updated.json["data"]["balesIn"] == 2
    assert second.status_code == 201
    stock = client.get(
        f"/api/inventory/{record['id']}/stock",
        headers=case["authorization"],
    )
    assert stock.json["data"]["display"] == "3 bales (68 pcs)"
    assert stock.json["data"]["stockBales"] == 3


def test_legacy_bale_record_uses_standard_and_stocks_remain_specification_scoped(client):
    case = create_case(client)
    legacy = InventoryRecord(
        location_id=case["location"].id,
        record_date=date.today(),
        specification_id=case["bale_spec"].id,
        qty_in=Decimal(40),
        qty_out=None,
        entered_unit=EnteredUnit.BALE,
        pieces_per_unit=1,
        pieces_per_bale=None,
        status=RecordStatus.LOCKED,
        created_by=case["admin"].id,
    )
    other_spec = Specification(
        item_id=case["bale_item"].id,
        label="Other",
        pack_size=10,
    )
    db.session.add(other_spec)
    db.session.flush()
    db.session.add(
        InventoryRecord(
            location_id=case["location"].id,
            record_date=date.today(),
            specification_id=other_spec.id,
            qty_in=Decimal(500),
            qty_out=None,
            entered_unit=EnteredUnit.BALE,
            pieces_per_unit=1,
            status=RecordStatus.LOCKED,
            created_by=case["admin"].id,
        )
    )
    db.session.add(legacy)
    db.session.commit()

    record_response = client.get(
        f"/api/inventory/{legacy.id}",
        headers=case["authorization"],
    )
    stock_response = client.get(
        f"/api/inventory/{legacy.id}/stock",
        headers=case["authorization"],
    )

    assert record_response.json["data"]["quantityInDisplay"] == (
        "2 bales x 20 pcs = 40 pcs"
    )
    assert stock_response.json["data"]["quantity"] == 40
