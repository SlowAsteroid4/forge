"""wp09_subtask_priority

Revision ID: 70b5c4f64d81
Revises: 9663836bf6a3
Create Date: 2026-06-04 16:24:56.042022

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70b5c4f64d81'
down_revision: Union[str, None] = '9663836bf6a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("subtasks", sa.Column("priority", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("subtasks", "priority")
