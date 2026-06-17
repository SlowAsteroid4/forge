"""wp22: add pruned_at and prune_reason to subtasks (soft-delete for prune).

Revision ID: wp22_prune_soft_delete
Revises: wp19_epic_kind
Create Date: 2026-06-17

Aditiva e idempotente: verifica existencia de columna antes de agregarla.
El sync/ETL NUNCA escribe estos campos (ADR-008 — Forge-only classification).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "wp22_prune_soft_delete"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    existing_cols = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(subtasks)"))}

    if "pruned_at" not in existing_cols:
        op.add_column("subtasks", sa.Column("pruned_at", sa.DateTime(), nullable=True))
    if "prune_reason" not in existing_cols:
        op.add_column("subtasks", sa.Column("prune_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    # SQLite no soporta DROP COLUMN en versiones antiguas; se omite intencionalmente.
    pass
