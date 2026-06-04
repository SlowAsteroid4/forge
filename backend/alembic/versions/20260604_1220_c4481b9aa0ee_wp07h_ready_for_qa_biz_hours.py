"""wp07h_ready_for_qa_biz_hours

Revision ID: c4481b9aa0ee
Revises: eec4694988b0
Create Date: 2026-06-04 12:20:55.070717

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4481b9aa0ee'
down_revision: Union[str, None] = 'eec4694988b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # WP-07h: separar la cola de handoff dev→QA ("Ready for QA") de la revisión
    # activa de QA/Edgar ("In QA"). El tiempo de "Ready for QA" es cuello del dev;
    # el de "In QA" se atribuye a QA/Edgar y se excluye de dev_resp_biz_hours.
    op.add_column(
        "subtasks",
        sa.Column("ready_for_qa_biz_hours", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("subtasks", "ready_for_qa_biz_hours")
