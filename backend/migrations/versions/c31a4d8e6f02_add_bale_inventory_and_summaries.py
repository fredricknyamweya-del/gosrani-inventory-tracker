"""Add bale configuration and normalized inventory quantities.

Revision ID: c31a4d8e6f02
Revises: 2abfe71c8930
Create Date: 2026-11-12 15:30:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "c31a4d8e6f02"
down_revision = "2abfe71c8930"
branch_labels = None
depends_on = None


BALE_PRODUCTS = (
    ("Duvets", "Duvet N", 5),
    ("Duvets", "Duvet S", 20),
    ("Duvets", "Woolen Duvet", 20),
    ("Blankets", "Goldstar Blanket (BF)", 20),
    ("Bedcovers", "Bedcover 60x80", 50),
    ("Pillow Cases", "White Pillow Case", 100),
)


def _create_stock_view() -> None:
    op.execute(
        """
        CREATE VIEW v_stock AS
        SELECT location_id,
               specification_id,
               COALESCE(SUM(qty_in_normalized), 0)
                 - COALESCE(SUM(qty_out_normalized), 0) AS stock
        FROM inventory_records
        WHERE deleted_at IS NULL
        GROUP BY location_id, specification_id
        """
    )


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column(
            "inventory_unit",
            sa.String(length=8),
            server_default="PCS",
            nullable=False,
        ),
    )
    op.add_column(
        "items", sa.Column("pieces_per_bale", sa.Integer(), nullable=True)
    )
    with op.batch_alter_table("items") as batch_op:
        batch_op.create_check_constraint(
            "item_bale_conversion_valid",
            "(inventory_unit = 'BALE' AND pieces_per_bale IS NOT NULL AND pieces_per_bale > 0) "
            "OR (inventory_unit != 'BALE' AND pieces_per_bale IS NULL)",
        )
    op.execute(
        sa.text(
            "UPDATE items SET inventory_unit = 'KG' WHERE unit = 'KG'"
        )
    )

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

    op.add_column(
        "inventory_records",
        sa.Column(
            "pieces_per_unit",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
    )
    op.add_column(
        "inventory_records",
        sa.Column("qty_in_normalized", sa.Numeric(15, 3), nullable=True),
    )
    op.add_column(
        "inventory_records",
        sa.Column("qty_out_normalized", sa.Numeric(15, 3), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE inventory_records SET "
            "qty_in_normalized = qty_in, qty_out_normalized = qty_out"
        )
    )

    op.execute("DROP VIEW v_stock")
    _create_stock_view()


def downgrade() -> None:
    op.execute("DROP VIEW v_stock")
    op.execute(
        """
        CREATE VIEW v_stock AS
        SELECT location_id,
               specification_id,
               COALESCE(SUM(qty_in), 0) - COALESCE(SUM(qty_out), 0) AS stock
        FROM inventory_records
        WHERE deleted_at IS NULL
        GROUP BY location_id, specification_id
        """
    )
    op.drop_column("inventory_records", "qty_out_normalized")
    op.drop_column("inventory_records", "qty_in_normalized")
    op.drop_column("inventory_records", "pieces_per_unit")
    with op.batch_alter_table("items") as batch_op:
        batch_op.drop_constraint("item_bale_conversion_valid", type_="check")
    op.drop_column("items", "pieces_per_bale")
    op.drop_column("items", "inventory_unit")
