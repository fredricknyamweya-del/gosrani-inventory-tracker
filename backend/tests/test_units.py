"""Regression tests for base-unit stock display formatting."""

from decimal import Decimal

import pytest

from app.models import StockUnit
from app.units import format_quantity_display


@pytest.mark.parametrize(
    ("quantity", "unit", "pack_size", "expected"),
    [
        ("8300", StockUnit.PCS, 20, ("415 bales", "(8,300 pcs)")),
        ("8307", StockUnit.PCS, 20, ("415 bales + 7 pcs", "(8,307 pcs)")),
        ("20", StockUnit.PCS, 20, ("1 bale", "(20 pcs)")),
        ("1", StockUnit.PCS, 20, ("1 pc", None)),
        ("7", StockUnit.PCS, 20, ("7 pcs", None)),
        ("0", StockUnit.PCS, 20, ("0", None)),
        ("-8307", StockUnit.PCS, 20, ("-415 bales + 7 pcs", "(-8,307 pcs)")),
        ("2", StockUnit.PCS, None, ("2 pcs", None)),
        ("1", StockUnit.PCS, None, ("1 pc", None)),
        ("-2", StockUnit.PCS, None, ("-2 pcs", None)),
        ("22816", StockUnit.KG, None, ("22,816 kg", None)),
        ("22.8165", StockUnit.KG, None, ("22.817 kg", None)),
        ("0", StockUnit.KG, None, ("0", None)),
    ],
)
def test_format_quantity_display_golden_cases(
    quantity, unit, pack_size, expected
):
    assert format_quantity_display(Decimal(quantity), unit, pack_size) == expected


def test_format_quantity_display_rejects_invalid_pack_size():
    with pytest.raises(ValueError, match="positive"):
        format_quantity_display(Decimal("1"), StockUnit.PCS, 0)
