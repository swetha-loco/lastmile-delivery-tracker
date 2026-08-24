"""add order package handling fields

Revision ID: 9c2d4e6f8a10
Revises: 7fd34db0ff33
Create Date: 2026-08-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9c2d4e6f8a10"
down_revision: str | Sequence[str] | None = "7fd34db0ff33"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("package_description", sa.String(length=200), nullable=True))
    op.add_column(
        "orders",
        sa.Column("is_fragile", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("orders", sa.Column("delivery_instructions", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "delivery_instructions")
    op.drop_column("orders", "is_fragile")
    op.drop_column("orders", "package_description")
