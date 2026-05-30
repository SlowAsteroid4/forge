"""wp01b_sp_adjustments_cycle_id

Revision ID: 8d19a99a4e21
Revises: c9d069c028f5
Create Date: 2026-05-29 23:52:44.117166

Cambios:
- ADD COLUMN cycle_id (nullable FK → cycles.id) en sp_adjustments
- Backfill cycle_id buscando el ciclo cuyo rango cubre applied_at
- Rename cycles.name: 'Sprint YYYY-WWW' → 'Ciclo YYYY-WWW'
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "8d19a99a4e21"
down_revision: Union[str, None] = "c9d069c028f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Añadir cycle_id a sp_adjustments
    with op.batch_alter_table("sp_adjustments") as batch_op:
        batch_op.add_column(
            sa.Column("cycle_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_sp_adjustments_cycle_id",
            "cycles",
            ["cycle_id"],
            ["id"],
        )
        batch_op.create_index("ix_sp_adjustments_cycle_id", ["cycle_id"])

    # 2. Backfill: asignar cycle_id basado en applied_at del adjustment
    conn = op.get_bind()
    adjustments = conn.execute(
        sa.text("SELECT id, applied_at FROM sp_adjustments WHERE applied_at IS NOT NULL")
    ).fetchall()

    for adj_id, applied_at in adjustments:
        cycle_row = conn.execute(
            sa.text(
                "SELECT id FROM cycles "
                "WHERE start_date <= date(:applied_at) AND end_date >= date(:applied_at) "
                "LIMIT 1"
            ),
            {"applied_at": applied_at},
        ).fetchone()
        if cycle_row:
            conn.execute(
                sa.text("UPDATE sp_adjustments SET cycle_id = :cid WHERE id = :aid"),
                {"cid": cycle_row[0], "aid": adj_id},
            )

    # 3. Rename cycles.name: 'Sprint YYYY-WWW' → 'Ciclo YYYY-WWW'
    conn.execute(
        sa.text(
            "UPDATE cycles SET name = replace(name, 'Sprint', 'Ciclo') WHERE name LIKE 'Sprint%'"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("sp_adjustments") as batch_op:
        batch_op.drop_index("ix_sp_adjustments_cycle_id")
        batch_op.drop_constraint("fk_sp_adjustments_cycle_id", type_="foreignkey")
        batch_op.drop_column("cycle_id")

    op.get_bind().execute(
        sa.text(
            "UPDATE cycles SET name = replace(name, 'Ciclo', 'Sprint') WHERE name LIKE 'Ciclo%'"
        )
    )
