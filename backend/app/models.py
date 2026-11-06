"""SQLAlchemy models matching the inventory ERD."""

from enum import Enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    func,
    text,
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

    user_links: Mapped[list["UserLocation"]] = relationship(
        back_populates="location"
    )
    inventory_records: Mapped[list["InventoryRecord"]] = relationship(
        back_populates="location"
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
    failed_logins: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    locked_until: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    location_links: Mapped[list["UserLocation"]] = relationship(back_populates="user")
    records_created: Mapped[list["InventoryRecord"]] = relationship(
        back_populates="creator",
        foreign_keys="InventoryRecord.created_by",
    )
    records_updated: Mapped[list["InventoryRecord"]] = relationship(
        back_populates="updater",
        foreign_keys="InventoryRecord.updated_by",
    )
    imported_batches: Mapped[list["ImportBatch"]] = relationship(
        back_populates="importer"
    )
    requests_created: Mapped[list["ItemRequest"]] = relationship(
        back_populates="requester",
        foreign_keys="ItemRequest.requested_by",
    )
    requests_reviewed: Mapped[list["ItemRequest"]] = relationship(
        back_populates="reviewer",
        foreign_keys="ItemRequest.reviewed_by",
    )
    audit_entries: Mapped[list["AuditLog"]] = relationship(back_populates="actor")
    assistant_queries: Mapped[list["AssistantQuery"]] = relationship(
        back_populates="user"
    )
    revoked_tokens: Mapped[list["RevokedToken"]] = relationship(back_populates="user")


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

    items: Mapped[list["Item"]] = relationship(back_populates="category")


class UserLocation(db.Model):
    """A user's permitted location."""

    __tablename__ = "user_locations"

    user_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("users.id"), primary_key=True
    )
    location_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("locations.id"), primary_key=True
    )

    user: Mapped["User"] = relationship(back_populates="location_links")
    location: Mapped["Location"] = relationship(back_populates="user_links")


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
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("categories.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    unit: Mapped[StockUnit] = mapped_column(
        _enum(StockUnit, "stock_unit"),
        nullable=False,
        server_default=text("'PCS'"),
    )
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    category: Mapped["Category"] = relationship(back_populates="items")
    specifications: Mapped[list["Specification"]] = relationship(
        back_populates="item"
    )


class ImportBatch(db.Model):
    """Metadata for a spreadsheet import."""

    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    source_file: Mapped[str] = mapped_column(String(255), nullable=False)
    imported_by: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("users.id"), nullable=False
    )
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    imported_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    importer: Mapped["User"] = relationship(back_populates="imported_batches")
    inventory_records: Mapped[list["InventoryRecord"]] = relationship(
        back_populates="import_batch"
    )


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
        ID_TYPE, ForeignKey("users.id"), nullable=False
    )
    category_id: Mapped[int | None] = mapped_column(
        ID_TYPE, ForeignKey("categories.id")
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
        ID_TYPE, ForeignKey("users.id")
    )
    reject_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    reviewed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))

    requester: Mapped["User"] = relationship(
        back_populates="requests_created",
        foreign_keys=[requested_by],
    )
    reviewer: Mapped["User | None"] = relationship(
        back_populates="requests_reviewed",
        foreign_keys=[reviewed_by],
    )
    category: Mapped["Category | None"] = relationship()


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
        ID_TYPE, ForeignKey("users.id"), nullable=False
    )
    before: Mapped[dict | list | None] = mapped_column(JSON_TYPE)
    after: Mapped[dict | list | None] = mapped_column(JSON_TYPE)
    at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    actor: Mapped["User"] = relationship(back_populates="audit_entries")


class AssistantQuery(db.Model):
    """An audit record of a read-only assistant request."""

    __tablename__ = "assistant_queries"

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("users.id"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    tools_called: Mapped[dict | list | None] = mapped_column(JSON_TYPE)
    result_count: Mapped[int | None] = mapped_column(Integer)
    at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="assistant_queries")


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
        ID_TYPE, ForeignKey("items.id"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    pack_size: Mapped[int | None] = mapped_column(Integer)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    item: Mapped["Item"] = relationship(back_populates="specifications")
    inventory_records: Mapped[list["InventoryRecord"]] = relationship(
        back_populates="specification"
    )


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
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("locations.id"), nullable=False
    )
    record_date: Mapped[Date] = mapped_column(Date, nullable=False)
    specification_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("specifications.id"), nullable=False
    )
    qty_in: Mapped[float | None] = mapped_column(Numeric(12, 3))
    qty_out: Mapped[float | None] = mapped_column(Numeric(12, 3))
    entered_unit: Mapped[EnteredUnit] = mapped_column(
        _enum(EnteredUnit, "entered_unit"),
        nullable=False,
        server_default=text("'PCS'"),
    )
    details: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RecordStatus] = mapped_column(
        _enum(RecordStatus, "record_status"),
        nullable=False,
        server_default=text("'Locked'"),
    )
    created_by: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_by: Mapped[int | None] = mapped_column(ID_TYPE, ForeignKey("users.id"))
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    import_batch_id: Mapped[int | None] = mapped_column(
        ID_TYPE, ForeignKey("import_batches.id")
    )

    location: Mapped["Location"] = relationship(back_populates="inventory_records")
    specification: Mapped["Specification"] = relationship(
        back_populates="inventory_records"
    )
    creator: Mapped["User"] = relationship(
        back_populates="records_created",
        foreign_keys=[created_by],
    )
    updater: Mapped["User | None"] = relationship(
        back_populates="records_updated",
        foreign_keys=[updated_by],
    )
    import_batch: Mapped["ImportBatch | None"] = relationship(
        back_populates="inventory_records"
    )


class RevokedToken(db.Model):
    """A JWT token revocation record for logout and refresh rotation."""

    __tablename__ = "revoked_tokens"
    __table_args__ = (Index("ix_revoked_tokens_expires_at", "expires_at"),)

    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    token_type: Mapped[str] = mapped_column(String(10), nullable=False)
    user_id: Mapped[int] = mapped_column(
        ID_TYPE, ForeignKey("users.id"), nullable=False
    )
    expires_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="revoked_tokens")