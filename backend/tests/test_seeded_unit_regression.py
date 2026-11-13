"""End-to-end unit regressions for every specification in the seed catalog."""

from datetime import date
from decimal import Decimal

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import select

from app.extensions import db
from app.models import InventoryRecord, Item, Specification, StockUnit, User
from app.seed import BALE_PRODUCT_CONFIG, CATALOG


SEEDED_SPECIFICATIONS = [
    (category, item_name, label, pack_size, unit)
    for category, items in CATALOG
    for item_name, unit, specifications in items
    for label, pack_size in specifications
]


def seed_catalog(app, monkeypatch):
    monkeypatch.setenv("SEED_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("SEED_ADMIN_NAME", "Catalog Admin")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "seed-password")
    monkeypatch.setenv("DEFAULT_LOCATION_CODE", "ELD")
    monkeypatch.setenv("DEFAULT_LOCATION_NAME", "Eldoret Godown")
    result = app.test_cli_runner().invoke(args=["seed"])
    assert result.exit_code == 0, result.output
    with app.app_context():
        admin = db.session.scalar(
            select(User).where(User.email == "admin@example.com")
        )
        return {
            "Authorization": f"Bearer {create_access_token(identity=str(admin.id))}"
        }


def post_entry(client, headers, category, item, size, entered_unit, **quantities):
    response = client.post(
        "/api/inventory",
        json=[
            {
                "date": date.today().isoformat(),
                "category": category,
                "item": item,
                "size": size,
                "enteredUnit": entered_unit,
                "handledBy": "Regression test",
                **quantities,
            }
        ],
        headers=headers,
    )
    assert response.status_code == 201, response.json
    return response.json["data"][0]


def get_stock(client, headers, record_id):
    response = client.get(
        f"/api/inventory/{record_id}/stock",
        headers=headers,
    )
    assert response.status_code == 200, response.json
    return response.json["data"]


@pytest.mark.parametrize(
    ("category", "item_name", "size", "pack_size", "stock_unit"),
    SEEDED_SPECIFICATIONS,
    ids=[
        f"{category}-{item_name}-{size}"
        for category, item_name, size, _, _ in SEEDED_SPECIFICATIONS
    ],
)
def test_seeded_specification_entry_storage_stock_and_display(
    client,
    app,
    monkeypatch,
    category,
    item_name,
    size,
    pack_size,
    stock_unit,
):
    headers = seed_catalog(app, monkeypatch)
    with app.app_context():
        item = db.session.scalar(
            select(Item).join(Specification).where(
                Item.name == item_name,
                Specification.label == size,
            )
        )
        specification = db.session.scalar(
            select(Specification).where(
                Specification.item_id == item.id,
                Specification.label == size,
            )
        )

    last_record_id = None
    if pack_size is not None:
        bale_record = post_entry(
            client,
            headers,
            category,
            item_name,
            size,
            "BALE",
            quantityIn=2,
        )
        last_record_id = bale_record["id"]
        expected_bale_pieces = 2 * pack_size
        assert bale_record["enteredUnit"] == "BALE"
        assert bale_record["normalizedQuantityIn"] == expected_bale_pieces
        assert bale_record["quantityInDisplay"] == "2 bales"
        with app.app_context():
            stored = db.session.get(InventoryRecord, int(bale_record["id"]))
            assert stored.qty_in == Decimal(expected_bale_pieces)
            assert stored.qty_in_normalized == Decimal(expected_bale_pieces)
            assert stored.specification_id == specification.id
        stock = get_stock(client, headers, last_record_id)
        assert stock["quantity"] == expected_bale_pieces
        assert stock["display"] == "2 bales"
        assert stock["secondaryDisplay"] == (
            f"({expected_bale_pieces:,} pcs)"
        )

        piece_record = post_entry(
            client,
            headers,
            category,
            item_name,
            size,
            "PCS",
            quantityIn=3,
        )
        last_record_id = piece_record["id"]
        assert piece_record["normalizedQuantityIn"] == 3
        assert piece_record["quantityInDisplay"] == "3 pcs"
        stock = get_stock(client, headers, last_record_id)
        combined_pieces = expected_bale_pieces + 3
        assert stock["quantity"] == combined_pieces
        assert stock["display"] == (
            f"2 bales + 3 pcs"
        )
        assert stock["secondaryDisplay"] == f"({combined_pieces:,} pcs)"

        out_quantity = expected_bale_pieces + 4
        out_record = post_entry(
            client,
            headers,
            category,
            item_name,
            size,
            "PCS",
            quantityOut=out_quantity,
        )
        last_record_id = out_record["id"]
        assert out_record["normalizedQuantityOut"] == out_quantity
        stock = get_stock(client, headers, last_record_id)
        assert stock["quantity"] == -1
        assert stock["display"] == "-1 pc"
        assert stock["secondaryDisplay"] is None

        zero_record = post_entry(
            client,
            headers,
            category,
            item_name,
            size,
            "PCS",
            quantityIn=1,
        )
        last_record_id = zero_record["id"]
        stock = get_stock(client, headers, last_record_id)
        assert stock["quantity"] == 0
        assert stock["display"] == "0"
        assert stock["secondaryDisplay"] is None
        return

    entered_unit = stock_unit.value
    in_quantity = Decimal("2.5") if stock_unit == StockUnit.KG else Decimal(3)
    in_record = post_entry(
        client,
        headers,
        category,
        item_name,
        size,
        entered_unit,
        quantityIn=float(in_quantity),
    )
    last_record_id = in_record["id"]
    expected_display = "2.5 kg" if stock_unit == StockUnit.KG else "3 pcs"
    assert in_record["quantityInDisplay"] == expected_display
    with app.app_context():
        stored = db.session.get(InventoryRecord, int(in_record["id"]))
        assert stored.qty_in == in_quantity
        assert stored.qty_in_normalized == in_quantity
    stock = get_stock(client, headers, last_record_id)
    assert Decimal(str(stock["quantity"])) == in_quantity
    assert stock["display"] == expected_display

    out_quantity = Decimal("3") if stock_unit == StockUnit.KG else Decimal(4)
    out_record = post_entry(
        client,
        headers,
        category,
        item_name,
        size,
        entered_unit,
        quantityOut=float(out_quantity),
    )
    last_record_id = out_record["id"]
    stock = get_stock(client, headers, last_record_id)
    assert Decimal(str(stock["quantity"])) == Decimal("-0.5") if stock_unit == StockUnit.KG else -1
    assert stock["display"] == ("-0.5 kg" if stock_unit == StockUnit.KG else "-1 pc")

    zero_quantity = Decimal("0.5") if stock_unit == StockUnit.KG else Decimal(1)
    zero_record = post_entry(
        client,
        headers,
        category,
        item_name,
        size,
        entered_unit,
        quantityIn=float(zero_quantity),
    )
    stock = get_stock(client, headers, zero_record["id"])
    assert stock["quantity"] == 0
    assert stock["display"] == "0"


def test_bf_goldstar_54x80_2st_shows_415_bales_for_8300_pieces(
    client, app, monkeypatch
):
    headers = seed_catalog(app, monkeypatch)
    record = post_entry(
        client,
        headers,
        "Blankets",
        "Goldstar Blanket (BF)",
        "54x80 2ST",
        "BALE",
        quantityIn=415,
    )

    assert record["normalizedQuantityIn"] == 8300
    assert record["quantityInDisplay"] == "415 bales"
    assert record["quantityInSecondaryDisplay"] == "(8,300 pcs)"
    stock = get_stock(client, headers, record["id"])
    assert stock["display"] == "415 bales"
    assert stock["secondaryDisplay"] == "(8,300 pcs)"
