"""Configure requested products for bale inventory.

Revision ID: f8b2c4d6e0a1
Revises: d71e4a9c2b60
Create Date: 2026-11-12 18:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "f8b2c4d6e0a1"
down_revision = "d71e4a9c2b60"
branch_labels = None
depends_on = None


BALE_PRODUCTS = (
    ("Pillows", "Pillow", 10),
    ("Duvets", "Duvet N", 5),
    ("Duvets", "Duvet S", 20),
    ("Duvets", "Woolen Duvet", 20),
    ("Blankets", "Goldstar Blanket (BF)", 20),
    ("Bedcovers", "Bedcover 60x80", 50),
    ("Pillow Cases", "White Pillow Case", 100),
)


def upgrade() -> None:
    for category, name, pieces_per_bale in BALE_PRODUCTS:
        op.execute(
            sa.text(
                """
                UPDATE items
                SET inventory_unit = 'BALE', pieces_per_bale = :pieces_per_bale
                WHERE id IN (
                    SELECT i.id
                    FROM items AS i
                    JOIN categories AS c ON c.id = i.category_id
                    WHERE lower(trim(c.name)) = lower(:category)
                      AND lower(trim(i.name)) = lower(:name)
                )
                """
            ).bindparams(
                category=category,
                name=name,
                pieces_per_bale=pieces_per_bale,
            )
        )


def downgrade() -> None:
    for category, name in (
        ("Pillows", "Pillow"),
        ("Blankets", "Goldstar Blanket (BF)"),
    ):
        op.execute(
            sa.text(
                """
                UPDATE items
                SET inventory_unit = 'PCS', pieces_per_bale = NULL
                WHERE id IN (
                    SELECT i.id
                    FROM items AS i
                    JOIN categories AS c ON c.id = i.category_id
                    WHERE lower(trim(c.name)) = lower(:category)
                      AND lower(trim(i.name)) = lower(:name)
                )
                """
            ).bindparams(category=category, name=name)
        )