"""Read-only stock report for active catalog specifications."""

import csv
import io
import os
from decimal import Decimal

import click
from flask.cli import with_appcontext
from sqlalchemy import and_, func, select

from app.extensions import db
from app.models import (
    Category,
    InventoryUnit,
    Item,
    Location,
    Specification,
    v_stock,
)
from app.units import format_quantity_display

EXPECTED_PACK_SPECS = (
    ("Duvets", ("Duvet N",), "4x6", 5),
    ("Duvets", ("Duvet N",), "5x6", 5),
    ("Duvets", ("Duvet N",), "6x6", 5),
    ("Duvets", ("Duvet S",), "4x6", 20),
    ("Duvets", ("Woolen Duvet",), "5x6", 20),
    ("Duvets", ("Woolen Duvet",), "4x6", 20),
    ("Pillows", ("Pillow",), "600g", 10),
    ("Pillows", ("Pillow",), "1 Kg", 10),
    ("Pillows", ("Pillow",), "Light", 10),
    (
        "Blankets",
        ("Goldstar Blanket (BF)", "Goldstar Blanket", "Bf Goldstar", "BF Goldstar"),
        "54x80 2ST",
        20,
    ),
    ("Bedcovers", ("Bedcover 60x80",), "Blue", 50),
    ("Bedcovers", ("Bedcover 60x80",), "Pink", 50),
    ("Bedcovers", ("Bedcover 60x80",), "Green", 50),
    ("Pillow Cases", ("White Pillow Case",), "100 pcs", 100),
)


def _catalog_key(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _format_base_quantity(value: Decimal) -> str:
    formatted = format(Decimal(value), ",f")
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted or "0"


def _missing_pack_warnings(rows: list[dict[str, object]]) -> list[str]:
    expected = {
        (
            _catalog_key(category),
            tuple(_catalog_key(alias) for alias in aliases),
            _catalog_key(size),
        ): pack_size
        for category, aliases, size, pack_size in EXPECTED_PACK_SPECS
    }
    warnings = []
    matched_expected = set()

    for row in rows:
        category = _catalog_key(str(row["category"]))
        item = _catalog_key(str(row["item"]))
        size = _catalog_key(str(row["size"]))
        expected_key = next(
            (
                key
                for key in expected
                if key[0] == category and item in key[1] and key[2] == size
            ),
            None,
        )
        if expected_key is not None:
            matched_expected.add(expected_key)
            expected_pack_size = expected[expected_key]
            actual_pack_size = row["pack_size"]
            if actual_pack_size != expected_pack_size:
                found = actual_pack_size if actual_pack_size is not None else "none"
                warnings.append(
                    f"{row['category']} / {row['item']} / {row['size']}: "
                    f"expected pack size {expected_pack_size}, found {found}."
                )
        elif (
            row["inventory_unit"] == InventoryUnit.BALE
            and row["pack_size"] is None
        ):
            warnings.append(
                f"{row['category']} / {row['item']} / {row['size']}: "
                "configured as BALE but has no specification pack size."
            )

    for key, expected_pack_size in expected.items():
        if key not in matched_expected:
            category, item_aliases, size = key
            warnings.append(
                f"Expected baled specification {category} / "
                f"{item_aliases[0]} / {size} was not found "
                f"(expected pack size {expected_pack_size})."
            )

    return warnings


@click.command("stock-report")
@click.option(
    "--csv",
    "csv_output",
    is_flag=True,
    help="Write the report as CSV.",
)
@with_appcontext
def stock_report_command(csv_output: bool) -> None:
    """Print active-specification stock at the configured default location."""
    location_code = os.getenv("DEFAULT_LOCATION_CODE", "ELD").strip().upper() or "ELD"
    location = db.session.scalar(
        select(Location).where(
            Location.code == location_code,
            Location.active.is_(True),
        )
    )
    if location is None:
        raise click.ClickException(
            f"Active default location {location_code!r} was not found."
        )

    statement = (
        select(
            Category.name.label("category"),
            Item.name.label("item"),
            Specification.label.label("size"),
            Specification.pack_size.label("pack_size"),
            Item.unit.label("unit"),
            Item.inventory_unit.label("inventory_unit"),
            func.coalesce(v_stock.c.stock, 0).label("stock"),
        )
        .select_from(Specification)
        .join(Item, Item.id == Specification.item_id)
        .join(Category, Category.id == Item.category_id)
        .outerjoin(
            v_stock,
            and_(
                v_stock.c.specification_id == Specification.id,
                v_stock.c.location_id == location.id,
            ),
        )
        .where(
            Specification.active.is_(True),
            Item.active.is_(True),
            Category.active.is_(True),
        )
        .order_by(Category.sort_order, Category.name, Item.name, Specification.label)
    )
    rows = [
        {
            "category": result.category,
            "item": result.item,
            "size": result.size,
            "pack_size": result.pack_size,
            "unit": result.unit,
            "inventory_unit": result.inventory_unit,
            "stock": Decimal(result.stock),
        }
        for result in db.session.execute(statement)
    ]

    headers = [
        "category",
        "item",
        "size",
        "pack_size",
        "stock_base_units",
        "display",
    ]
    report_rows = []
    for row in rows:
        display, secondary = format_quantity_display(
            row["stock"], row["unit"], row["pack_size"]
        )
        report_rows.append(
            [
                row["category"],
                row["item"],
                row["size"],
                str(row["pack_size"]) if row["pack_size"] is not None else "",
                _format_base_quantity(row["stock"]),
                " ".join(part for part in (display, secondary) if part),
            ]
        )

    warnings = _missing_pack_warnings(rows)
    if csv_output:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(report_rows)
        click.echo(output.getvalue(), nl=False)
        for warning in warnings:
            click.echo(f"WARNING: {warning}", err=True)
        return

    widths = [
        max(len(header), *(len(row[index]) for row in report_rows))
        for index, header in enumerate(headers)
    ]
    click.echo("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    click.echo("  ".join("-" * width for width in widths))
    for row in report_rows:
        click.echo("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))
    click.echo(f"\nLocation: {location.name} ({location.code})")
    if warnings:
        click.echo("\nPack-size warnings:")
        for warning in warnings:
            click.echo(f"WARNING: {warning}")
