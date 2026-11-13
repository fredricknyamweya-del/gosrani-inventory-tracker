"""Apply the approved item entry-unit policy to a local catalog."""

import click
from flask.cli import with_appcontext
from sqlalchemy import func, select

from app.api_utils import audit
from app.extensions import db
from app.models import (
    AuditAction,
    AuditEntity,
    Category,
    EnteredUnit,
    Item,
    User,
    UserRole,
)

BALE_CATEGORIES = {"pillows", "duvets", "blankets"}
PCS_CATEGORIES = {"sofa sets", "mattresses", "cushions"}
BALE_ITEMS = {"woolen duvet", "plain school bedcovers - heavy", "white pillow case"}
PCS_ITEMS = {"duvet bags", "pillow kiss case"}


def _key(value: str) -> str:
    return value.strip().casefold()


def _policy_for(category_name: str, item_name: str) -> EnteredUnit | None:
    category_key = _key(category_name)
    item_key = _key(item_name)
    if item_key in BALE_ITEMS:
        return EnteredUnit.BALE
    if item_key in PCS_ITEMS:
        return EnteredUnit.PCS
    if category_key in BALE_CATEGORIES and item_key != "duvet bags":
        return EnteredUnit.BALE
    if category_key in PCS_CATEGORIES:
        return EnteredUnit.PCS
    return None


@click.command("apply-unit-policy")
@click.option(
    "--apply",
    "apply_changes",
    is_flag=True,
    help="Persist entry-unit changes and audit rows (default is a dry run).",
)
@with_appcontext
def apply_unit_policy_command(apply_changes: bool) -> None:
    """Preview or apply the explicit BALE/PCS item-name and category policy."""
    categories = {
        _key(category.name): category
        for category in db.session.scalars(select(Category)).all()
    }
    items = db.session.execute(
        select(Item, Category.name)
        .join(Category, Category.id == Item.category_id)
        .order_by(Category.name, Item.name)
    ).all()
    matched_categories = set()
    matched_items = set()
    planned_changes: list[tuple[Item, EnteredUnit]] = []

    for item, category_name in items:
        category_key = _key(category_name)
        item_key = _key(item.name)
        if category_key in BALE_CATEGORIES | PCS_CATEGORIES:
            matched_categories.add(category_key)
        if item_key in BALE_ITEMS | PCS_ITEMS:
            matched_items.add(item_key)
        target = _policy_for(category_name, item.name)
        if target is not None and item.entry_unit != target:
            planned_changes.append((item, target))

    click.echo("Applying unit policy." if apply_changes else "Unit policy dry run; no changes made.")
    if planned_changes:
        for item, target in planned_changes:
            category = categories.get(_key(item.category.name)) if item.category else None
            category_name = category.name if category else str(item.category_id)
            click.echo(
                f"{category_name} / {item.name}: "
                f"{item.entry_unit.value} -> {target.value}"
            )
    else:
        click.echo("No entry-unit changes are needed.")

    unmatched = [
        *(f"category: {name}" for name in sorted(BALE_CATEGORIES | PCS_CATEGORIES) if name not in matched_categories),
        *(f"item: {name}" for name in sorted(BALE_ITEMS | PCS_ITEMS) if name not in matched_items),
    ]
    for name in unmatched:
        click.echo(f"UNMATCHED {name}")

    if not apply_changes or not planned_changes:
        return

    actor = db.session.scalar(
        select(User)
        .where(User.role == UserRole.ADMIN)
        .order_by(User.is_primary_admin.desc(), User.id)
    )
    if actor is None:
        raise click.ClickException(
            "Applying the unit policy requires at least one administrator for audit records."
        )

    for item, target in planned_changes:
        previous = item.entry_unit.value
        item.entry_unit = target
        audit(
            AuditEntity.ITEM,
            item.id,
            AuditAction.UPDATE,
            actor.id,
            before={"entryUnit": previous},
            after={"entryUnit": target.value},
        )
    db.session.commit()
    click.echo(f"Updated {len(planned_changes)} item(s); audit records were written.")
