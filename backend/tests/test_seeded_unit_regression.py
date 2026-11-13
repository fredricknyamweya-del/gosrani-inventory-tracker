"""End-to-end unit regressions for every specification in the seed catalog."""

from datetime import date
from decimal import Decimal

import pytest
from flask_jwt_extended import create_access_token
from sqlalchemy import select

from app.extensions import db
from app.models import (
    Category,
    EnteredUnit,
    InventoryRecord,
    Item,
    Specification,
    StockUnit,
    User,
)
from app.seed import CATALOG

BALE_CATEGORIES = {"pillows", "duvets", "blankets"}
PCS_CATEGORIES = {"sofa sets", "mattresses", "cushions"}
BALE_ITEMS = {
    "woolen duvet",
    "plain school bedcovers - heavy",
    "white pillow case",
}
PCS_ITEMS = {"duvet bags", "pillow kiss case"}
UNLISTED_ITEMS = {
    "bedcover 60x80",
    "fibre",
    "pillow individual packaging bags",
    "pillow (10 pc) packaging polythene bags",
}

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
    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed"])
    assert result.exit_code == 0, result.output
    with app.app_context():
        admin = db.session.scalar(
            select(User).where(User.email == "admin@example.com")
        )
        return {"Authorization": f"Bearer {create_access_token(identity=str(admin.id))}"}


def apply_unit_policy(app):
    result = app.test_cli_runner().invoke(args=["apply-unit-policy", "--apply"])
    assert result.exit_code == 0, result.output
    return result.output


def expected_policy_unit(category_name, item_name):
    category_key = category_name.casefold()
    item_key = item_name.casefold()
    if item_key in BALE_ITEMS:
        return EnteredUnit.BALE
    if item_key in PCS_ITEMS:
        return EnteredUnit.PCS
    if category_key in BALE_CATEGORIES and item_key != "duvet bags":
        return EnteredUnit.BALE
    if category_key in PCS_CATEGORIES:
        return EnteredUnit.PCS
    return None


def post_entry(
    client,
    headers,
    category,
    item,
    size,
    entry_unit,
    *,
    quantity_in,
    pieces_per_bale=None,
):
    payload = {
        "date": date.today().isoformat(),
        "category": category,
        "item": item,
        "size": size,
        "quantityIn": quantity_in,
        "handledBy": "Regression test",
    }
    if pieces_per_bale is not None:
        payload["piecesPerBale"] = pieces_per_bale
    if entry_unit is not None:
        payload["enteredUnit"] = entry_unit.value
    response = client.post("/api/inventory", json=payload, headers=headers)
    assert response.status_code == 201, response.json
    return response.json["data"][0]


def get_stock(client, headers, record_id):
    response = client.get(
        f"/api/inventory/{record_id}/stock",
        headers=headers,
    )
    assert response.status_code == 200, response.json
    return response.json["data"]


def test_seeded_catalog_units_follow_explicit_policy_and_leave_unlisted_unchanged(
    app, monkeypatch
):
    seed_catalog(app, monkeypatch)
    with app.app_context():
        initial = {
            (category.name, item.name): item.entry_unit
            for item, category in db.session.execute(
                select(Item, Category).join(Category, Item.category_id == Category.id)
            )
        }
    dry_run = app.test_cli_runner().invoke(args=["apply-unit-policy"])
    assert dry_run.exit_code == 0, dry_run.output
    assert "dry run" in dry_run.output.lower()
    assert "UNMATCHED item: Plain School Bedcovers - Heavy" in dry_run.output

    output = apply_unit_policy(app)
    assert "Updated " in output
    with app.app_context():
        items = db.session.execute(
            select(Item, Category).join(Category, Item.category_id == Category.id)
        ).all()
        observed_names = {
            (category.name.casefold(), item.name.casefold())
            for item, category in items
        }
        for item, category in items:
            target = expected_policy_unit(category.name, item.name)
            if target is not None:
                assert item.entry_unit == target, (category.name, item.name)
            elif item.name.casefold() in UNLISTED_ITEMS:
                assert item.entry_unit == initial[(category.name, item.name)]
        assert all(item.entry_unit in EnteredUnit for item, _ in items)
        assert ("sofa sets", "any item") not in observed_names


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
    apply_unit_policy(app)
    with app.app_context():
        item = db.session.scalar(
            select(Item)
            .join(Specification)
            .join(Category)
            .where(
                Category.name == category,
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
        entry_unit = item.entry_unit

    if entry_unit == EnteredUnit.BALE:
        pieces_per_bale = pack_size or 12
        expected_pieces = 2 * pieces_per_bale
        record = post_entry(
            client,
            headers,
            category,
            item_name,
            size,
            entry_unit,
            quantity_in=2,
            pieces_per_bale=pieces_per_bale,
        )
        expected_record_display = (
            f"2 bales x {pieces_per_bale} pcs = {expected_pieces} pcs"
        )
        expected_stock_display = f"2 bales ({expected_pieces} pcs)"
        assert record["quantityIn"] == expected_pieces
        assert record["balesIn"] == 2
        assert record["piecesPerBale"] == pieces_per_bale
        assert record["quantityInDisplay"] == expected_record_display
    elif entry_unit == EnteredUnit.KG:
        expected_pieces = 2.5
        record = post_entry(
            client,
            headers,
            category,
            item_name,
            size,
            entry_unit,
            quantity_in=expected_pieces,
        )
        expected_record_display = "2.5 kg"
        expected_stock_display = expected_record_display
        assert record["quantityIn"] == expected_pieces
        assert record["piecesPerBale"] is None
        assert record["balesIn"] is None
    else:
        expected_pieces = 3
        record = post_entry(
            client,
            headers,
            category,
            item_name,
            size,
            entry_unit,
            quantity_in=expected_pieces,
        )
        expected_record_display = "3 pcs"
        expected_stock_display = expected_record_display
        assert record["quantityIn"] == expected_pieces
        assert record["piecesPerBale"] is None
        assert record["balesIn"] is None

    assert record["entryUnit"] == entry_unit.value
    assert record["quantityInDisplay"] == expected_record_display
    with app.app_context():
        stored = db.session.get(InventoryRecord, int(record["id"]))
        assert stored is not None
        assert stored.specification_id == specification.id
        assert stored.qty_in == Decimal(str(expected_pieces))

    stock = get_stock(client, headers, record["id"])
    assert Decimal(str(stock["quantity"])) == Decimal(str(expected_pieces))
    assert stock["display"] == expected_stock_display
    if stock_unit == StockUnit.KG:
        assert stock["stockBales"] is None
    elif entry_unit == EnteredUnit.BALE:
        assert stock["stockPieces"] == expected_pieces
        assert stock["stockBales"] == 2
    else:
        assert stock["stockPieces"] == expected_pieces
        assert stock["stockBales"] is None


def test_pillow_goldstar_and_mattress_examples_use_the_configured_unit(
    client, app, monkeypatch
):
    headers = seed_catalog(app, monkeypatch)
    apply_unit_policy(app)
    examples = [
        ("Pillows", "Pillow", "600g", EnteredUnit.BALE, 10),
        (
            "Blankets",
            "Goldstar Blanket (BF)",
            "54x80 2ST",
            EnteredUnit.BALE,
            20,
        ),
        ("Mattresses", "HDF", "36x4", EnteredUnit.PCS, None),
    ]
    for category, item, size, unit, pack_size in examples:
        record = post_entry(
            client,
            headers,
            category,
            item,
            size,
            unit,
            quantity_in=2,
            pieces_per_bale=pack_size,
        )
        assert record["entryUnit"] == unit.value
        if unit == EnteredUnit.BALE:
            assert record["quantityIn"] == 2 * pack_size
            assert record["quantityInDisplay"] == (
                f"2 bales x {pack_size} pcs = {2 * pack_size} pcs"
            )
        else:
            assert record["quantityIn"] == 2
            assert record["quantityInDisplay"] == "2 pcs"
