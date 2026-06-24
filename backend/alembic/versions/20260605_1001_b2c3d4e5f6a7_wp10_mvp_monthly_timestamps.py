"""wp10_mvp_monthly_timestamps — add created_at / updated_at to mvp_monthly

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-05 10:01:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NOW = "2026-06-05 00:00:00"


def upgrade() -> None:
    with op.batch_alter_table("mvp_monthly") as batch_op:
        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=_NOW,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=_NOW,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("mvp_monthly") as batch_op:
        batch_op.drop_column("created_at")
        batch_op.drop_column("updated_at")
