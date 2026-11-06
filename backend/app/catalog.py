"""Persistent product catalog and staff request endpoints."""

from datetime import UTC, datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api_utils import ApiValidationError, audit, current_user, iso_datetime
from app.errors import error_response, validation_error
from app.extensions import db
from app.models import (
    AuditAction,
    AuditEntity,
    Category,
    Item,
    ItemRequest,
    RequestStatus,
    Specification,
    StockUnit,
    User,
    UserRole,
)

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
        "active": item.active,
        "specifications": [specification.label for specification in specifications],
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
        item = Item(category_id=category.id, name=name, unit=unit)
        db.session.add(item)
        db.session.flush()
        for label in specifications:
            db.session.add(Specification(item_id=item.id, label=label))
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
        if "name" in payload:
            item.name = _required_text(payload, "name", "Item name", 120)
        if "active" in payload:
            if not isinstance(payload["active"], bool):
                raise ApiValidationError("active", "Active must be a boolean.")
            item.active = payload["active"]

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
        desired_keys = {label.lower() for label in desired}
        for specification in active_specs:
            specification.active = specification.label.lower() in desired_keys
        for label in desired:
            existing = by_name.get(label.lower())
            if existing is None:
                db.session.add(Specification(item_id=item.id, label=label))
            else:
                existing.label = label
                existing.active = True
        db.session.flush()
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
