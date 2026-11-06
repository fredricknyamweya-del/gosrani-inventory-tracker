"""Align revoked token identifier length with the model.

Revision ID: 91f2d8a4c6b0
Revises: 7c54b58da329
Create Date: 2026-11-06 18:02:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "91f2d8a4c6b0"
down_revision = "7c54b58da329"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("revoked_tokens") as batch_op:
        batch_op.alter_column(
            "jti",
            existing_type=sa.String(length=64),
            type_=sa.String(length=36),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("revoked_tokens") as batch_op:
        batch_op.alter_column(
            "jti",
            existing_type=sa.String(length=36),
            type_=sa.String(length=64),
            existing_nullable=False,
        )
