"""Set Goldstar Blanket inventory to pieces.

Revision ID: d71e4a9c2b60
Revises: c31a4d8e6f02
Create Date: 2026-11-12 17:03:00
"""

from alembic import op
import sqlalchemy as sa

revision = "d71e4a9c2b60"
down_revision = "c31a4d8e6f02"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
        ).bindparams(category="Blankets", name="Goldstar Blanket (BF)")
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE items
            SET inventory_unit = 'BALE', pieces_per_bale = 20
            WHERE id IN (
                SELECT i.id
                FROM items AS i
                JOIN categories AS c ON c.id = i.category_id
                WHERE lower(trim(c.name)) = lower(:category)
                  AND lower(trim(i.name)) = lower(:name)
            )
            """
        ).bindparams(category="Blankets", name="Goldstar Blanket (BF)")
    )
