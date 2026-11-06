"""Read-only inventory lookup assistant endpoint."""

import re
from datetime import date, timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func, or_, select

from app.api_utils import current_user, json_number
from app.errors import error_response, validation_error
from app.extensions import db
from app.inventory import _serialize
from app.models import (
    AssistantQuery,
    Category,
    InventoryRecord,
    Item,
    Specification,
    UserRole,
)
from app.users import users_bp  # noqa: F401
from app.api_utils import user_location_ids

assistant_bp = Blueprint("assistant", __name__, url_prefix="/api/assistant")


@assistant_bp.post("/query")
@jwt_required()
def query_inventory():
    user = current_user()
    if user.role != UserRole.ADMIN:
        return error_response(403)
    payload = request.get_json()
    question = payload.get("question") if isinstance(payload, dict) else None
    if not isinstance(question, str) or not question.strip():
        return validation_error([{"field": "question", "message": "Ask a question first."}])
    question = question.strip()
    if len(question) > 500:
        return validation_error([{"field": "question", "message": "Keep your question to 500 characters or fewer."}])

    query = question.lower()
    locations = user_location_ids(user.id)
    items = db.session.scalars(
        select(Item).where(Item.active.is_(True)).order_by(func.length(Item.name).desc())
    ).all()
    item = next((candidate for candidate in items if candidate.name.lower() in query), None)
    categories = db.session.scalars(
        select(Category).where(Category.active.is_(True)).order_by(func.length(Category.name).desc())
    ).all()
    category = next((candidate for candidate in categories if candidate.name.lower() in query), None)
    specification = None
    if item is not None:
        specifications = db.session.scalars(
            select(Specification)
            .where(Specification.item_id == item.id, Specification.active.is_(True))
            .order_by(func.length(Specification.label).desc())
        ).all()
        specification = next(
            (candidate for candidate in specifications if candidate.label.lower() in query),
            None,
        )

    conditions = [
        InventoryRecord.deleted_at.is_(None),
        InventoryRecord.location_id.in_(locations) if locations else False,
    ]
    if item is not None:
        conditions.append(Specification.item_id == item.id)
    elif category is not None:
        conditions.append(Item.category_id == category.id)
    if specification is not None:
        conditions.append(InventoryRecord.specification_id == specification.id)

    direction = (
        "in"
        if re.search(r"\b(received|receive|incoming|inbound)\b", query)
        else "out"
        if re.search(r"\b(went out|go out|outgoing|outbound|issued|dispatch|dispatched|sold|out)\b", query)
        else None
    )
    if direction == "in":
        conditions.append(InventoryRecord.qty_in > 0)
    elif direction == "out":
        conditions.append(InventoryRecord.qty_out > 0)

    date_range = re.search(
        r"\b(?:from|between)\s+(\d{4}-\d{2}-\d{2})\s+(?:to|and)\s+(\d{4}-\d{2}-\d{2})\b",
        query,
    )
    start_date = end_date = None
    if date_range:
        try:
            start_date = date.fromisoformat(date_range.group(1))
            end_date = date.fromisoformat(date_range.group(2))
        except ValueError:
            return validation_error([{"field": "question", "message": "Enter a valid date range in YYYY-MM-DD format."}])
        if start_date > end_date:
            return validation_error([{"field": "question", "message": "The date range start must be on or before its end."}])
    elif "yesterday" in query:
        start_date = end_date = date.today() - timedelta(days=1)
    elif "today" in query:
        start_date = end_date = date.today()
    elif "this week" in query:
        today = date.today()
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    if start_date:
        conditions.append(InventoryRecord.record_date >= start_date)
    if end_date:
        conditions.append(InventoryRecord.record_date <= end_date)

    keyword_match = re.search(
        r"\bdetails?\s+(?:mention|mentions|contain|contains|say|says)\s+(.+)|\bmention\s+(.+)",
        query,
    )
    keyword = next((value for value in keyword_match.groups() if value), None) if keyword_match else None
    if keyword:
        keyword = re.sub(r"[?.!,;:]+$", "", keyword).strip()
        conditions.append(InventoryRecord.details.ilike(f"%{keyword}%"))
    elif item is None and category is None and not date_range:
        ignored = {
            "how", "much", "what", "show", "find", "entries", "where", "the",
            "details", "mention", "mentions", "received", "receive", "incoming",
            "inbound", "went", "out", "today", "yesterday", "this", "week",
            "stock", "balance", "remaining", "left", "from", "between", "and",
            "with", "for", "in", "on", "of", "is",
        }
        terms = [
            term.strip(".,?!;:()")
            for term in query.split()
            if len(term.strip(".,?!;:()")) > 2
            and term.strip(".,?!;:()") not in ignored
        ]
        if terms:
            statement = select(InventoryRecord.id).join(
                InventoryRecord.specification
            ).join(Specification.item).join(Item.category)
            statement = statement.where(
                InventoryRecord.location_id.in_(locations) if locations else False,
                InventoryRecord.deleted_at.is_(None),
                or_(
                    *[
                        field.ilike(f"%{term}%")
                        for term in terms
                        for field in (
                            Category.name,
                            Item.name,
                            Specification.label,
                            InventoryRecord.details,
                        )
                    ]
                ),
            )
            matching_ids = db.session.scalars(statement).all()
            conditions.append(InventoryRecord.id.in_(matching_ids))

    statement = (
        select(InventoryRecord)
        .join(InventoryRecord.specification)
        .join(Specification.item)
        .join(Item.category)
        .where(*conditions)
        .order_by(InventoryRecord.record_date.desc(), InventoryRecord.id.desc())
    )
    matching = db.session.scalars(statement).all()
    total = len(matching)
    result_records = matching[:5]
    wants_stock = bool(re.search(r"\b(stock|balance|remaining|left)\b", query))
    if wants_stock and item is not None:
        balance = sum(
            (record.qty_in or 0) - (record.qty_out or 0)
            for record in matching
        )
        answer = (
            f"Recorded stock for {item.name} ({specification.label}) is {json_number(balance)}."
            if specification
            else f"Recorded stock for {item.name} is {json_number(balance)} across its specifications."
        )
    elif total:
        answer = f"I found {total} matching inventory {'record' if total == 1 else 'records'}."
        if total > 5:
            answer += " Showing the first 5."
    else:
        answer = "I couldn't find any matching records."

    db.session.add(
        AssistantQuery(
            user_id=user.id,
            question=question,
            tools_called={"itemId": item.id if item else None, "categoryId": category.id if category else None},
            result_count=total,
        )
    )
    db.session.commit()
    return jsonify({
        "data": {
            "answer": answer,
            "records": [_serialize(record) for record in result_records],
            "totalMatches": total,
            "searchQuery": keyword or (item.name if item else None) or (category.name if category else question),
        }
    })