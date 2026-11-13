"""Formatting helpers for quantities stored in their base unit."""

from decimal import Decimal

from app.models import EnteredUnit, StockUnit


def _format_number(value: Decimal) -> str:
    return f"{value:,.3f}".rstrip("0").rstrip(".")


def effective_pieces_per_bale(
    entered_unit: EnteredUnit,
    pieces_per_bale: int | None,
    pack_size: int | None,
    legacy_pieces_per_unit: int | None = None,
) -> int | None:
    """Resolve the conversion saved on a record or available from its catalog."""
    if entered_unit != EnteredUnit.BALE:
        return None
    return pieces_per_bale or pack_size or (
        legacy_pieces_per_unit
        if legacy_pieces_per_unit is not None and legacy_pieces_per_unit > 1
        else None
    )


def format_quantity_display(
    quantity: Decimal,
    unit: StockUnit,
    pack_size: int | None,
    *,
    entry_unit: EnteredUnit | None = None,
    entered_unit: EnteredUnit | None = None,
    pieces_per_bale: int | None = None,
    bales: Decimal | None = None,
) -> tuple[str, str | None]:
    """Format base-unit stock or a transaction using its stored entry unit."""
    quantity = Decimal(quantity)
    if not quantity.is_finite():
        raise ValueError("Stock quantities must be finite.")
    if pack_size is not None and pack_size <= 0:
        raise ValueError("Specification pack sizes must be positive.")
    if pieces_per_bale is not None and pieces_per_bale <= 0:
        raise ValueError("Pieces per bale must be positive.")
    if quantity == 0:
        if entry_unit is None and entered_unit is None and bales is None:
            return "0", None
        if unit == StockUnit.KG:
            return "0 kg", None
        if entered_unit == EnteredUnit.BALE:
            if pieces_per_bale is None:
                return "0 pcs", None
            return f"0 bales x {pieces_per_bale} pcs = 0 pcs", None
        if bales is not None:
            return "0 bales (0 pcs)", None
        if entry_unit == EnteredUnit.BALE:
            return "0 bales (0 pcs)", None
        return "0 pcs", None
    if unit == StockUnit.KG:
        return f"{_format_number(quantity)} kg", None

    if entered_unit == EnteredUnit.BALE:
        if pieces_per_bale is None:
            return f"{_format_number(quantity)} pcs", None
        bale_quantity = quantity / Decimal(pieces_per_bale)
        bale_label = "bale" if abs(bale_quantity) == 1 else "bales"
        piece_label = "pc" if abs(quantity) == 1 else "pcs"
        return (
            (
                f"{_format_number(bale_quantity)} {bale_label} x "
                f"{pieces_per_bale} pcs = {_format_number(quantity)} {piece_label}"
            ),
            None,
        )

    if bales is not None:
        bale_quantity = Decimal(bales)
        bale_label = "bale" if abs(bale_quantity) == 1 else "bales"
        piece_label = "pc" if abs(quantity) == 1 else "pcs"
        return (
            (
                f"{_format_number(bale_quantity)} {bale_label} "
                f"({_format_number(quantity)} {piece_label})"
            ),
            None,
        )

    if entry_unit == EnteredUnit.BALE:
        return f"{_format_number(quantity)} pcs", None

    if entry_unit == EnteredUnit.PCS or entered_unit == EnteredUnit.PCS:
        label = "pc" if abs(quantity) == 1 else "pcs"
        return f"{_format_number(quantity)} {label}", None

    # Keep the legacy specification-pack display for older callers without
    # item or record unit context. Application surfaces pass explicit units.
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
