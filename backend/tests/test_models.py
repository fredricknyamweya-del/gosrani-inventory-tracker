"""Tests for the ERD-backed SQLAlchemy schema."""

from sqlalchemy import inspect

from app.extensions import db
from app.models import InventoryRecord, Specification

EXPECTED_TABLES = {
    "locations",
    "users",
    "categories",
    "user_locations",
    "items",
    "import_batches",
    "item_requests",
    "audit_log",
    "assistant_queries",
    "specifications",
    "inventory_records",
    "revoked_tokens",
}


def test_erd_tables_are_registered_and_created(app):
    assert set(db.metadata.tables) == EXPECTED_TABLES
    inspector = inspect(db.engine)
    assert EXPECTED_TABLES <= set(inspector.get_table_names())


def test_sqlite_primary_keys_use_integer_storage(app):
    columns = inspect(db.engine).get_columns("inventory_records")
    id_column = next(column for column in columns if column["name"] == "id")

    assert id_column["type"].__class__.__name__ == "INTEGER"


def test_schema_constraints_and_partial_indexes_are_named():
    record_constraints = {
        constraint.name for constraint in InventoryRecord.__table__.constraints
    }
    spec_indexes = {index.name: index for index in Specification.__table__.indexes}

    assert {"has_a_quantity", "quantities_non_negative"} <= record_constraints
    assert "specifications_one_default_per_item_uq" in spec_indexes
    assert spec_indexes["specifications_one_default_per_item_uq"].dialect_options[
        "postgresql"
    ]["where"] is not None
    assert spec_indexes["specifications_one_default_per_item_uq"].dialect_options[
        "sqlite"
    ]["where"] is not None
