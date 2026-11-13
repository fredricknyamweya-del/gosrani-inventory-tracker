"""Add strict item entry units and record bale conversions.

Revision ID: 7f4e3a9c2b10
Revises: f8b2c4d6e0a1
Create Date: 2026-11-13 12:50:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "7f4e3a9c2b10"
down_revision = "f8b2c4d6e0a1"
branch_labels = None
depends_on = None


def _create_stock_view() -> None:
    op.execute(
        """
        CREATE VIEW v_stock AS
        SELECT records.location_id,
               records.specification_id,
               SUM(records.qty_in_base) - SUM(records.qty_out_base) AS stock,
               CASE WHEN items.unit = 'PCS'
                    THEN SUM(records.qty_in_base) - SUM(records.qty_out_base)
                    ELSE NULL
               END AS stock_pieces,
               CASE WHEN items.entry_unit = 'BALE'
                         AND SUM(
                             CASE
                                 WHEN records.effective_pieces_per_bale IS NULL
                                      AND (records.qty_in_base <> 0 OR records.qty_out_base <> 0)
                                 THEN 1
                                 ELSE 0
                             END
                         ) = 0
                    THEN SUM(
                        1.0 * (records.qty_in_base - records.qty_out_base)
                        / records.effective_pieces_per_bale
                    )
                    ELSE NULL
               END AS stock_bales
        FROM (
            SELECT inventory_records.location_id,
                   inventory_records.specification_id,
                   COALESCE(inventory_records.qty_in_normalized, inventory_records.qty_in, 0)
                     AS qty_in_base,
                   COALESCE(inventory_records.qty_out_normalized, inventory_records.qty_out, 0)
                     AS qty_out_base,
                   COALESCE(
                       inventory_records.pieces_per_bale,
                       specifications.pack_size,
                       NULLIF(inventory_records.pieces_per_unit, 1)
                   ) AS effective_pieces_per_bale
            FROM inventory_records
            JOIN specifications
              ON specifications.id = inventory_records.specification_id
            WHERE inventory_records.deleted_at IS NULL
        ) AS records
        JOIN specifications
          ON specifications.id = records.specification_id
        JOIN items
          ON items.id = specifications.item_id
        GROUP BY records.location_id,
                 records.specification_id,
                 items.unit,
                 items.entry_unit
        """
    )


def _create_legacy_stock_view() -> None:
    op.execute(
        """
        CREATE VIEW v_stock AS
        SELECT location_id,
               specification_id,
               COALESCE(SUM(COALESCE(qty_in_normalized, qty_in)), 0)
                 - COALESCE(SUM(COALESCE(qty_out_normalized, qty_out)), 0) AS stock
        FROM inventory_records
        WHERE deleted_at IS NULL
        GROUP BY location_id, specification_id
        """
    )


def upgrade() -> None:
    op.execute("DROP VIEW v_stock")
    if op.get_bind().dialect.name == "sqlite":
        op.execute(
            """
            ALTER TABLE items
            ADD COLUMN entry_unit VARCHAR(4) NOT NULL DEFAULT 'PCS'
            CONSTRAINT items_entry_unit_valid
            CHECK (entry_unit IN ('PCS', 'BALE', 'KG'))
            """
        )
        op.execute(
            """
            ALTER TABLE inventory_records
            ADD COLUMN pieces_per_bale INTEGER
            CONSTRAINT pieces_per_bale_positive
            CHECK (pieces_per_bale IS NULL OR pieces_per_bale > 0)
            """
        )
    else:
        op.add_column(
            "items",
            sa.Column(
                "entry_unit",
                sa.Enum(
                    "PCS",
                    "BALE",
                    "KG",
                    name="item_entry_unit",
                    native_enum=False,
                    create_constraint=False,
                ),
                server_default="PCS",
                nullable=False,
            )
        )
        op.create_check_constraint(
            "items_entry_unit_valid",
            "items",
            "entry_unit IN ('PCS', 'BALE', 'KG')",
        )
        op.add_column(
            "inventory_records",
            sa.Column("pieces_per_bale", sa.Integer(), nullable=True),
        )
        op.create_check_constraint(
            "pieces_per_bale_positive",
            "inventory_records",
            "pieces_per_bale IS NULL OR pieces_per_bale > 0",
        )

    op.execute(
        """
        UPDATE items
        SET entry_unit = 'BALE'
        WHERE EXISTS (
            SELECT 1
            FROM specifications
            WHERE specifications.item_id = items.id
              AND specifications.pack_size IS NOT NULL
        )
        """
    )
    _create_stock_view()


def downgrade() -> None:
    op.execute("DROP VIEW v_stock")
    if op.get_bind().dialect.name == "sqlite":
        op.execute("ALTER TABLE inventory_records DROP COLUMN pieces_per_bale")
        op.execute("ALTER TABLE items DROP COLUMN entry_unit")
    else:
        op.drop_constraint(
            "pieces_per_bale_positive",
            "inventory_records",
            type_="check",
        )
        op.drop_column("inventory_records", "pieces_per_bale")
        op.drop_constraint("items_entry_unit_valid", "items", type_="check")
        op.drop_column("items", "entry_unit")
    _create_legacy_stock_view()
