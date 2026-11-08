"""Tests for inventory record validation."""

from datetime import date

from app.extensions import db
from app.inventory import _resolve_record
from app.models import Category, Item, Specification


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
