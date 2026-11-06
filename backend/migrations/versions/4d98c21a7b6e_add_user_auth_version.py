"""Add user authentication version for password-change session invalidation.

Revision ID: 4d98c21a7b6e
Revises: 91f2d8a4c6b0
Create Date: 2026-11-06 19:10:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "4d98c21a7b6e"
down_revision = "91f2d8a4c6b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "auth_version",
                sa.Integer(),
                server_default=sa.text("0"),
                nullable=False,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("auth_version")
