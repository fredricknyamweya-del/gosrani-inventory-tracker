"""Persistent product catalog and staff request endpoints."""

from datetime import UTC, datetime
from decimal import Decimal

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import delete, func, select
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
    ItemRequest,
    Location,
    RequestStatus,
    Specification,
    StockUnit,
    User,
    UserRole,
    v_stock,
)
from app.units import format_quantity_display

catalog_bp = Blueprint("catalog", __name__, url_prefix="/api/catalog")


def _serialize_category(category: Category) -> dict[str, object]:
    return {"id": str(category.id), "name": category.name, "active": category.active}


def _serialize_item(item: Item) -> dict[str, object]:
    specifications = db.session.scalars(
        select(Specification)
        .where(Specification.item_id == item.id, Specification.active.is_(True))
        .order_by(Specification.id)
    ).all()
    return {
        "id": str(item.id),
        "categoryId": str(item.category_id),
        "name": item.name,
        "unit": item.unit.value,
        "entryUnit": item.entry_unit.value,
        "inventoryUnit": item.inventory_unit.value,
        "piecesPerBale": item.pieces_per_bale,
        "active": item.active,
        "specifications": [specification.label for specification in specifications],
        "specificationPackSizes": [
            {"label": specification.label, "packSize": specification.pack_size}
            for specification in specifications
        ],
    }


def _serialize_request(item_request: ItemRequest) -> dict[str, object]:
    category = db.session.get(Category, item_request.category_id) if item_request.category_id else None
    requester = db.session.get(User, item_request.requested_by)
    reviewer = (
        db.session.get(User, item_request.reviewed_by)
        if item_request.reviewed_by
        else None
    )
    request_type = (
        "category"
        if item_request.new_category_name
        else "specification"
        if item_request.item_id
        else "product"
    )
    return {
        "id": str(item_request.id),
        "requestType": request_type,
        "categoryId": str(item_request.category_id) if item_request.category_id else None,
        "category": category.name if category else item_request.new_category_name or "",
        "categoryName": item_request.new_category_name or "",
        "itemId": str(item_request.item_id) if item_request.item_id else None,
        "itemName": item_request.item_name,
        "specification": item_request.specification or "",
        "note": item_request.note or "",
        "requestedById": item_request.requested_by,
        "requestedBy": requester.name if requester else "",
        "status": item_request.status.value,
        "createdAt": iso_datetime(item_request.created_at),
        "processedBy": reviewer.name if reviewer else None,
        "processedAt": iso_datetime(item_request.reviewed_at),
        "reason": item_request.reject_reason or "",
    }


def _require_admin():
    user = current_user()
    if user.role != UserRole.ADMIN:
        return None, error_response(403)
    return user, None


def _required_text(payload: dict, key: str, label: str, maximum: int) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ApiValidationError(key, f"{label} is required.")
    value = value.strip()
    if len(value) > maximum:
        raise ApiValidationError(key, f"{label} must be {maximum} characters or fewer.")
    return value


def _find_category(value: object) -> Category | None:
    if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
        return db.session.get(Category, int(value))
    if isinstance(value, str) and value.strip():
        return db.session.scalar(
            select(Category).where(func.lower(func.trim(Category.name)) == value.strip().lower())
        )
    return None


def _find_item(value: object, category_id: int) -> Item | None:
    if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
        return db.session.scalar(
            select(Item).where(Item.id == int(value), Item.category_id == category_id)
        )
    if isinstance(value, str) and value.strip():
        return db.session.scalar(
            select(Item).where(
                Item.category_id == category_id,
                func.lower(func.trim(Item.name)) == value.strip().lower(),
            )
        )
    return None


def _create_category(name: str, actor_id: int) -> Category:
    category = db.session.scalar(
        select(Category).where(func.lower(func.trim(Category.name)) == name.lower())
    )
    if category is not None:
        raise ApiValidationError("name", "A category with this name already exists.")
    category = Category(name=name)
    db.session.add(category)
    db.session.flush()
    audit(AuditEntity.CATEGORY, category.id, AuditAction.CREATE, actor_id, after={"name": name})
    return category


def _normalize_specifications(values: object) -> list[str]:
    if not isinstance(values, list):
        raise ApiValidationError("specifications", "Specifications must be a list.")
    labels = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ApiValidationError("specifications", "Each specification must have a name.")
        label = value.strip()
        if len(label) > 120:
            raise ApiValidationError("specifications", "Specifications must be 120 characters or fewer.")
        if label.lower() in {entry.lower() for entry in labels}:
            raise ApiValidationError("specifications", f'Specification "{label}" is duplicated.')
        labels.append(label)
    return labels


def _inventory_configuration(
    payload: dict,
    *,
    current_unit: InventoryUnit = InventoryUnit.PCS,
    current_pieces_per_bale: int | None = None,
    stock_unit: StockUnit = StockUnit.PCS,
) -> tuple[InventoryUnit, int | None]:
    unit_value = payload.get(
        "inventoryUnit",
        current_unit.value if current_unit != InventoryUnit.PCS or "unit" not in payload
        else ("KG" if payload.get("unit") == StockUnit.KG.value else current_unit.value),
    )
    try:
        inventory_unit = InventoryUnit(unit_value)
    except (TypeError, ValueError):
        raise ApiValidationError(
            "inventoryUnit", "Inventory unit must be PCS, BALE, or KG."
        ) from None

    rate = (
        payload.get("piecesPerBale")
        if "piecesPerBale" in payload
        else None
        if "inventoryUnit" in payload and inventory_unit != InventoryUnit.BALE
        else current_pieces_per_bale
    )
    if inventory_unit == InventoryUnit.BALE:
        if isinstance(rate, bool) or not isinstance(rate, int) or rate <= 0:
            raise ApiValidationError(
                "piecesPerBale",
                "Enter a positive whole number of pieces per bale before enabling bale stock.",
            )
        return inventory_unit, rate
    if rate not in (None, ""):
        raise ApiValidationError(
            "piecesPerBale", "Pieces per bale is only valid for bale-based products."
        )
    if inventory_unit == InventoryUnit.KG and stock_unit != StockUnit.KG:
        raise ApiValidationError(
            "inventoryUnit", "Kilogram inventory requires the item's stock unit to be KG."
        )
    if inventory_unit != InventoryUnit.KG and stock_unit == StockUnit.KG:
        raise ApiValidationError(
            "inventoryUnit", "Change the item's stock unit before leaving kilogram inventory."
        )
    return inventory_unit, None


def _entry_unit(
    payload: dict,
    *,
    stock_unit: StockUnit,
    current: EnteredUnit | None = None,
) -> EnteredUnit:
    fallback = current or (
        EnteredUnit.KG if stock_unit == StockUnit.KG else EnteredUnit.PCS
    )
    if "entryUnit" in payload:
        value = payload["entryUnit"]
    elif current is None and "inventoryUnit" in payload:
        value = payload["inventoryUnit"]
    else:
        value = fallback.value
    try:
        entry_unit = EnteredUnit(value)
    except (TypeError, ValueError):
        raise ApiValidationError(
            "entryUnit", "Entered unit must be BALE, PCS, or KG."
        ) from None
    if (entry_unit == EnteredUnit.KG) != (stock_unit == StockUnit.KG):
        raise ApiValidationError(
            "entryUnit",
            "KG entry units require KG stock; BALE and PCS require piece stock.",
        )
    return entry_unit


def _specification_pack_sizes(
    value: object,
    labels: list[str],
    entry_unit: EnteredUnit,
) -> dict[str, int | None]:
    if value is None:
        return {}
    if not isinstance(value, list):
        raise ApiValidationError(
            "specificationPackSizes",
            "Specification pack sizes must be a list.",
        )
    normalized: dict[str, int | None] = {}
    label_lookup = {label.casefold(): label for label in labels}
    for row in value:
        if not isinstance(row, dict):
            raise ApiValidationError(
                "specificationPackSizes",
                "Each specification pack size must include a label and packSize.",
            )
        label = row.get("label")
        if not isinstance(label, str) or label.casefold() not in label_lookup:
            raise ApiValidationError(
                "specificationPackSizes",
                "Pack sizes must refer to a specification in this item.",
            )
        key = label_lookup[label.casefold()]
        if key.casefold() in {entry.casefold() for entry in normalized}:
            raise ApiValidationError(
                "specificationPackSizes", f'Specification "{key}" is duplicated.'
            )
        raw_size = row.get("packSize")
        if raw_size in (None, ""):
            pack_size = None
        elif (
            isinstance(raw_size, bool)
            or not isinstance(raw_size, int)
            or not 1 <= raw_size <= 10_000
        ):
            raise ApiValidationError(
                "specificationPackSizes",
                "Pieces per bale must be a whole number from 1 to 10000.",
            )
        else:
            pack_size = raw_size
        if pack_size is not None and entry_unit != EnteredUnit.BALE:
            raise ApiValidationError(
                "specificationPackSizes",
                "Only BALE items can have specification pack sizes.",
            )
        normalized[key] = pack_size
    return normalized


@catalog_bp.get("")
@jwt_required()
def get_catalog():
    categories = db.session.scalars(
        select(Category).where(Category.active.is_(True)).order_by(Category.sort_order, Category.name)
    ).all()
    items = db.session.scalars(
        select(Item).join(Category).where(Category.active.is_(True)).order_by(Item.name)
    ).all()
    return jsonify({
        "data": {
            "categories": [_serialize_category(category) for category in categories],
            "items": [_serialize_item(item) for item in items],
        }
    })


@catalog_bp.get("/summary")
@jwt_required()
def get_catalog_summary():
    user = current_user()
    location_ids = user_location_ids(user.id)
    locations = db.session.execute(
        select(Location.id, Location.name)
        .where(Location.id.in_(location_ids) if location_ids else False)
        .order_by(Location.name)
    ).all()
    stock_statement = (
        select(
            v_stock.c.location_id,
            v_stock.c.specification_id,
            v_stock.c.stock,
            v_stock.c.stock_pieces,
            v_stock.c.stock_bales,
        )
        .where(v_stock.c.location_id.in_(location_ids) if location_ids else False)
    )
    stock_by_specification = {
        (row.location_id, row.specification_id): row
        for row in db.session.execute(stock_statement).all()
    }
    totals_statement = (
        select(
            InventoryRecord.location_id,
            InventoryRecord.specification_id,
            func.coalesce(
                func.sum(
                    func.coalesce(
                        InventoryRecord.qty_in_normalized,
                        InventoryRecord.qty_in,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    func.coalesce(
                        InventoryRecord.qty_out_normalized,
                        InventoryRecord.qty_out,
                    )
                ),
                0,
            ),
        )
        .where(
            InventoryRecord.deleted_at.is_(None),
            InventoryRecord.location_id.in_(location_ids) if location_ids else False,
        )
        .group_by(InventoryRecord.location_id, InventoryRecord.specification_id)
    )
    totals_by_location_and_specification = {
        (row[0], row[1]): (Decimal(row[2]), Decimal(row[3]))
        for row in db.session.execute(totals_statement).all()
    }
    specifications = db.session.execute(
        select(Specification, Item, Category.name)
        .join(Item, Item.id == Specification.item_id)
        .join(Category, Category.id == Item.category_id)
        .where(Specification.active.is_(True))
        .order_by(Category.sort_order, Category.name, Item.name, Specification.label)
    ).all()
    stock_summaries = []
    for specification, item, category_name in specifications:
        for location_id, location_name in locations:
            normalized_in, normalized_out = totals_by_location_and_specification.get(
                (location_id, specification.id), (Decimal(0), Decimal(0))
            )
            stock_row = stock_by_specification.get((location_id, specification.id))
            normalized_stock = Decimal(stock_row.stock if stock_row else 0)
            stock_bales = (
                Decimal(stock_row.stock_bales)
                if stock_row is not None and stock_row.stock_bales is not None
                else None
            )
            in_display, in_secondary = format_quantity_display(
                normalized_in,
                item.unit,
                specification.pack_size,
                entry_unit=item.entry_unit,
            )
            out_display, out_secondary = format_quantity_display(
                normalized_out,
                item.unit,
                specification.pack_size,
                entry_unit=item.entry_unit,
            )
            stock_display, stock_secondary = format_quantity_display(
                normalized_stock,
                item.unit,
                specification.pack_size,
                entry_unit=item.entry_unit,
                bales=stock_bales,
            )
            stock_summaries.append(
                {
                    "id": str(specification.id),
                    "itemName": item.name,
                    "category": category_name,
                    "size": specification.label,
                    "unit": item.unit.value,
                    "entryUnit": item.entry_unit.value,
                    "inventoryUnit": item.inventory_unit.value,
                    "packSize": specification.pack_size,
                    "locationId": str(location_id),
                    "locationName": location_name,
                    "totalStockIn": json_number(normalized_in),
                    "totalStockInDisplay": in_display,
                    "totalStockInSecondaryDisplay": in_secondary,
                    "totalStockOut": json_number(normalized_out),
                    "totalStockOutDisplay": out_display,
                    "totalStockOutSecondaryDisplay": out_secondary,
                    "remainingStock": json_number(normalized_stock),
                    "stockPieces": (
                        json_number(stock_row.stock_pieces)
                        if stock_row is not None
                        else None
                    ),
                    "stockBales": json_number(stock_bales),
                    "display": stock_display,
                    "secondaryDisplay": stock_secondary,
                    "equivalentPieces": (
                        json_number(normalized_stock)
                        if item.unit == StockUnit.PCS
                        and specification.pack_size is not None
                        else None
                    ),
                }
            )

    items = db.session.execute(
        select(Item, Category.name)
        .join(Category, Category.id == Item.category_id)
        .order_by(Category.sort_order, Category.name, Item.name)
    ).all()
    item_entries_statement = (
        select(
            Item.id,
            func.count(InventoryRecord.id),
            func.max(InventoryRecord.record_date),
        )
        .join(Specification, Specification.item_id == Item.id)
        .join(InventoryRecord, InventoryRecord.specification_id == Specification.id)
        .where(
            InventoryRecord.deleted_at.is_(None),
            InventoryRecord.location_id.in_(location_ids) if location_ids else False,
        )
        .group_by(Item.id)
    )
    entries_by_item = {
        row[0]: (row[1], row[2])
        for row in db.session.execute(item_entries_statement).all()
    }

    product_summaries = []
    for item, category_name in items:
        entry_count, last_date = entries_by_item.get(item.id, (0, None))
        product_summaries.append(
            {
                "id": str(item.id),
                "productName": item.name,
                "category": category_name,
                "inventoryUnit": item.inventory_unit.value,
                "entryUnit": item.entry_unit.value,
                "piecesPerBale": item.pieces_per_bale,
                "totalEntries": entry_count,
                "lastTransactionDate": last_date.isoformat() if last_date else None,
            }
        )

    return jsonify(
        {
            "data": {
                "products": product_summaries,
                "stockBySpecification": stock_summaries,
                "totals": {
                    "registeredProducts": len(items),
                    "baleBasedProducts": sum(
                        item.entry_unit == EnteredUnit.BALE for item, _ in items
                    ),
                    "pieceBasedProducts": sum(
                        item.entry_unit == EnteredUnit.PCS for item, _ in items
                    ),
                    "kilogramBasedProducts": sum(
                        item.entry_unit == EnteredUnit.KG for item, _ in items
                    ),
                    "stockEntries": sum(
                        summary["totalEntries"] for summary in product_summaries
                    ),
                },
            }
        }
    )


@catalog_bp.post("/categories")
@jwt_required()
def create_category():
    user, denied = _require_admin()
    if denied:
        return denied
    payload = request.get_json()
    if not isinstance(payload, dict):
        return validation_error([{"field": "body", "message": "A JSON object is required."}])
    try:
        name = _required_text(payload, "name", "Category name", 100)
        category = _create_category(name, user.id)
        db.session.commit()
    except ApiValidationError as error:
        db.session.rollback()
        return validation_error([{"field": error.field, "message": str(error)}])
    except IntegrityError:
        db.session.rollback()
        return error_response(409, "A category with this name already exists.", "catalog_conflict")
    return jsonify({"data": _serialize_category(category)}), 201


@catalog_bp.post("/items")
@jwt_required()
def create_item():
    user, denied = _require_admin()
    if denied:
        return denied
    payload = request.get_json()
    if not isinstance(payload, dict):
        return validation_error([{"field": "body", "message": "A JSON object is required."}])
    try:
        category = _find_category(payload.get("categoryId", payload.get("category")))
        if category is None or not category.active:
            raise ApiValidationError("categoryId", "Choose a valid active catalog category.")
        name = _required_text(payload, "name", "Item name", 120)
        specifications = _normalize_specifications(payload.get("specifications"))
        if not specifications:
            raise ApiValidationError("specifications", "Add at least one item specification.")
        unit_value = payload.get("unit", StockUnit.PCS.value)
        try:
            unit = StockUnit(unit_value)
        except (TypeError, ValueError):
            raise ApiValidationError("unit", "Unit must be PCS or KG.") from None
        entry_unit = _entry_unit(payload, stock_unit=unit)
        if "inventoryUnit" in payload or (
            "piecesPerBale" in payload
            and "specificationPackSizes" not in payload
        ):
            inventory_unit, pieces_per_bale = _inventory_configuration(
                payload, stock_unit=unit
            )
        else:
            inventory_unit = InventoryUnit(entry_unit.value)
            pieces_per_bale = None
        specification_pack_sizes = _specification_pack_sizes(
            payload.get("specificationPackSizes"),
            specifications,
            entry_unit,
        )
        item = Item(
            category_id=category.id,
            name=name,
            unit=unit,
            entry_unit=entry_unit,
            inventory_unit=inventory_unit,
            pieces_per_bale=pieces_per_bale,
        )
        db.session.add(item)
        db.session.flush()
        for label in specifications:
            db.session.add(
                Specification(
                    item_id=item.id,
                    label=label,
                    pack_size=specification_pack_sizes.get(label),
                )
            )
        audit(
            AuditEntity.ITEM,
            item.id,
            AuditAction.CREATE,
            user.id,
            after={"categoryId": category.id, "name": name, "specifications": specifications},
        )
        db.session.commit()
    except ApiValidationError as error:
        db.session.rollback()
        return validation_error([{"field": error.field, "message": str(error)}])
    except IntegrityError:
        db.session.rollback()
        return error_response(409, "An item or specification with this name already exists.", "catalog_conflict")
    return jsonify({"data": _serialize_item(item)}), 201


@catalog_bp.patch("/items/<int:item_id>")
@jwt_required()
def update_item(item_id: int):
    user, denied = _require_admin()
    if denied:
        return denied
    item = db.session.get(Item, item_id)
    if item is None:
        return error_response(404, "Catalog item not found.", "not_found")
    payload = request.get_json()
    if not isinstance(payload, dict):
        return validation_error([{"field": "body", "message": "A JSON object is required."}])
    before = _serialize_item(item)
    try:
        if "entryUnit" in payload:
            entry_unit = _entry_unit(
                payload,
                stock_unit=item.unit,
                current=item.entry_unit,
            )
            if entry_unit != item.entry_unit:
                has_inventory = db.session.scalar(
                    select(InventoryRecord.id)
                    .join(
                        Specification,
                        Specification.id == InventoryRecord.specification_id,
                    )
                    .where(Specification.item_id == item.id)
                    .limit(1)
                )
                if has_inventory:
                    db.session.rollback()
                    return error_response(
                        409,
                        "An item's entered unit cannot be changed after inventory records exist.",
                        "item_entry_unit_immutable",
                    )
            item.entry_unit = entry_unit

        if "name" in payload:
            item.name = _required_text(payload, "name", "Item name", 120)
        if "active" in payload:
            if not isinstance(payload["active"], bool):
                raise ApiValidationError("active", "Active must be a boolean.")
            item.active = payload["active"]
        if "inventoryUnit" in payload or "piecesPerBale" in payload:
            inventory_unit, pieces_per_bale = _inventory_configuration(
                payload,
                current_unit=item.inventory_unit,
                current_pieces_per_bale=item.pieces_per_bale,
                stock_unit=item.unit,
            )
            if inventory_unit != item.inventory_unit:
                has_inventory = db.session.scalar(
                    select(InventoryRecord.id)
                    .join(
                        Specification,
                        Specification.id == InventoryRecord.specification_id,
                    )
                    .where(Specification.item_id == item.id)
                    .limit(1)
                )
                if has_inventory and (
                    inventory_unit == InventoryUnit.KG
                ) != (item.inventory_unit == InventoryUnit.KG):
                    raise ApiValidationError(
                        "inventoryUnit",
                        "An item's kilogram or piece-based stock type cannot be changed after stock transactions exist.",
                    )
            item.inventory_unit = inventory_unit
            item.pieces_per_bale = pieces_per_bale

        active_specs = db.session.scalars(
            select(Specification).where(Specification.item_id == item.id)
        ).all()
        by_name = {spec.label.lower(): spec for spec in active_specs}
        if "specifications" in payload:
            desired = _normalize_specifications(payload["specifications"])
        else:
            desired = [spec.label for spec in active_specs if spec.active]
        if "addSpecifications" in payload:
            additions = _normalize_specifications(payload["addSpecifications"])
            for label in additions:
                if label.lower() in {entry.lower() for entry in desired}:
                    raise ApiValidationError("addSpecifications", f'Specification "{label}" already exists.')
                desired.append(label)
        if "removeSpecifications" in payload:
            removals = payload["removeSpecifications"]
            if not isinstance(removals, list) or not all(isinstance(value, str) for value in removals):
                raise ApiValidationError("removeSpecifications", "Specifications to remove must be a list of names.")
            removal_set = {value.strip().lower() for value in removals}
            desired = [label for label in desired if label.lower() not in removal_set]
        specification_pack_sizes = (
            _specification_pack_sizes(
                payload["specificationPackSizes"],
                desired,
                item.entry_unit,
            )
            if "specificationPackSizes" in payload
            else {}
        )
        desired_keys = {label.lower() for label in desired}
        for specification in active_specs:
            specification.active = specification.label.lower() in desired_keys
        for label in desired:
            existing = by_name.get(label.lower())
            if existing is None:
                db.session.add(
                    Specification(
                        item_id=item.id,
                        label=label,
                        pack_size=specification_pack_sizes.get(label),
                    )
                )
            else:
                existing.label = label
                existing.active = True
                if label in specification_pack_sizes:
                    requested_pack_size = specification_pack_sizes[label]
                    if requested_pack_size != existing.pack_size:
                        has_inventory = db.session.scalar(
                            select(InventoryRecord.id)
                            .where(
                                InventoryRecord.specification_id == existing.id
                            )
                            .limit(1)
                        )
                        if has_inventory:
                            db.session.rollback()
                            return error_response(
                                409,
                                "A specification pack size cannot be changed after inventory records exist.",
                                "specification_pack_size_immutable",
                            )
                        existing.pack_size = requested_pack_size
        db.session.flush()
        if item.entry_unit != EnteredUnit.BALE and db.session.scalar(
            select(Specification.id)
            .where(
                Specification.item_id == item.id,
                Specification.pack_size.is_not(None),
            )
            .limit(1)
        ):
            raise ApiValidationError(
                "specificationPackSizes",
                "PCS and KG items cannot have specification pack sizes.",
            )
        after = _serialize_item(item)
        audit(AuditEntity.ITEM, item.id, AuditAction.UPDATE, user.id, before=before, after=after)
        db.session.commit()
    except ApiValidationError as error:
        db.session.rollback()
        return validation_error([{"field": error.field, "message": str(error)}])
    except IntegrityError:
        db.session.rollback()
        return error_response(409, "The catalog update conflicts with an existing item or specification.", "catalog_conflict")
    return jsonify({"data": _serialize_item(item)})


@catalog_bp.delete("/items/<int:item_id>")
@jwt_required()
def delete_item(item_id: int):
    user, denied = _require_admin()
    if denied:
        return denied
    item = db.session.get(Item, item_id)
    if item is None:
        return error_response(404, "Catalog item not found.", "not_found")

    has_inventory = db.session.scalar(
        select(InventoryRecord.id)
        .join(Specification, Specification.id == InventoryRecord.specification_id)
        .where(Specification.item_id == item.id)
        .limit(1)
    )
    if has_inventory:
        return error_response(
            409,
            "This item has inventory history and cannot be permanently deleted. Deactivate it instead.",
            "item_has_inventory",
        )

    has_requests = db.session.scalar(
        select(ItemRequest.id).where(ItemRequest.item_id == item.id).limit(1)
    )
    if has_requests:
        return error_response(
            409,
            "This item is referenced by catalog requests and cannot be permanently deleted. Deactivate it instead.",
            "item_has_requests",
        )

    before = _serialize_item(item)
    try:
        audit(
            AuditEntity.ITEM,
            item.id,
            AuditAction.DELETE,
            user.id,
            before=before,
        )
        db.session.execute(
            delete(Specification).where(Specification.item_id == item.id)
        )
        db.session.delete(item)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error_response(
            409,
            "This item is linked to historical records and cannot be permanently deleted. Deactivate it instead.",
            "item_delete_conflict",
        )
    return jsonify({"data": {"id": item_id}})


@catalog_bp.get("/requests")
@jwt_required()
def list_requests():
    user = current_user()
    statement = select(ItemRequest).order_by(ItemRequest.created_at.desc(), ItemRequest.id.desc())
    if user.role != UserRole.ADMIN:
        statement = statement.where(ItemRequest.requested_by == user.id)
    requests = db.session.scalars(statement).all()
    return jsonify({"data": [_serialize_request(item_request) for item_request in requests]})


@catalog_bp.post("/requests")
@jwt_required()
def create_request():
    user = current_user()
    payload = request.get_json()
    if not isinstance(payload, dict):
        return validation_error([{"field": "body", "message": "A JSON object is required."}])
    if user.role != UserRole.USER:
        return error_response(403, "Only staff users can submit catalog requests.", "forbidden")
    request_type = payload.get("requestType")
    if request_type not in {"category", "product", "specification"}:
        return validation_error([{"field": "requestType", "message": "Choose category, product, or specification."}])
    try:
        category = None
        item = None
        category_name = None
        specification_name = None
        if request_type == "category":
            category_name = _required_text(payload, "categoryName", "Category name", 100)
            if db.session.scalar(select(Category.id).where(func.lower(func.trim(Category.name)) == category_name.lower())):
                raise ApiValidationError("categoryName", "A category with this name already exists.")
            item_name = category_name
        else:
            category = _find_category(payload.get("categoryId"))
            if category is None or not category.active:
                raise ApiValidationError("categoryId", "Choose a valid active category.")
            if request_type == "product":
                item_name = _required_text(payload, "itemName", "Product name", 120)
                if _find_item(item_name, category.id) is not None:
                    raise ApiValidationError("itemName", "This product already exists; request a missing specification instead.")
            else:
                item = _find_item(payload.get("itemId"), category.id)
                if item is None:
                    raise ApiValidationError("itemId", "Choose a valid existing catalog product.")
                item_name = item.name
            specification_name = _required_text(payload, "specification", "Specification", 120)
            if item is not None and db.session.scalar(
                select(Specification.id).where(
                    Specification.item_id == item.id,
                    Specification.active.is_(True),
                    func.lower(func.trim(Specification.label)) == specification_name.lower(),
                )
            ):
                raise ApiValidationError("specification", "This specification is already available in the catalog.")
        note = payload.get("note", "")
        if not isinstance(note, str) or len(note) > 2000:
            raise ApiValidationError("note", "Note must be 2,000 characters or fewer.")
        duplicate = db.session.scalar(
            select(ItemRequest.id).where(
                ItemRequest.requested_by == user.id,
                ItemRequest.status == RequestStatus.PENDING,
                ItemRequest.category_id == (category.id if category else None),
                ItemRequest.new_category_name == category_name,
                ItemRequest.item_id == (item.id if item else None),
                ItemRequest.item_name == item_name,
                ItemRequest.specification == specification_name,
            )
        )
        if duplicate:
            raise ApiValidationError("request", "A matching catalog request is already pending.")
        item_request = ItemRequest(
            requested_by=user.id,
            category_id=category.id if category else None,
            item_id=item.id if item else None,
            new_category_name=category_name,
            item_name=item_name,
            specification=specification_name,
            note=note.strip(),
        )
        db.session.add(item_request)
        db.session.flush()
        audit(AuditEntity.ITEM_REQUEST, item_request.id, AuditAction.CREATE, user.id, after={
            "requestType": request_type,
            "categoryId": category.id if category else None,
            "categoryName": category_name,
            "itemName": item_name,
            "specification": specification_name,
        })
        db.session.commit()
    except ApiValidationError as error:
        db.session.rollback()
        return validation_error([{"field": error.field, "message": str(error)}])
    except IntegrityError:
        db.session.rollback()
        return error_response(409, "The catalog request conflicts with current catalog data.", "request_conflict")
    return jsonify({"data": _serialize_request(item_request)}), 201


@catalog_bp.patch("/requests/<int:request_id>")
@jwt_required()
def review_request(request_id: int):
    user, denied = _require_admin()
    if denied:
        return denied
    item_request = db.session.get(ItemRequest, request_id)
    if item_request is None:
        return error_response(404, "Catalog request not found.", "not_found")
    if item_request.status != RequestStatus.PENDING:
        return validation_error([{"field": "status", "message": "This catalog request has already been processed."}])
    payload = request.get_json()
    if not isinstance(payload, dict):
        return validation_error([{"field": "body", "message": "A JSON object is required."}])
    action = str(payload.get("action", "")).lower()
    before = _serialize_request(item_request)
    try:
        if action == "approve":
            if item_request.new_category_name:
                name = str(payload.get("categoryName") or item_request.new_category_name).strip()
                _create_category(_required_text({"name": name}, "name", "Category name", 100), user.id)
            elif item_request.category_id is not None:
                category = db.session.get(Category, item_request.category_id)
                if category is None:
                    return error_response(404, "Requested category no longer exists.", "not_found")
                item_name = str(payload.get("itemName") or item_request.item_name).strip()
                existing_item = db.session.get(Item, item_request.item_id) if item_request.item_id else None
                if item_request.item_id and existing_item is None:
                    return error_response(404, "Requested catalog item no longer exists.", "not_found")
                if existing_item is not None:
                    specification = _required_text(
                        {"specification": item_request.specification},
                        "specification",
                        "Specification",
                        120,
                    )
                    existing = db.session.scalar(
                        select(Specification).where(
                            Specification.item_id == existing_item.id,
                            func.lower(func.trim(Specification.label)) == specification.lower(),
                        )
                    )
                    if existing is not None and existing.active:
                        raise ApiValidationError("specification", "This specification already exists.")
                    if existing is None:
                        db.session.add(Specification(item_id=existing_item.id, label=specification))
                    else:
                        existing.active = True
                    if item_name.lower() != existing_item.name.lower():
                        existing_item.name = _required_text({"name": item_name}, "name", "Item name", 120)
                    audit(AuditEntity.ITEM, existing_item.id, AuditAction.UPDATE, user.id)
                else:
                    if db.session.scalar(
                        select(Item.id).where(
                            Item.category_id == category.id,
                            func.lower(func.trim(Item.name)) == item_name.lower(),
                        )
                    ):
                        raise ApiValidationError("itemName", "An item with this name already exists.")
                    item = Item(category_id=category.id, name=_required_text({"name": item_name}, "name", "Item name", 120))
                    db.session.add(item)
                    db.session.flush()
                    specification = _required_text(
                        {"specification": item_request.specification},
                        "specification",
                        "Specification",
                        120,
                    )
                    db.session.add(Specification(item_id=item.id, label=specification))
                    audit(AuditEntity.ITEM, item.id, AuditAction.CREATE, user.id, after={
                        "categoryId": category.id,
                        "name": item.name,
                        "specifications": [specification],
                    })
            item_request.status = RequestStatus.APPROVED
            item_request.reject_reason = None
        elif action == "reject":
            reason = payload.get("reason", "")
            if not isinstance(reason, str) or len(reason) > 2000:
                raise ApiValidationError("reason", "Reason must be 2,000 characters or fewer.")
            item_request.status = RequestStatus.REJECTED
            item_request.reject_reason = reason.strip()
        else:
            raise ApiValidationError("action", "Request action must be approve or reject.")
        item_request.reviewed_by = user.id
        item_request.reviewed_at = datetime.now(UTC)
        audit(
            AuditEntity.ITEM_REQUEST,
            item_request.id,
            AuditAction.APPROVE if action == "approve" else AuditAction.REJECT,
            user.id,
            before=before,
            after=_serialize_request(item_request),
        )
        db.session.commit()
    except ApiValidationError as error:
        db.session.rollback()
        return validation_error([{"field": error.field, "message": str(error)}])
    except IntegrityError:
        db.session.rollback()
        return error_response(409, "The approval conflicts with an existing catalog item.", "catalog_conflict")
    return jsonify({"data": _serialize_request(item_request)})
