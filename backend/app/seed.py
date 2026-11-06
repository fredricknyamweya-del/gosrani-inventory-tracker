"""Seed the initial administrator, location, and starter catalog."""

import os
import re

import click
from flask.cli import with_appcontext
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import (
    Category,
    Item,
    Location,
    Specification,
    StockUnit,
    User,
    UserLocation,
    UserRole,
    UserStatus,
)

CATALOG: tuple[tuple[str, tuple[tuple[str, StockUnit, tuple[tuple[str, int | None], ...]], ...]], ...] = (
    (
        "Duvets",
        (
            ("Duvet N", StockUnit.PCS, (("4x6", 5), ("5x6", 5), ("6x6", 5))),
            ("Duvet S", StockUnit.PCS, (("4x6", 20),)),
            ("Woolen Duvet", StockUnit.PCS, (("5x6", 20), ("4x6", 20))),
            ("Duvet Bags", StockUnit.PCS, (("Standard", None),)),
        ),
    ),
    ("Pillows", (("Pillow", StockUnit.PCS, (("600g", 10), ("1 Kg", 10), ("Light", 10))),)),
    (
        "Mattresses",
        (
            ("HDF", StockUnit.PCS, (("36x4", None), ("48x4", None), ("48x6", None))),
            (
                "SHDF",
                StockUnit.PCS,
                (
                    ("48x8", None),
                    ("30x5", None),
                    ("30x6", None),
                    ("42x8", None),
                    ("54x8", None),
                    ("60x8", None),
                    ("72x8", None),
                    ("72x10", None),
                ),
            ),
            (
                "SHDQ",
                StockUnit.PCS,
                (("60x8", None), ("72x8", None), ("48x8", None)),
            ),
        ),
    ),
    ("Cushions", (("SHDQ Cushion", StockUnit.PCS, (('4"', None),)),)),
    ("Sofa Sets", ()),
    (
        "Blankets",
        (("Goldstar Blanket (BF)", StockUnit.PCS, (("54x80 2ST", 20),)),),
    ),
    (
        "Bedcovers",
        (
            (
                "Bedcover 60x80",
                StockUnit.PCS,
                (("Blue", 50), ("Pink", 50), ("Green", 50)),
            ),
        ),
    ),
    (
        "Pillow Cases",
        (
            ("Pillow Kiss Case", StockUnit.PCS, (("Standard", None),)),
            ("White Pillow Case", StockUnit.PCS, (("100 pcs", 100),)),
        ),
    ),
    ("Raw Materials", (("Fibre", StockUnit.KG, (("Standard", None),)),)),
    (
        "Packaging",
        (
            ("Pillow Individual Packaging Bags", StockUnit.PCS, (("Standard", None),)),
            (
                "Pillow (10 pc) Packaging Polythene Bags",
                StockUnit.PCS,
                (("Standard", None),),
            ),
        ),
    ),
)
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _find_ci(model, field: str, value: str):
    column = getattr(model, field)
    return db.session.scalar(
        select(model).where(func.lower(func.trim(column)) == value.strip().lower())
    )


def _seed_catalog() -> tuple[int, int, int]:
    categories_added = 0
    items_added = 0
    specifications_added = 0

    for category_name, items in CATALOG:
        category = _find_ci(Category, "name", category_name)
        if category is None:
            category = Category(name=category_name)
            db.session.add(category)
            db.session.flush()
            categories_added += 1

        for item_name, unit, specifications in items:
            item = db.session.scalar(
                select(Item).where(
                    Item.category_id == category.id,
                    func.lower(func.trim(Item.name)) == item_name.strip().lower(),
                )
            )
            if item is None:
                item = Item(category_id=category.id, name=item_name, unit=unit)
                db.session.add(item)
                db.session.flush()
                items_added += 1
            elif item.unit != unit:
                raise click.ClickException(
                    f"Existing catalog item {item_name!r} has a different stock unit."
                )

            for label, pack_size in specifications:
                spec = db.session.scalar(
                    select(Specification).where(
                        Specification.item_id == item.id,
                        func.lower(func.trim(Specification.label))
                        == label.strip().lower(),
                    )
                )
                if spec is None:
                    db.session.add(
                        Specification(
                            item_id=item.id,
                            label=label,
                            pack_size=pack_size,
                        )
                    )
                    specifications_added += 1
                elif spec.pack_size != pack_size:
                    raise click.ClickException(
                        f"Existing specification {label!r} for {item_name!r} "
                        "has a different pack size."
                    )

    return categories_added, items_added, specifications_added


def seed_database() -> dict[str, int]:
    """Create missing first-run data without changing existing credentials."""
    email = os.getenv("SEED_ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("SEED_ADMIN_PASSWORD", "")
    name = os.getenv("SEED_ADMIN_NAME", "System Administrator").strip()
    location_code = os.getenv("DEFAULT_LOCATION_CODE", "ELD").strip().upper()
    location_name = os.getenv("DEFAULT_LOCATION_NAME", "Eldoret Godown").strip()

    if not EMAIL_PATTERN.fullmatch(email):
        raise click.ClickException("Set a valid SEED_ADMIN_EMAIL before seeding.")
    if len(email) > 254:
        raise click.ClickException("SEED_ADMIN_EMAIL must be no more than 254 characters.")
    if len(password) < 12:
        raise click.ClickException(
            "SEED_ADMIN_PASSWORD must contain at least 12 characters."
        )
    if not name or len(name) > 120:
        raise click.ClickException("SEED_ADMIN_NAME must be 1 to 120 characters.")
    if not location_code or len(location_code) > 10:
        raise click.ClickException(
            "DEFAULT_LOCATION_CODE must be 1 to 10 characters."
        )
    if not location_name or len(location_name) > 100:
        raise click.ClickException(
            "DEFAULT_LOCATION_NAME must be 1 to 100 characters."
        )

    try:
        user = _find_ci(User, "email", email)
        if user is not None and (
            user.role != UserRole.ADMIN or user.status != UserStatus.ACTIVE
        ):
            raise click.ClickException(
                "The configured seed email belongs to an account that is not an "
                "active Admin; no account was changed."
            )
        user_added = user is None
        if user is None:
            user = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
            )
            db.session.add(user)
            db.session.flush()

        location = db.session.scalar(
            select(Location).where(Location.code == location_code)
        )
        if location is None:
            location = Location(code=location_code, name=location_name)
            db.session.add(location)
            db.session.flush()
            location_added = True
        else:
            location_added = False

        link_exists = db.session.get(UserLocation, (user.id, location.id))
        if link_exists is None:
            db.session.add(UserLocation(user_id=user.id, location_id=location.id))

        categories_added, items_added, specifications_added = _seed_catalog()
        db.session.commit()
    except click.ClickException:
        db.session.rollback()
        raise
    except SQLAlchemyError:
        db.session.rollback()
        raise click.ClickException(
            "Database seeding failed and was rolled back. Confirm the schema is "
            "migrated and database constraints are satisfied."
        ) from None

    return {
        "admins_added": int(user_added),
        "locations_added": int(location_added),
        "categories_added": categories_added,
        "items_added": items_added,
        "specifications_added": specifications_added,
        "admin_location_links_added": int(link_exists is None),
    }


@click.command("seed")
@with_appcontext
def seed_command() -> None:
    """Seed initial Admin, location, and starter catalog records."""
    counts = seed_database()
    click.echo(
        "Seed complete: "
        + ", ".join(f"{key.replace('_', ' ')}={value}" for key, value in counts.items())
    )
