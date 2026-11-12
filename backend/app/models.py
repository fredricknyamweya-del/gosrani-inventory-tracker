"""SQLAlchemy models matching the inventory ERD."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    func,
    text,
)
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db

ID_TYPE = BigInteger().with_variant(Integer, "sqlite")
JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


class UserRole(str, Enum):
    ADMIN = "Admin"
    USER = "User"


class UserStatus(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"


class StockUnit(str, Enum):
    PCS = "PCS"
    KG = "KG"


class InventoryUnit(str, Enum):
    PCS = "PCS"
    BALE = "BALE"
    KG = "KG"


class EnteredUnit(str, Enum):
    PCS = "PCS"
    BALE = "BALE"
    KG = "KG"


class RecordStatus(str, Enum):
    SAVED = "Saved"
    LOCKED = "Locked"


class RequestStatus(str, Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    LOCK = "lock"
    DELETE = "delete"
    APPROVE = "approve"
    REJECT = "reject"


class AuditEntity(str, Enum):
    INVENTORY_RECORD = "inventory_record"
    CATEGORY = "category"
    ITEM = "item"
    SPECIFICATION = "specification"
    USER = "user"
    ITEM_REQUEST = "item_request"


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


def _enum(enum_class: type[Enum], name: str) -> SqlEnum:
    return SqlEnum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )


class Location(db.Model):
    """A physical stock location."""

    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

class User(db.Model):
    """An authenticated staff or administrator account."""

    __tablename__ = "users"
    __table_args__ = (
        Index("users_email_lower_uq", text("lower(email)"), unique=True),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        _enum(UserRole, "user_role"),
        nullable=False,
        server_default=text("'User'"),
    )
    status: Mapped[UserStatus] = mapped_column(
        _enum(UserStatus, "user_status"),
        nullable=False,
        server_default=text("'Active'"),
    )
    is_primary_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    auth_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    failed_logins: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    locations: Mapped[list[Location]] = relationship(
        secondary="user_locations",
        lazy="raise",
        viewonly=True,
    )


class Category(db.Model):
    """A top-level inventory category."""

    __tablename__ = "categories"
    __table_args__ = (
        Index("categories_name_uq", text("lower(trim(name))"), unique=True),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    items: Mapped[list["Item"]] = relationship(lazy="raise", viewonly=True)


class UserLocation(db.Model):
    """A user's permitted location."""

    __tablename__ = "user_locations"

    user_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    location_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("locations.id", ondelete="RESTRICT"), primary_key=True
    )

    user: Mapped["User"] = relationship(lazy="raise")
    location: Mapped["Location"] = relationship(lazy="raise")


class Item(db.Model):
    """A product within a category."""

    __tablename__ = "items"
    __table_args__ = (
        Index(
            "items_name_per_category_uq",
            "category_id",
            text("lower(trim(name))"),
            unique=True,
        ),
        CheckConstraint(
            "(inventory_unit = 'BALE' AND pieces_per_bale IS NOT NULL AND pieces_per_bale > 0) "
            "OR (inventory_unit != 'BALE' AND pieces_per_bale IS NULL)",
            name="item_bale_conversion_valid",
        ),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    unit: Mapped[StockUnit] = mapped_column(
        _enum(StockUnit, "stock_unit"),
        nullable=False,
        server_default=text("'PCS'"),
    )
    inventory_unit: Mapped[InventoryUnit] = mapped_column(
        _enum(InventoryUnit, "inventory_unit"),
        nullable=False,
        server_default=text("'PCS'"),
    )
    pieces_per_bale: Mapped[int | None] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    category: Mapped["Category"] = relationship(lazy="raise")
    specifications: Mapped[list["Specification"]] = relationship(
        lazy="raise",
        viewonly=True,
    )


class ImportBatch(db.Model):
    """Metadata for a spreadsheet import."""

    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    source_file: Mapped[str] = mapped_column(String(255), nullable=False)
    imported_by: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    importer: Mapped["User"] = relationship(lazy="raise")


class ItemRequest(db.Model):
    """A staff request for a missing catalog entry."""

    __tablename__ = "item_requests"
    __table_args__ = (
        CheckConstraint(
            "(category_id IS NOT NULL) <> (new_category_name IS NOT NULL)",
            name="request_has_one_category",
        ),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    requested_by: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    category_id: Mapped[int | None] = mapped_column(
        ID_TYPE, ForeignKey("categories.id", ondelete="RESTRICT")
    )
    item_id: Mapped[int | None] = mapped_column(
        ID_TYPE, ForeignKey("items.id", ondelete="RESTRICT")
    )
    new_category_name: Mapped[str | None] = mapped_column(String(100))
    item_name: Mapped[str] = mapped_column(String(120), nullable=False)
    specification: Mapped[str | None] = mapped_column(String(120))
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RequestStatus] = mapped_column(
        _enum(RequestStatus, "request_status"),
        nullable=False,
        server_default=text("'Pending'"),
    )
    reviewed_by: Mapped[int | None] = mapped_column(
        ID_TYPE, ForeignKey("users.id", ondelete="RESTRICT")
    )
    reject_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    requester: Mapped["User"] = relationship(
        lazy="raise",
        foreign_keys=[requested_by],
    )
    reviewer: Mapped["User | None"] = relationship(
        lazy="raise",
        foreign_keys=[reviewed_by],
    )
    category: Mapped["Category | None"] = relationship(lazy="raise")
    item: Mapped["Item | None"] = relationship(lazy="raise")


class AuditLog(db.Model):
    """An append-only audit entry for a changed entity."""

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_entity_at", "entity_type", "entity_id", "at"),
        Index("ix_audit_log_actor_at", "actor_id", "at"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    entity_type: Mapped[AuditEntity] = mapped_column(
        _enum(AuditEntity, "audit_entity"), nullable=False
    )
    entity_id: Mapped[int] = mapped_column(ID_TYPE, nullable=False)
    action: Mapped[AuditAction] = mapped_column(
        _enum(AuditAction, "audit_action"), nullable=False
    )
    actor_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    before: Mapped[dict[str, object] | list[object] | None] = mapped_column(JSON_TYPE)
    after: Mapped[dict[str, object] | list[object] | None] = mapped_column(JSON_TYPE)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    actor: Mapped["User"] = relationship(lazy="raise")


class AssistantQuery(db.Model):
    """An audit record of a read-only assistant request."""

    __tablename__ = "assistant_queries"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    tools_called: Mapped[dict[str, object] | list[object] | None] = mapped_column(
        JSON_TYPE
    )
    result_count: Mapped[int | None] = mapped_column(Integer)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(lazy="raise")


class Specification(db.Model):
    """A size, colour, or other variant of an item."""

    __tablename__ = "specifications"
    __table_args__ = (
        Index(
            "specifications_label_per_item_uq",
            "item_id",
            text("lower(trim(label))"),
            unique=True,
        ),
        Index(
            "specifications_one_default_per_item_uq",
            "item_id",
            unique=True,
            postgresql_where=text("is_default"),
            sqlite_where=text("is_default = 1"),
        ),
        CheckConstraint("pack_size IS NULL OR pack_size > 0", name="pack_size_positive"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("items.id", ondelete="RESTRICT"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    pack_size: Mapped[int | None] = mapped_column(Integer)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    item: Mapped["Item"] = relationship(lazy="raise")


class InventoryRecord(db.Model):
    """A stock movement recorded against one specification and location."""

    __tablename__ = "inventory_records"
    __table_args__ = (
        Index(
            "ix_inventory_records_location_record_date",
            "location_id",
            "record_date",
        ),
        Index(
            "ix_inventory_records_location_spec_date",
            "location_id",
            "specification_id",
            "record_date",
        ),
        Index(
            "ix_inventory_records_location_record_date_live",
            "location_id",
            "record_date",
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "qty_in IS NOT NULL OR qty_out IS NOT NULL",
            name="has_a_quantity",
        ),
        CheckConstraint(
            "qty_in >= 0 AND qty_out >= 0",
            name="quantities_non_negative",
        ),
        CheckConstraint(
            "pieces_per_unit > 0",
            name="pieces_per_unit_positive",
        ),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False
    )
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    specification_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("specifications.id", ondelete="RESTRICT"), nullable=False
    )
    qty_in: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    qty_out: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    pieces_per_unit: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    qty_in_normalized: Mapped[Decimal | None] = mapped_column(Numeric(15, 3))
    qty_out_normalized: Mapped[Decimal | None] = mapped_column(Numeric(15, 3))
    entered_unit: Mapped[EnteredUnit] = mapped_column(
        _enum(EnteredUnit, "entered_unit"),
        nullable=False,
        server_default=text("'PCS'"),
    )
    handled_by: Mapped[str | None] = mapped_column(String(160))
    details: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RecordStatus] = mapped_column(
        _enum(RecordStatus, "record_status"),
        nullable=False,
        server_default=text("'Locked'"),
    )
    created_by: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(
        ID_TYPE, ForeignKey("users.id", ondelete="RESTRICT")
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    import_batch_id: Mapped[int | None] = mapped_column(
        ID_TYPE, ForeignKey("import_batches.id", ondelete="RESTRICT")
    )

    location: Mapped["Location"] = relationship(lazy="raise")
    specification: Mapped["Specification"] = relationship(lazy="raise")
    creator: Mapped["User"] = relationship(
        lazy="raise",
        foreign_keys=[created_by],
    )
    updater: Mapped["User | None"] = relationship(
        lazy="raise",
        foreign_keys=[updated_by],
    )
    import_batch: Mapped["ImportBatch | None"] = relationship(lazy="raise")


class RevokedToken(db.Model):
    """A JWT token revocation record for logout and refresh rotation."""

    __tablename__ = "revoked_tokens"
    __table_args__ = (Index("ix_revoked_tokens_expires_at", "expires_at"),)

    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    token_type: Mapped[TokenType] = mapped_column(
        _enum(TokenType, "token_type"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(lazy="raise")


v_stock = Table(
    "v_stock",
    MetaData(),
    Column("location_id", ID_TYPE, nullable=False),
    Column("specification_id", ID_TYPE, nullable=False),
    Column("stock", Numeric(15, 3), nullable=True),
)