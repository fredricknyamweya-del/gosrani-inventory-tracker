"""Tests for the ERD-backed SQLAlchemy schema."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    AssistantQuery,
    AuditAction,
    AuditEntity,
    AuditLog,
    Category,
    EnteredUnit,
    ImportBatch,
    InventoryRecord,
    Item,
    ItemRequest,
    Location,
    RecordStatus,
    RequestStatus,
    RevokedToken,
    Specification,
    StockUnit,
    TokenType,
    User,
    UserLocation,
    UserRole,
    UserStatus,
    v_stock,
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
    assert inspect(Category).relationships["items"].lazy == "raise"
    assert inspect(Item).relationships["category"].lazy == "raise"
    assert inspect(Item).relationships["specifications"].lazy == "raise"
    assert inspect(UserLocation).relationships["user"].lazy == "raise"
    assert inspect(UserLocation).relationships["location"].lazy == "raise"
    assert inspect(Specification).relationships["item"].lazy == "raise"


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


def test_remaining_models_accept_valid_rows_and_stock_view_excludes_deleted(app):
    location, user, category, item, specification = _create_catalog()
    batch = ImportBatch(
        source_file="opening.xlsx",
        imported_by=user.id,
        row_count=2,
    )
    db.session.add(batch)
    db.session.flush()
    live_record = InventoryRecord(
        location_id=location.id,
        record_date=date(2026, 1, 2),
        specification_id=specification.id,
        qty_in=10,
        qty_out=2,
        entered_unit=EnteredUnit.PCS,
        status=RecordStatus.SAVED,
        created_by=user.id,
        import_batch_id=batch.id,
    )
    deleted_record = InventoryRecord(
        location_id=location.id,
        record_date=date(2026, 1, 3),
        specification_id=specification.id,
        qty_in=100,
        qty_out=0,
        created_by=user.id,
        deleted_at=datetime(2026, 1, 4, tzinfo=UTC),
    )
    request = ItemRequest(
        requested_by=user.id,
        category_id=category.id,
        item_name="Mattress",
        status=RequestStatus.PENDING,
    )
    audit = AuditLog(
        entity_type=AuditEntity.ITEM,
        entity_id=item.id,
        action=AuditAction.CREATE,
        actor_id=user.id,
        before=None,
        after={"name": item.name},
    )
    assistant_query = AssistantQuery(
        user_id=user.id,
        question="What is the stock?",
        tools_called=["stock_by_item"],
        result_count=1,
    )
    revoked_token = RevokedToken(
        jti="test-token-id",
        token_type=TokenType.ACCESS,
        user_id=user.id,
        expires_at=datetime(2030, 1, 1, tzinfo=UTC),
    )
    db.session.add_all(
        [
            live_record,
            deleted_record,
            request,
            audit,
            assistant_query,
            revoked_token,
        ]
    )
    db.session.commit()

    stock_row = db.session.execute(
        select(v_stock).where(
            v_stock.c.location_id == location.id,
            v_stock.c.specification_id == specification.id,
        )
    ).one()
    assert stock_row.stock == 8
    assert request.id is not None
    assert audit.id is not None
    assert assistant_query.id is not None
    assert revoked_token.jti == "test-token-id"
    assert item.unit is StockUnit.PCS


@pytest.mark.parametrize(
    ("model", "values"),
    [
        (ImportBatch, {"source_file": "file.xlsx", "imported_by": 999, "row_count": 0}),
        (ItemRequest, {"requested_by": 999, "new_category_name": "New", "item_name": "X"}),
        (AuditLog, {"entity_type": AuditEntity.ITEM, "entity_id": 1, "action": AuditAction.CREATE, "actor_id": 999}),
        (AssistantQuery, {"user_id": 999, "question": "Q"}),
        (Specification, {"item_id": 999, "label": "X"}),
        (RevokedToken, {"jti": "missing-user", "token_type": TokenType.ACCESS, "user_id": 999, "expires_at": "2030-01-01 00:00:00"}),
    ],
)
def test_model_foreign_keys_reject_missing_parents(app, model, values):
    db.session.add(model(**values))

    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_inventory_checks_reject_missing_and_negative_quantities(app):
    location, user, _category, _item, specification = _create_catalog()
    common = {
        "location_id": location.id,
        "record_date": date(2026, 1, 2),
        "specification_id": specification.id,
        "created_by": user.id,
    }

    db.session.add(InventoryRecord(**common))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()

    db.session.add(InventoryRecord(**common, qty_in=-1, qty_out=0))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_inventory_record_identifiers_are_not_reused_after_delete(app):
    location, user, _category, _item, specification = _create_catalog()
    record = InventoryRecord(
        location_id=location.id,
        record_date=date(2026, 1, 2),
        specification_id=specification.id,
        qty_in=1,
        created_by=user.id,
    )
    db.session.add(record)
    db.session.commit()
    deleted_id = record.id
    db.session.delete(record)
    db.session.commit()

    next_record = InventoryRecord(
        location_id=location.id,
        record_date=date(2026, 1, 3),
        specification_id=specification.id,
        qty_in=1,
        created_by=user.id,
    )
    db.session.add(next_record)
    db.session.commit()

    assert next_record.id > deleted_id
