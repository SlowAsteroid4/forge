"""wp10_monthly_mvp — add source_cycle_ids to mvp_monthly

Revision ID: a1b2c3d4e5f6
Revises: 70b5c4f64d81
Create Date: 2026-06-05 10:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "70b5c4f64d81"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("mvp_monthly") as batch_op:
        batch_op.add_column(
            sa.Column("source_cycle_ids", sa.Text(), nullable=True, comment="JSON array of cycle IDs in the month")
        )
        # Base class columns missing from original table creation
        batch_op.add_column(
            sa.Column("created_at", sa.DateTime(), nullable=True, comment="Timestamp de creación (UTC)")
        )
        batch_op.add_column(
            sa.Column("updated_at", sa.DateTime(), nullable=True, comment="Timestamp de última actualización (UTC)")
        )


def downgrade() -> None:
    with op.batch_alter_table("mvp_monthly") as batch_op:
        batch_op.drop_column("source_cycle_ids")
        batch_op.drop_column("created_at")
        batch_op.drop_column("updated_at")
