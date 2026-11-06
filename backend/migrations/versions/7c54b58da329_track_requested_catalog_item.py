"""Track the item targeted by a specification request.

Revision ID: 7c54b58da329
Revises: 82aa092d9e0e
Create Date: 2026-11-06 16:30:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "7c54b58da329"
down_revision = "82aa092d9e0e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("item_requests") as batch_op:
        batch_op.add_column(sa.Column(
            "item_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=True,
        ))
        batch_op.create_foreign_key(
            "fk_item_requests_item_id_items",
            "items",
            ["item_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("item_requests") as batch_op:
        batch_op.drop_constraint("fk_item_requests_item_id_items", type_="foreignkey")
        batch_op.drop_column("item_id")
