"""Tests for the ERD-backed SQLAlchemy schema."""

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    Category,
    InventoryRecord,
    Item,
    Location,
    Specification,
    User,
    UserLocation,
    UserRole,
    UserStatus,
)

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


def _create_catalog():
    location = Location(code="ELD", name="Eldoret Godown")
    user = User(name="Staff", email="staff@example.com", password_hash="hash")
    category = Category(name="Bedding")
    db.session.add_all([location, user, category])
    db.session.flush()
    item = Item(category_id=category.id, name="Duvet")
    db.session.add(item)
    db.session.flush()
    specification = Specification(item_id=item.id, label="4x6")
    db.session.add(specification)
    db.session.commit()
    return location, user, category, item, specification


def test_identity_and_catalog_models_insert_with_server_defaults(app):
    location, user, category, item, specification = _create_catalog()

    assert location.active is True
    assert user.role is UserRole.USER
    assert user.status is UserStatus.ACTIVE
    assert user.failed_logins == 0
    assert category.sort_order == 0
    assert category.active is True
    assert item.unit.value == "PCS"
    assert item.active is True
    assert specification.is_default is False
    assert specification.active is True


def test_user_location_association_inserts_and_restricts_parent_deletes(app):
    location, user, category, _item, _specification = _create_catalog()
    association = UserLocation(user_id=user.id, location_id=location.id)
    db.session.add(association)
    db.session.commit()

    with pytest.raises(IntegrityError):
        db.session.delete(location)
        db.session.commit()
    db.session.rollback()

    with pytest.raises(IntegrityError):
        db.session.delete(category)
        db.session.commit()
    db.session.rollback()


def test_user_location_rejects_missing_foreign_keys(app):
    db.session.add(UserLocation(user_id=999, location_id=999))

    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


@pytest.mark.parametrize(
    ("model", "first", "duplicate"),
    [
        (
            User,
            {"name": "First", "email": "staff@example.com", "password_hash": "hash"},
            {"name": "Second", "email": "STAFF@example.com", "password_hash": "hash"},
        ),
        (Category, {"name": " Bedding "}, {"name": "bedding"}),
    ],
)
def test_case_and_whitespace_insensitive_identity_indexes(app, model, first, duplicate):
    db.session.add(model(**first))
    db.session.commit()
    db.session.add(model(**duplicate))

    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_item_and_specification_names_are_unique_after_normalization(app):
    _location, _user, category, item, specification = _create_catalog()
    db.session.add(Item(category_id=category.id, name="  duvet "))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()

    db.session.add(Specification(item_id=item.id, label=" 4X6 "))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    assert db.session.get(Specification, specification.id) is not None


def test_specifications_enforce_one_default_and_positive_pack_size(app):
    _location, _user, _category, item, _specification = _create_catalog()
    db.session.add_all(
        [
            Specification(
                item_id=item.id,
                label="Standard",
                is_default=True,
                pack_size=1,
            ),
            Specification(
                item_id=item.id,
                label="Default 2",
                is_default=True,
            ),
        ]
    )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()

    db.session.add(Specification(item_id=item.id, label="Invalid", pack_size=0))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


@pytest.mark.parametrize(
    ("column", "value"),
    [("role", "Owner"), ("status", "Archived")],
)
def test_user_enum_checks_reject_values_outside_the_dbml(app, column, value):
    statement = text(
        f"INSERT INTO users (name, email, password_hash, {column}) "
        "VALUES ('Staff', 'staff@example.com', 'hash', :value)"
    )
    with pytest.raises(IntegrityError):
        db.session.execute(statement, {"value": value})
        db.session.commit()
    db.session.rollback()


def test_catalog_relationships_prevent_implicit_lazy_queries():
    assert inspect(User).relationships.locations.lazy == "raise"
    assert inspect(Category).relationships.items.lazy == "raise"
    assert inspect(Item).relationships.category.lazy == "raise"
    assert inspect(Item).relationships.specifications.lazy == "raise"
    assert inspect(UserLocation).relationships.user.lazy == "raise"
    assert inspect(UserLocation).relationships.location.lazy == "raise"
    assert inspect(Specification).relationships.item.lazy == "raise"


def test_catalog_foreign_keys_are_restrict():
    foreign_keys = {
        (foreign_key.parent.name, foreign_key.ondelete)
        for table_name in ("user_locations", "items", "specifications")
        for foreign_key in db.metadata.tables[table_name].foreign_keys
    }

    assert foreign_keys == {
        ("user_id", "RESTRICT"),
        ("location_id", "RESTRICT"),
        ("category_id", "RESTRICT"),
        ("item_id", "RESTRICT"),
    }
