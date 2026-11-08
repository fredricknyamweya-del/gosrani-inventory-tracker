"""Add the person who handled an inventory movement.

Revision ID: b43d92f1a6c0
Revises: 2abfe71c8930
Create Date: 2026-11-08 22:06:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "b43d92f1a6c0"
down_revision = "2abfe71c8930"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "inventory_records",
        sa.Column("handled_by", sa.String(length=160), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("inventory_records", "handled_by")
