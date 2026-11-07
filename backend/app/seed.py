"""Seed the initial administrator, location, and starter catalog."""

import os
import re
import secrets

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


def seed_database(
    *, user_passwords: list[tuple[str, str]] | None = None
) -> tuple[dict[str, int], list[tuple[str, str]]]:
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
    if len(password) < 6:
        raise click.ClickException(
            "SEED_ADMIN_PASSWORD must contain at least 6 characters."
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

    normalized_user_passwords: list[tuple[str, str]] = []
    user_emails: set[str] = set()
    for user_email, user_password in user_passwords or []:
        normalized_email = user_email.strip().lower()
        if not EMAIL_PATTERN.fullmatch(normalized_email):
            raise click.ClickException(
                f"Set a valid email address for each --user-email value; "
                f"{user_email!r} is invalid."
            )
        if len(normalized_email) > 254:
            raise click.ClickException(
                f"User email {normalized_email!r} must be no more than 254 characters."
            )
        if normalized_email == email or normalized_email in user_emails:
            raise click.ClickException(
                "The Admin and seeded User accounts must have unique email addresses."
            )
        if len(user_password) < 6:
            raise click.ClickException(
                "Generated User passwords must contain at least 6 characters."
            )
        user_emails.add(normalized_email)
        normalized_user_passwords.append((normalized_email, user_password))

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

        users_added = 0
        user_location_links_added = 0
        created_user_credentials = []
        for index, (user_email, user_password) in enumerate(
            normalized_user_passwords, start=1
        ):
            seeded_user = _find_ci(User, "email", user_email)
            if seeded_user is not None:
                if (
                    seeded_user.role != UserRole.USER
                    or seeded_user.status != UserStatus.ACTIVE
                ):
                    raise click.ClickException(
                        f"Seed email {user_email!r} belongs to an account that is "
                        "not an active User; no account was changed."
                    )
            else:
                local_name = re.sub(
                    r"[^A-Za-z0-9]+", " ", user_email.partition("@")[0]
                ).strip()
                seeded_user = User(
                    name=(local_name.title() or f"Inventory User {index}")[:120],
                    email=user_email,
                    password_hash=generate_password_hash(user_password),
                    role=UserRole.USER,
                    status=UserStatus.ACTIVE,
                )
                db.session.add(seeded_user)
                db.session.flush()
                users_added += 1
                created_user_credentials.append((user_email, user_password))

            user_link = db.session.get(UserLocation, (seeded_user.id, location.id))
            if user_link is None:
                db.session.add(
                    UserLocation(user_id=seeded_user.id, location_id=location.id)
                )
                user_location_links_added += 1

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

    return (
        {
            "admins_added": int(user_added),
            "users_added": users_added,
            "locations_added": int(location_added),
            "categories_added": categories_added,
            "items_added": items_added,
            "specifications_added": specifications_added,
            "admin_location_links_added": int(link_exists is None),
            "user_location_links_added": user_location_links_added,
        },
        created_user_credentials,
    )


@click.command("seed")
@with_appcontext
@click.option(
    "--user-email",
    "user_emails",
    multiple=True,
    help="Create an active User account for this email (repeatable).",
)
def seed_command(user_emails: tuple[str, ...]) -> None:
    """Seed initial accounts, location, and starter catalog records."""
    user_passwords = [
        (email, secrets.token_urlsafe(24)) for email in user_emails
    ]
    counts, created_user_credentials = seed_database(user_passwords=user_passwords)
    click.echo(
        "Seed complete: "
        + ", ".join(f"{key.replace('_', ' ')}={value}" for key, value in counts.items())
    )
    for email, password in created_user_credentials:
        click.echo(f"New User login: {email} / {password}")
