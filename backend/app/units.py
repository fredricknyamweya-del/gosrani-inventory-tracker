"""Formatting helpers for quantities stored in their base unit."""

from decimal import Decimal

from app.models import StockUnit


def _format_number(value: Decimal) -> str:
    return f"{value:,.3f}".rstrip("0").rstrip(".")


def format_quantity_display(
    quantity: Decimal,
    unit: StockUnit,
    pack_size: int | None,
) -> tuple[str, str | None]:
    """Return a primary stock label and optional base-unit secondary label."""
    quantity = Decimal(quantity)
    if not quantity.is_finite():
        raise ValueError("Stock quantities must be finite.")
    if pack_size is not None and pack_size <= 0:
        raise ValueError("Specification pack sizes must be positive.")
    if quantity == 0:
        return "0", None
    if unit == StockUnit.KG:
        return f"{_format_number(quantity)} kg", None

    absolute_quantity = abs(quantity)
    sign = "-" if quantity < 0 else ""
    if pack_size is None:
        label = "pc" if absolute_quantity == 1 else "pcs"
        return f"{_format_number(quantity)} {label}", None

    bale_count = int(absolute_quantity // Decimal(pack_size))
    remainder = absolute_quantity - Decimal(bale_count * pack_size)
    parts = []
    if bale_count:
        bale_label = "bale" if bale_count == 1 else "bales"
        parts.append(f"{bale_count:,} {bale_label}")
    if remainder:
        piece_label = "pc" if remainder == 1 else "pcs"
        parts.append(f"{_format_number(remainder)} {piece_label}")
    if not parts:
        return "0", None

    display = sign + " + ".join(parts)
    if bale_count:
        piece_label = "pc" if absolute_quantity == 1 else "pcs"
        return display, f"({_format_number(quantity)} {piece_label})"
    return display, None
