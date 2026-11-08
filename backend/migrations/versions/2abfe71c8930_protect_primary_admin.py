"""Protect the configured primary administrator and fix location capitalization.

Revision ID: 2abfe71c8930
Revises: 4d98c21a7b6e
Create Date: 2026-11-08 14:20:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "2abfe71c8930"
down_revision = "4d98c21a7b6e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_primary_admin",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.execute(
        sa.text(
            "UPDATE locations SET name = :new_name "
            "WHERE lower(trim(name)) = :old_name"
        ).bindparams(
            new_name="Gosrani Technical Office",
            old_name="gosrani technical office",
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE locations SET name = :old_name "
            "WHERE name = :new_name"
        ).bindparams(
            old_name="Gosrani Technical office",
            new_name="Gosrani Technical Office",
        )
    )
    op.drop_column("users", "is_primary_admin")
