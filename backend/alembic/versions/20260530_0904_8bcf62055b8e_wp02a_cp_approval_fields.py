"""wp02a_cp_approval_fields

Revision ID: 8bcf62055b8e
Revises: 8d19a99a4e21
Create Date: 2026-05-30 09:04:53.758101

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8bcf62055b8e'
down_revision: Union[str, None] = '8d19a99a4e21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use ADD COLUMN directly (no rename needed, avoids view conflicts in SQLite)
    op.execute("ALTER TABLE subtasks ADD COLUMN cp_rejection_reason TEXT")
    op.execute(
        "ALTER TABLE subtasks ADD COLUMN cp_modified_post_approval BOOLEAN NOT NULL DEFAULT 0"
    )

    # Backfill: mark L/XL that need approval and don't have it yet
    op.execute(
        "UPDATE subtasks SET cp_approval_required = 1 "
        "WHERE complexity_size IN ('L', 'XL') AND cp_approved_at IS NULL"
    )


def downgrade() -> None:
    # SQLite doesn't support DROP COLUMN in older versions; recreate if needed
    pass
