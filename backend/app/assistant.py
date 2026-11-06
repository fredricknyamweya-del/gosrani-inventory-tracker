"""Read-only inventory assistant endpoints."""

import re
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func, or_, select

from app.api_utils import current_user, json_number, user_location_ids
from app.errors import error_response, validation_error
from app.extensions import db
from app.models import (
    AssistantQuery,
    Category,
    InventoryRecord,
    Item,
    Specification,
    UserRole,
)

assistant_bp = Blueprint("assistant", __name__, url_prefix="/api/assistant")

_STOP_WORDS = {
    "a",
    "all",
    "and",
    "are",
    "balance",
    "between",
    "find",
    "for",
    "from",
    "have",
    "how",
    "in",
    "is",
    "it",
    "left",
    "me",
    "mention",
    "mentions",
    "much",
    "of",
    "on",
    "out",
    "records",
    "remaining",
    "show",
    "stock",
    "the",
    "this",
    "today",
    "to",
    "where",
    "what",
    "which",
    "with",
    "yesterday",
    "week",
    "received",
    "receive",
    "incoming",
    "inbound",
    "went",
    "going",
    "outgoing",
    "outbound",
    "issued",
    "dispatch",
    "dispatched",
    "sold",
    "quantity",
    "entries",
    "entry",
    "details",
}


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _match_catalog_name(
    query: str, values: list[tuple[int, str]]
) -> tuple[int, str] | None:
    return next(
        (
            value
            for value in sorted(values, key=lambda entry: len(entry[1]), reverse=True)
            if _normalized(value[1]) in query
        ),
        None,
    )


def _date_range(query: str) -> tuple[date | None, date | None]:
    explicit = re.search(
        r"\b(?:from\s+(\d{4}-\d{2}-\d{2})\s+to|between\s+(\d{4}-\d{2}-\d{2})\s+and)\s+(\d{4}-\d{2}-\d{2})\b",
        query,
    )
    if explicit:
        start_text, alternate_start, end_text = explicit.groups()
        start_text = start_text or alternate_start
        try:
            start = date.fromisoformat(start_text)
            end = date.fromisoformat(end_text)
        except ValueError:
            raise ValueError("Enter a valid date range in YYYY-MM-DD format.") from None
        if (
            start.isoformat() != start_text
            or end.isoformat() != end_text
            or start > end
        ):
            raise ValueError("Enter a valid date range in YYYY-MM-DD format.")
        return start, end

    today = date.today()
    if re.search(r"\byesterday\b", query):
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    if re.search(r"\btoday\b", query):
        return today, today
    if re.search(r"\bthis week\b", query):
        return today - timedelta(days=today.weekday()), today
    return None, None


def _format_quantity(value: Decimal) -> str:
    return format(value.normalize(), "f")


@assistant_bp.post("/query")
@jwt_required()
def query_assistant():
    user = current_user()
    if user.role != UserRole.ADMIN:
        return error_response(403)

    payload = request.get_json()
    if not isinstance(payload, dict):
        return validation_error(
            [{"field": "body", "message": "A JSON object is required."}]
        )
    question = payload.get("question")
    if not isinstance(question, str) or not question.strip():
        return validation_error(
            [{"field": "question", "message": "Ask a question first."}]
        )
    question = question.strip()
    if len(question) > 500:
        return validation_error(
            [
                {
                    "field": "question",
                    "message": "Keep your question to 500 characters or fewer.",
                }
            ]
        )

    hourly_limit = current_app.config.get("ASSISTANT_HOURLY_LIMIT", 30)
    if not isinstance(hourly_limit, int) or hourly_limit < 1:
        raise ValueError("ASSISTANT_HOURLY_LIMIT must be a positive integer.")
    cutoff = datetime.now(UTC) - timedelta(hours=1)
    recent_queries = (
        db.session.scalar(
            select(func.count(AssistantQuery.id)).where(
                AssistantQuery.user_id == user.id,
                AssistantQuery.at >= cutoff,
            )
        )
        or 0
    )
    if recent_queries >= hourly_limit:
        return error_response(429)

    query = _normalized(question)
    categories = db.session.execute(select(Category.id, Category.name)).all()
    items = db.session.execute(select(Item.id, Item.name, Item.category_id)).all()
    specifications = db.session.execute(
        select(Specification.id, Specification.label, Specification.item_id)
    ).all()
    matched_category = _match_catalog_name(
        query, [(row.id, row.name) for row in categories]
    )
    matched_item = _match_catalog_name(query, [(row.id, row.name) for row in items])
    matched_specification = None
    if matched_item:
        matched_specification = _match_catalog_name(
            query,
            [
                (row.id, row.label)
                for row in specifications
                if row.item_id == matched_item[0]
            ],
        )

    keyword_match = re.search(
        r"\bdetails?\s+(?:mention|mentions|contain|contains|say|says)\s+(.+)|\bmention\s+(.+)",
        query,
    )
    keyword = (
        next((value for value in keyword_match.groups() if value), None)
        if keyword_match
        else None
    )
    if keyword:
        keyword = re.sub(r"[?.!,;:]+$", "", keyword).strip()

    direction = (
        "in"
        if re.search(r"\b(received|receive|incoming|inbound)\b", query)
        else "out"
        if re.search(
            r"\b(went out|go out|outgoing|outbound|issued|dispatch|dispatched|sold)\b|\bout\b",
            query,
        )
        else None
    )
    wants_stock = bool(re.search(r"\b(stock|balance|remaining|left)\b", query))
    try:
        date_from, date_to = _date_range(query)
    except ValueError as exc:
        return validation_error([{"field": "question", "message": str(exc)}])

    criteria = [
        InventoryRecord.location_id.in_(user_location_ids(user.id)),
        InventoryRecord.deleted_at.is_(None),
    ]
    if matched_item:
        criteria.append(Item.id == matched_item[0])
    if matched_specification:
        criteria.append(Specification.id == matched_specification[0])
    if matched_category:
        criteria.append(Category.id == matched_category[0])
    if keyword:
        criteria.append(InventoryRecord.details.contains(keyword, autoescape=True))
    if direction == "in":
        criteria.append(InventoryRecord.qty_in > 0)
    elif direction == "out":
        criteria.append(InventoryRecord.qty_out > 0)
    if date_from:
        criteria.append(InventoryRecord.record_date >= date_from)
    if date_to:
        criteria.append(InventoryRecord.record_date <= date_to)

    has_structured_filter = any(
        (matched_item, matched_category, keyword, direction, date_from, date_to)
    )
    if not has_structured_filter:
        terms = [
            term.strip(".,?!:;()[]{}\"'")
            for term in query.split()
            if len(term.strip(".,?!:;()[]{}\"'")) > 2
            and term.strip(".,?!:;()[]{}\"'") not in _STOP_WORDS
        ]
        if terms:
            criteria.append(
                or_(
                    *(
                        or_(
                            Category.name.contains(term, autoescape=True),
                            Item.name.contains(term, autoescape=True),
                            Specification.label.contains(term, autoescape=True),
                            InventoryRecord.details.contains(term, autoescape=True),
                        )
                        for term in terms
                    )
                )
            )
        else:
            criteria.append(InventoryRecord.id == -1)

    statement = (
        select(InventoryRecord, Category.name, Item.name, Specification.label)
        .join(InventoryRecord.specification)
        .join(Specification.item)
        .join(Item.category)
        .where(*criteria)
    )
    if wants_stock and matched_item:
        stock_statement = (
            select(
                func.coalesce(func.sum(InventoryRecord.qty_in), 0)
                - func.coalesce(func.sum(InventoryRecord.qty_out), 0)
            )
            .select_from(InventoryRecord)
            .join(InventoryRecord.specification)
            .join(Specification.item)
            .join(Item.category)
            .where(*criteria)
        )
        balance = Decimal(str(db.session.scalar(stock_statement) or 0))
        specification_label = (
            matched_specification[1] if matched_specification else None
        )
        answer = (
            f"Recorded stock for {matched_item[1]} ({specification_label}) is "
            f"{_format_quantity(balance)}."
            if specification_label
            else f"Recorded stock for {matched_item[1]} is "
            f"{_format_quantity(balance)} across its specifications."
        )
    else:
        answer = ""

    total_matches = (
        db.session.scalar(
            select(func.count()).select_from(statement.order_by(None).subquery())
        )
        or 0
    )
    rows = db.session.execute(
        statement.order_by(
            InventoryRecord.record_date.desc(), InventoryRecord.id.desc()
        ).limit(5)
    ).all()
    records = [
        {
            "id": record.id,
            "date": record.record_date.isoformat(),
            "category": category_name,
            "item": item_name,
            "size": specification_label,
            "quantityIn": json_number(record.qty_in),
            "quantityOut": json_number(record.qty_out),
            "details": record.details or "",
        }
        for record, category_name, item_name, specification_label in rows
    ]
    if not answer:
        answer = (
            f"I found {total_matches} matching inventory record"
            f"{'' if total_matches == 1 else 's'}."
            if total_matches <= 5
            else f"I found {total_matches} matching inventory records. Showing the first 5."
        )
    search_query = keyword or (matched_item[1] if matched_item else None)
    if not search_query:
        search_query = matched_category[1] if matched_category else question

    db.session.add(
        AssistantQuery(
            user_id=user.id,
            question=question,
            tools_called={
                "item": matched_item[1] if matched_item else None,
                "category": matched_category[1] if matched_category else None,
                "specification": matched_specification[1]
                if matched_specification
                else None,
                "direction": direction,
                "from": date_from.isoformat() if date_from else None,
                "to": date_to.isoformat() if date_to else None,
                "stock": wants_stock,
            },
            result_count=total_matches,
        )
    )
    db.session.commit()
    return jsonify(
        {
            "data": {
                "answer": answer,
                "records": records,
                "totalMatches": total_matches,
                "searchQuery": search_query,
            }
        }
    )
