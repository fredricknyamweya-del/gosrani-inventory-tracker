"""Database-backed inventory endpoints."""

from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.api_utils import (
    ApiValidationError,
    audit,
    current_user,
    iso_datetime,
    json_number,
    user_location_ids,
)
from app.errors import error_response, validation_error
from app.extensions import db
from app.models import (
    AuditAction,
    AuditEntity,
    Category,
    EnteredUnit,
    InventoryRecord,
    InventoryUnit,
    Item,
    Location,
    RecordStatus,
    Specification,
    StockUnit,
    User,
    UserRole,
    v_stock,
)
from app.units import effective_pieces_per_bale, format_quantity_display

inventory_bp = Blueprint("inventory", __name__, url_prefix="/api/inventory")


@inventory_bp.after_request
def _disable_stock_response_caching(response):
    if request.endpoint == "inventory.get_inventory_stock":
        response.headers["Cache-Control"] = "no-store"
    return response


def _parse_record_identifier(identifier: str) -> int | None:
    digits = identifier[4:] if identifier[:4].casefold() == "inv-" else identifier
    if not digits or any(character not in "0123456789" for character in digits):
        return None
    return int(digits)


def _resolve_record(
    payload: object,
    *,
    existing_record: InventoryRecord | None = None,
) -> tuple[dict[str, object] | None, list[dict[str, str]]]:
    if not isinstance(payload, dict):
        return None, [{"field": "body", "message": "A JSON object is required."}]

    errors: list[dict[str, str]] = []
    date_value = payload.get("date")
    try:
        record_date = date.fromisoformat(str(date_value))
        if record_date.isoformat() != date_value:
            raise ValueError
    except (TypeError, ValueError):
        errors.append({"field": "date", "message": "Enter a valid date in YYYY-MM-DD format."})
        record_date = None

    def find_name(model, value: object, field: str, parent_field: str | None = None, parent_id: int | None = None):
        if not isinstance(value, (str, int)) or not str(value).strip():
            errors.append({"field": field, "message": f"{field.title()} is required."})
            return None
        statement = select(model)
        if str(value).isdigit():
            statement = statement.where(model.id == int(value))
        else:
            statement = statement.where(func.lower(model.name if model is not Specification else model.label) == str(value).strip().lower())
        if parent_field and parent_id is not None:
            statement = statement.where(getattr(model, parent_field) == parent_id)
        result = db.session.scalar(statement)
        if result is None:
            errors.append({"field": field, "message": f"Choose a valid {field} from the catalog."})
        return result

    category = find_name(Category, payload.get("category"), "category")
    item = None
    specification = None
    if category is not None:
        item = find_name(Item, payload.get("item"), "item", "category_id", category.id)
    if item is not None:
        specification = find_name(
            Specification,
            payload.get("size", payload.get("specification")),
            "size",
            "item_id",
            item.id,
        )

    stock_unit = item.unit if item is not None else StockUnit.PCS
    pack_size = specification.pack_size if specification is not None else None
    same_specification = (
        existing_record is not None
        and specification is not None
        and specification.id == existing_record.specification_id
    )
    default_unit = (
        item.entry_unit if item is not None else EnteredUnit.PCS
    )
    entered_unit_value = payload.get("enteredUnit", default_unit.value)
    try:
        entered_unit = EnteredUnit(entered_unit_value)
    except (TypeError, ValueError):
        errors.append(
            {"field": "enteredUnit", "message": "Choose PCS, BALE, or KG."}
        )
        entered_unit = default_unit
    if item is not None and entered_unit != item.entry_unit:
        unit_name = {
            EnteredUnit.BALE: "bales",
            EnteredUnit.PCS: "pieces",
            EnteredUnit.KG: "kg",
        }[item.entry_unit]
        errors.append(
            {
                "field": "enteredUnit",
                "message": f"{item.name} is entered in {unit_name}.",
            }
        )

    pieces_per_bale = None
    if entered_unit == EnteredUnit.BALE:
        raw_pieces_per_bale = payload.get(
            "piecesPerBale",
            existing_record.pieces_per_bale
            if same_specification and existing_record is not None
            else pack_size,
        )
        try:
            parsed_pieces_per_bale = Decimal(str(raw_pieces_per_bale))
            if (
                not parsed_pieces_per_bale.is_finite()
                or parsed_pieces_per_bale != parsed_pieces_per_bale.to_integral_value()
                or not 1 <= parsed_pieces_per_bale <= 10_000
            ):
                raise InvalidOperation
            pieces_per_bale = int(parsed_pieces_per_bale)
        except (InvalidOperation, ValueError):
            errors.append(
                {
                    "field": "piecesPerBale",
                    "message": (
                        "Enter how many pieces are in each bale."
                        if raw_pieces_per_bale in (None, "")
                        else "Pieces per bale must be a whole number from 1 to 10000."
                    ),
                }
            )
    pieces_per_unit = pieces_per_bale or 1

    quantities: dict[str, Decimal | None] = {}
    for key in ("quantityIn", "quantityOut"):
        value = payload.get(key)
        if value in (None, ""):
            quantities[key] = None
            continue
        try:
            quantity = Decimal(str(value))
            if (
                not quantity.is_finite()
                or quantity < 0
                or quantity != quantity.quantize(Decimal("0.001"))
            ):
                raise InvalidOperation
            if (
                entered_unit == EnteredUnit.BALE
                or entered_unit == EnteredUnit.PCS
            ) and quantity != quantity.to_integral_value():
                raise InvalidOperation
            quantities[key] = quantity
        except (InvalidOperation, ValueError):
            errors.append({
                "field": key,
                "message": (
                    "Enter a non-negative whole number of bales or pieces."
                    if entered_unit in {EnteredUnit.BALE, EnteredUnit.PCS}
                    else "Enter a non-negative quantity with no more than three decimal places."
                ),
            })
            quantities[key] = None
    if quantities["quantityIn"] is None and quantities["quantityOut"] is None:
        errors.append({"field": "quantity", "message": "Enter a value for Quantity In or Quantity Out."})

    handled_by = payload.get("handledBy")
    if not isinstance(handled_by, str) or not handled_by.strip():
        errors.append({"field": "handledBy", "message": "The name of the person who handled the stock is required."})
    elif len(handled_by.strip()) > 160:
        errors.append({"field": "handledBy", "message": "The name must be 160 characters or fewer."})

    details = payload.get("details", "")
    if details is not None and not isinstance(details, str):
        errors.append({"field": "details", "message": "Details must be text."})
    elif details and len(details) > 10_000:
        errors.append({"field": "details", "message": "Details must be 10,000 characters or fewer."})

    if errors:
        return None, errors
    return {
        "date": record_date,
        "category": category,
        "item": item,
        "specification": specification,
        "quantityIn": quantities["quantityIn"],
        "quantityOut": quantities["quantityOut"],
        "enteredUnit": entered_unit,
        "piecesPerBale": pieces_per_bale,
        "piecesPerUnit": pieces_per_unit or 1,
        "normalizedQuantityIn": (
            quantities["quantityIn"] * (pieces_per_unit or 1)
            if quantities["quantityIn"] is not None
            else None
        ),
        "normalizedQuantityOut": (
            quantities["quantityOut"] * (pieces_per_unit or 1)
            if quantities["quantityOut"] is not None
            else None
        ),
        "handledBy": handled_by.strip(),
        "details": (details or "").strip(),
    }, []


def _serialize(record: InventoryRecord) -> dict[str, object]:
    specification = db.session.get(Specification, record.specification_id)
    item = db.session.get(Item, specification.item_id) if specification else None
    category = db.session.get(Category, item.category_id) if item else None
    creator = db.session.get(User, record.created_by)
    updater = (
        db.session.get(User, record.updated_by)
        if record.updated_by
        else None
    )
    stock_unit = item.unit if item else StockUnit.PCS
    pack_size = specification.pack_size if specification else None
    base_quantity_in = record.qty_in_normalized
    if base_quantity_in is None:
        base_quantity_in = record.qty_in
    base_quantity_out = record.qty_out_normalized
    if base_quantity_out is None:
        base_quantity_out = record.qty_out
    conversion = (
        Decimal(record.pieces_per_unit)
        if record.entered_unit == EnteredUnit.BALE
        else Decimal(1)
    )
    quantity_in = (
        base_quantity_in / conversion if base_quantity_in is not None else None
    )
    quantity_out = (
        base_quantity_out / conversion if base_quantity_out is not None else None
    )
    quantity_in_display = (
        format_quantity_display(base_quantity_in, stock_unit, pack_size)
        if base_quantity_in is not None
        else (None, None)
    )
    quantity_out_display = (
        format_quantity_display(base_quantity_out, stock_unit, pack_size)
        if base_quantity_out is not None
        else (None, None)
    )
    return {
        "id": record.id,
        "locationId": str(record.location_id),
        "date": record.record_date.isoformat(),
        "category": category.name if category else "",
        "item": item.name if item else "",
        "size": specification.label if specification else "",
        "quantityIn": json_number(quantity_in),
        "quantityOut": json_number(quantity_out),
        "normalizedQuantityIn": json_number(base_quantity_in),
        "normalizedQuantityOut": json_number(base_quantity_out),
        "quantityInDisplay": quantity_in_display[0],
        "quantityInSecondaryDisplay": quantity_in_display[1],
        "quantityOutDisplay": quantity_out_display[0],
        "quantityOutSecondaryDisplay": quantity_out_display[1],
        "piecesPerUnit": record.pieces_per_unit,
        "handledBy": record.handled_by or "",
        "enteredUnit": record.entered_unit.value,
        "unit": stock_unit.value,
        "packSize": pack_size,
        "details": record.details or "",
        "addedBy": creator.name if creator else "",
        "modifiedBy": updater.name if updater else (creator.name if creator else ""),
        "createdAt": iso_datetime(record.created_at),
        "status": record.status.value,
    }


def _record_snapshot(record: InventoryRecord) -> dict[str, object]:
    return {
        "recordDate": record.record_date.isoformat(),
        "specificationId": record.specification_id,
        "quantityIn": json_number(record.qty_in),
        "quantityOut": json_number(record.qty_out),
        "normalizedQuantityIn": json_number(record.qty_in_normalized),
        "normalizedQuantityOut": json_number(record.qty_out_normalized),
        "piecesPerUnit": record.pieces_per_unit,
        "enteredUnit": record.entered_unit.value,
        "handledBy": record.handled_by,
        "details": record.details,
        "status": record.status.value,
    }


def _accessible_location_ids() -> list[int]:
    user = current_user()
    return user_location_ids(user.id)


def _warning_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    warnings = []
    today = date.today()
    location_ids = _accessible_location_ids()
    for index, row in enumerate(rows):
        flags: list[dict[str, str]] = []
        qty_in = row["quantityIn"]
        qty_out = row["quantityOut"]
        if (qty_in is not None and qty_in >= 500) or (qty_out is not None and qty_out >= 500):
            flags.append({
                "field": "quantity",
                "message": "Unusually large quantity. Check that the units are correct.",
            })
        if qty_in is not None and qty_out is not None:
            flags.append({"field": "quantity", "message": "Both Quantity In and Quantity Out have values."})

        location_id = row.get("locationId")
        if location_ids and location_id is not None and qty_out is not None:
            stock = db.session.scalar(
                select(v_stock.c.stock)
                .where(
                    v_stock.c.location_id == location_id,
                    v_stock.c.specification_id == row["specification"].id,
                )
            ) or 0
            if row["normalizedQuantityOut"] > stock:
                flags.append({
                    "field": "quantityOut",
                    "message": "Quantity Out is greater than the recorded available stock.",
                })
        record_date = row["date"]
        if record_date > today:
            flags.append({"field": "date", "message": "This date is in the future."})
        if (today - record_date).days > 180:
            flags.append({"field": "date", "message": "This date is more than six months in the past."})
        warnings.append({"index": index, "flags": flags})
    return warnings


def _location_for_create(payload: dict[str, object], user_id: int) -> int | None:
    allowed = user_location_ids(user_id)
    requested = payload.get("locationId")
    if requested is not None:
        try:
            location_id = int(requested)
        except (TypeError, ValueError):
            return None
        return location_id if location_id in allowed else None
    return allowed[0] if allowed else None


def _create_one(payload: dict[str, object], user, location_id: int) -> InventoryRecord:
    values, errors = _resolve_record(payload)
    if errors:
        raise ApiValidationError(errors[0]["field"], errors[0]["message"])
    normalized_out = values["normalizedQuantityOut"]
    if normalized_out is not None:
        available = db.session.scalar(
            select(v_stock.c.stock).where(
                v_stock.c.location_id == location_id,
                v_stock.c.specification_id == values["specification"].id,
            )
        ) or 0
        if normalized_out > available:
            raise ApiValidationError(
                "quantityOut",
                "Quantity Out cannot exceed the available stock for this product and location.",
            )
    record = InventoryRecord(
        location_id=location_id,
        record_date=values["date"],
        specification_id=values["specification"].id,
        qty_in=values["normalizedQuantityIn"],
        qty_out=values["normalizedQuantityOut"],
        handled_by=values["handledBy"],
        entered_unit=values["enteredUnit"],
        pieces_per_unit=values["piecesPerUnit"],
        qty_in_normalized=values["normalizedQuantityIn"],
        qty_out_normalized=values["normalizedQuantityOut"],
        details=values["details"],
        status=RecordStatus.SAVED if user.role == UserRole.ADMIN else RecordStatus.LOCKED,
        created_by=user.id,
    )
    db.session.add(record)
    db.session.flush()
    audit(
        AuditEntity.INVENTORY_RECORD,
        record.id,
        AuditAction.CREATE,
        user.id,
        after=_record_snapshot(record),
    )
    return record


@inventory_bp.get("")
@jwt_required()
def list_inventory():
    current_user()
    location_ids = _accessible_location_ids()
    statement = (
        select(InventoryRecord)
        .where(
            InventoryRecord.location_id.in_(location_ids),
            InventoryRecord.deleted_at.is_(None),
        )
    )
    if not location_ids:
        statement = statement.where(False)
    category = request.args.get("category", "").strip()
    item_name = request.args.get("item", "").strip()
    size = request.args.get("size", "").strip()
    search = request.args.get("search", "").strip()
    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()
    if category:
        statement = statement.join(InventoryRecord.specification).join(Specification.item).join(Item.category)
        statement = statement.where(func.lower(Category.name) == category.lower())
    elif item_name or size or search:
        statement = statement.join(InventoryRecord.specification).join(Specification.item).join(Item.category)
    if item_name:
        statement = statement.where(func.lower(Item.name) == item_name.lower())
    if size:
        statement = statement.where(func.lower(Specification.label) == size.lower())
    if search:
        pattern = f"%{search}%"
        statement = statement.join(InventoryRecord.creator)
        statement = statement.where(
            or_(
                Category.name.ilike(pattern),
                Item.name.ilike(pattern),
                Specification.label.ilike(pattern),
                InventoryRecord.handled_by.ilike(pattern),
                InventoryRecord.details.ilike(pattern),
                User.name.ilike(pattern),
            )
        )
    for key, value in (("from", date_from), ("to", date_to)):
        if value:
            try:
                parsed = date.fromisoformat(value)
            except ValueError:
                return validation_error([{"field": key, "message": "Enter a valid date in YYYY-MM-DD format."}])
            statement = statement.where(
                InventoryRecord.record_date >= parsed if key == "from" else InventoryRecord.record_date <= parsed
            )
    sort = request.args.get("sort", "desc")
    if sort not in {"asc", "desc"}:
        return validation_error([{"field": "sort", "message": "Sort must be asc or desc."}])
    try:
        page = int(request.args.get("page", "1"))
        limit = int(request.args.get("limit", "6"))
    except ValueError:
        return validation_error([{"field": "pagination", "message": "Page and limit must be whole numbers."}])
    if page < 1:
        return validation_error([{"field": "page", "message": "Page must be a positive whole number."}])
    if not 1 <= limit <= 100:
        return validation_error([{"field": "limit", "message": "Limit must be between 1 and 100."}])

    total = db.session.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    statement = statement.order_by(
        InventoryRecord.record_date.asc() if sort == "asc" else InventoryRecord.record_date.desc(),
        InventoryRecord.id.asc() if sort == "asc" else InventoryRecord.id.desc(),
    ).offset((page - 1) * limit).limit(limit)
    records = db.session.scalars(statement).all()
    return jsonify({
        "data": [_serialize(record) for record in records],
        "meta": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit},
    })


@inventory_bp.post("/validate")
@jwt_required()
def validate_inventory():
    payload = request.get_json()
    rows = payload if isinstance(payload, list) else [payload]
    if not rows:
        return validation_error([{"field": "body", "message": "Add at least one inventory entry."}])
    normalized_rows = []
    errors = []
    for index, row in enumerate(rows):
        values, row_errors = _resolve_record(row)
        if row_errors:
            errors.extend({**error, "field": f"rows.{index}.{error['field']}"} for error in row_errors)
            continue
        normalized_rows.append({
            "date": values["date"].isoformat(),
            "category": values["category"].name,
            "item": values["item"].name,
            "size": values["specification"].label,
            "quantityIn": json_number(values["quantityIn"]),
            "quantityOut": json_number(values["quantityOut"]),
            "quantityInDisplay": (
                format_quantity_display(
                    values["normalizedQuantityIn"],
                    values["item"].unit,
                    values["specification"].pack_size,
                )[0]
                if values["normalizedQuantityIn"] is not None
                else None
            ),
            "quantityInSecondaryDisplay": (
                format_quantity_display(
                    values["normalizedQuantityIn"],
                    values["item"].unit,
                    values["specification"].pack_size,
                )[1]
                if values["normalizedQuantityIn"] is not None
                else None
            ),
            "quantityOutDisplay": (
                format_quantity_display(
                    values["normalizedQuantityOut"],
                    values["item"].unit,
                    values["specification"].pack_size,
                )[0]
                if values["normalizedQuantityOut"] is not None
                else None
            ),
            "quantityOutSecondaryDisplay": (
                format_quantity_display(
                    values["normalizedQuantityOut"],
                    values["item"].unit,
                    values["specification"].pack_size,
                )[1]
                if values["normalizedQuantityOut"] is not None
                else None
            ),
            "handledBy": values["handledBy"],
            "enteredUnit": values["enteredUnit"],
            "details": values["details"],
        })
    if errors:
        return validation_error(errors)
    # Warnings use the resolved specifications, so resolve once more after normalization.
    user = current_user()
    allowed_location_ids = user_location_ids(user.id)
    warning_inputs = []
    for index, row in enumerate(rows):
        values, _ = _resolve_record(row)
        if values is None:
            continue
        location_id = _location_for_create(
            row if isinstance(row, dict) else {},
            user.id,
        )
        if location_id is None and allowed_location_ids:
            location_id = allowed_location_ids[0]
        if row.get("locationId") is not None and location_id is None:
            return error_response(
                403,
                "You do not have access to the selected stock location.",
                "location_forbidden",
            )
        values["locationId"] = location_id
        warning_inputs.append(values)
    return jsonify({"data": {"rows": normalized_rows, "warnings": _warning_rows(warning_inputs)}})


@inventory_bp.post("")
@jwt_required()
def create_inventory():
    user = current_user()
    payload = request.get_json()
    rows = payload if isinstance(payload, list) else [payload]
    if not rows:
        return validation_error([{"field": "body", "message": "Add at least one inventory entry."}])
    allowed_ids = user_location_ids(user.id)
    location_id = _location_for_create(rows[0] if isinstance(rows[0], dict) else {}, user.id)
    if not allowed_ids:
        return error_response(403, "Your account is not assigned to a stock location.", "location_forbidden")
    if location_id is None:
        return error_response(403, "You do not have access to the selected stock location.", "location_forbidden")
    records = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            db.session.rollback()
            return validation_error([{"field": f"rows.{index}", "message": "A JSON object is required."}])
        try:
            row_location_id = _location_for_create(row, user.id)
            if row.get("locationId") is not None and row_location_id is None:
                db.session.rollback()
                return error_response(403, "You do not have access to the selected stock location.", "location_forbidden")
            records.append(_create_one(row, user, row_location_id or location_id))
        except ApiValidationError as error:
            db.session.rollback()
            return validation_error([{"field": f"rows.{index}.{error.field}", "message": str(error)}])
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error_response(409, "The inventory entry conflicts with current catalog or location data.", "inventory_conflict")
    result = [_serialize(record) for record in records]
    return jsonify({"data": result}), 201


@inventory_bp.get("/<int:record_id>")
@jwt_required()
def get_inventory(record_id: int):
    record = db.session.scalar(
        select(InventoryRecord).where(
            InventoryRecord.id == record_id,
            InventoryRecord.deleted_at.is_(None),
            InventoryRecord.location_id.in_(_accessible_location_ids()),
        )
    )
    if record is None:
        return error_response(404, "Inventory record not found.", "not_found")
    return jsonify({"data": _serialize(record)})


@inventory_bp.get("/<record_identifier>/stock")
@jwt_required()
def get_inventory_stock(record_identifier: str):
    user = current_user()
    if user.role != UserRole.ADMIN:
        return error_response(403)

    record_id = _parse_record_identifier(record_identifier)
    if record_id is None:
        return error_response(404, "Inventory record not found.", "not_found")

    record = db.session.scalar(
        select(InventoryRecord).where(
            InventoryRecord.id == record_id,
            InventoryRecord.deleted_at.is_(None),
            InventoryRecord.location_id.in_(_accessible_location_ids()),
        )
    )
    if record is None:
        return error_response(404, "Inventory record not found.", "not_found")

    specification = db.session.get(Specification, record.specification_id)
    item = db.session.get(Item, specification.item_id)
    location = db.session.get(Location, record.location_id)
    quantity = db.session.scalar(
        select(v_stock.c.stock).where(
            v_stock.c.location_id == record.location_id,
            v_stock.c.specification_id == record.specification_id,
        )
    )
    quantity = Decimal(quantity or 0)
    display, secondary_display = format_quantity_display(
        quantity,
        item.unit,
        specification.pack_size,
    )
    equivalent_pieces = (
        json_number(quantity)
        if item.unit == StockUnit.PCS and specification.pack_size is not None
        else None
    )

    return jsonify({
        "data": {
            "quantity": json_number(quantity),
            "unit": item.unit.value,
            "normalizedQuantity": json_number(quantity),
            "equivalentPieces": json_number(equivalent_pieces),
            "packSize": specification.pack_size,
            "piecesPerBale": item.pieces_per_bale,
            "display": display,
            "secondaryDisplay": secondary_display,
            "locationId": str(location.id),
            "locationName": location.name,
            "specificationId": str(specification.id),
            "itemName": item.name,
            "sizeLabel": specification.label,
            "asOf": iso_datetime(datetime.now(UTC)),
        }
    })


@inventory_bp.patch("/<int:record_id>")
@jwt_required()
def update_inventory(record_id: int):
    user = current_user()
    if user.role != UserRole.ADMIN:
        return error_response(403)
    record = db.session.get(InventoryRecord, record_id)
    if record is None or record.deleted_at is not None:
        return error_response(404, "Inventory record not found.", "not_found")
    if record.location_id not in user_location_ids(user.id):
        return error_response(404, "Inventory record not found.", "not_found")

    payload = request.get_json()
    if not isinstance(payload, dict):
        return validation_error([{"field": "body", "message": "A JSON object is required."}])
    before = _record_snapshot(record)
    current_specification = db.session.get(Specification, record.specification_id)
    current_item = db.session.get(Item, current_specification.item_id)
    current_category = db.session.get(Category, current_item.category_id)
    merged = {
        "date": record.record_date.isoformat(),
        "category": current_category.name,
        "item": current_item.name,
        "size": current_specification.label,
        "quantityIn": _serialize(record)["quantityIn"],
        "quantityOut": _serialize(record)["quantityOut"],
        "handledBy": record.handled_by or "",
        "details": record.details or "",
        **payload,
    }
    values, errors = _resolve_record(merged, existing_record=record)
    if errors:
        return validation_error(errors)
    current_stock = db.session.scalar(
        select(v_stock.c.stock).where(
            v_stock.c.location_id == record.location_id,
            v_stock.c.specification_id == values["specification"].id,
        )
    ) or 0
    if values["specification"].id == record.specification_id:
        current_stock = (
            current_stock
            - (
                record.qty_in_normalized
                if record.qty_in_normalized is not None
                else record.qty_in or 0
            )
            + (
                record.qty_out_normalized
                if record.qty_out_normalized is not None
                else record.qty_out or 0
            )
        )
    if values["normalizedQuantityOut"] is not None and values["normalizedQuantityOut"] > current_stock:
        return validation_error(
            [
                {
                    "field": "quantityOut",
                    "message": "Quantity Out cannot exceed the available stock for this product and location.",
                }
            ]
        )
    if "status" in payload and (
        not isinstance(payload["status"], str)
        or payload["status"] not in {status.value for status in RecordStatus}
    ):
        return validation_error([{"field": "status", "message": "Status must be Saved or Locked."}])
    record.record_date = values["date"]
    record.specification_id = values["specification"].id
    record.qty_in = values["normalizedQuantityIn"]
    record.qty_out = values["normalizedQuantityOut"]
    record.entered_unit = values["enteredUnit"]
    record.pieces_per_unit = values["piecesPerUnit"]
    record.qty_in_normalized = values["normalizedQuantityIn"]
    record.qty_out_normalized = values["normalizedQuantityOut"]
    record.handled_by = values["handledBy"]
    record.details = values["details"]
    if "status" in payload:
        record.status = RecordStatus(payload["status"])
    record.updated_by = user.id
    record.updated_at = datetime.now(UTC)
    audit(
        AuditEntity.INVENTORY_RECORD,
        record.id,
        AuditAction.LOCK if record.status == RecordStatus.LOCKED and before["status"] != "Locked" else AuditAction.UPDATE,
        user.id,
        before=before,
        after=_record_snapshot(record),
    )
    db.session.commit()
    return jsonify({"data": _serialize(record)})


@inventory_bp.delete("/<int:record_id>")
@jwt_required()
def delete_inventory(record_id: int):
    user = current_user()
    if user.role != UserRole.ADMIN:
        return error_response(403)
    record = db.session.get(InventoryRecord, record_id)
    if record is None or record.deleted_at is not None or record.location_id not in user_location_ids(user.id):
        return error_response(404, "Inventory record not found.", "not_found")
    before = _record_snapshot(record)
    record.deleted_at = datetime.now(UTC)
    audit(AuditEntity.INVENTORY_RECORD, record.id, AuditAction.DELETE, user.id, before=before)
    db.session.commit()
    return jsonify({"data": {"id": record.id}})
