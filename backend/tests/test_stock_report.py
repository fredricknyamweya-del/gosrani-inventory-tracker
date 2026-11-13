"""Tests for the read-only stock-report CLI command."""

import csv
from datetime import date
from io import StringIO

from sqlalchemy import func, select

from app.extensions import db
from app.models import (
    Category,
    EnteredUnit,
    InventoryRecord,
    Item,
    Location,
    Specification,
    User,
)


def seed_catalog(app, monkeypatch):
    monkeypatch.setenv("SEED_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("SEED_ADMIN_NAME", "Catalog Admin")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "seed-password")
    monkeypatch.setenv("DEFAULT_LOCATION_CODE", "ELD")
    monkeypatch.setenv("DEFAULT_LOCATION_NAME", "Eldoret Godown")
    result = app.test_cli_runner().invoke(args=["seed"])
    assert result.exit_code == 0, result.output


def test_stock_report_lists_base_stock_and_csv_without_writing(app, monkeypatch):
    seed_catalog(app, monkeypatch)
    with app.app_context():
        admin = db.session.scalar(
            select(User).where(User.email == "admin@example.com")
        )
        goldstar = db.session.scalar(
            select(Item).where(Item.name == "Goldstar Blanket (BF)")
        )
        specification = db.session.scalar(
            select(Specification).where(
                Specification.item_id == goldstar.id,
                Specification.label == "54x80 2ST",
            )
        )
        location = db.session.scalar(select(Location).where(Location.code == "ELD"))
        record = InventoryRecord(
            location_id=location.id,
            record_date=date.today(),
            specification_id=specification.id,
            qty_in=8300,
            qty_in_normalized=8300,
            entered_unit=EnteredUnit.PCS,
            handled_by="Test handler",
            created_by=admin.id,
        )
        db.session.add(record)
        db.session.commit()
        record_count = db.session.scalar(
            select(func.count(InventoryRecord.id))
        )

    runner = app.test_cli_runner()
    table_result = runner.invoke(args=["stock-report"])
    assert table_result.exit_code == 0, table_result.output
    assert "415 bales (8,300 pcs)" in table_result.output
    assert "Goldstar Blanket (BF)" in table_result.output

    csv_result = runner.invoke(args=["stock-report", "--csv"])
    assert csv_result.exit_code == 0, csv_result.output
    parsed = list(csv.reader(StringIO(csv_result.output)))
    assert parsed[0] == [
        "category",
        "item",
        "size",
        "pack_size",
        "stock_base_units",
        "display",
    ]
    assert [
        "Blankets",
        "Goldstar Blanket (BF)",
        "54x80 2ST",
        "20",
        "8300",
        "415 bales (8,300 pcs)",
    ] in parsed[1:]
    with app.app_context():
        assert db.session.scalar(
            select(func.count(InventoryRecord.id))
        ) == record_count


def test_stock_report_flags_expected_specification_without_pack_size(app, monkeypatch):
    seed_catalog(app, monkeypatch)
    with app.app_context():
        category = db.session.scalar(
            select(Category).where(Category.name == "Duvets")
        )
        item = db.session.scalar(
            select(Item).where(
                Item.category_id == category.id,
                Item.name == "Duvet N",
            )
        )
        specification = db.session.scalar(
            select(Specification).where(
                Specification.item_id == item.id,
                Specification.label == "4x6",
            )
        )
        specification.pack_size = None
        db.session.commit()

    result = app.test_cli_runner().invoke(args=["stock-report"])

    assert result.exit_code == 0, result.output
    assert "Duvets / Duvet N / 4x6: expected pack size 5, found none." in result.output
