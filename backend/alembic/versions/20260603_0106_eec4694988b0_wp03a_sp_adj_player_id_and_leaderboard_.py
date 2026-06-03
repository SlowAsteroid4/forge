"""wp03a_sp_adj_player_id_and_leaderboard_period_type

Revision ID: eec4694988b0
Revises: 8bcf62055b8e
Create Date: 2026-06-03 01:06:51.957123

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eec4694988b0'
down_revision: Union[str, None] = '8bcf62055b8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── sp_adjustments: subtask_key nullable + player_id ──────────────────
    with op.batch_alter_table("sp_adjustments", schema=None) as batch_op:
        batch_op.alter_column(
            "subtask_key",
            existing_type=sa.VARCHAR(20),
            nullable=True,
        )
        batch_op.add_column(
            sa.Column(
                "player_id",
                sa.Integer(),
                sa.ForeignKey("players.id", ondelete="CASCADE"),
                nullable=True,
            )
        )

    # ── leaderboard_snapshots: sprint_id nullable + period_type ──────────
    with op.batch_alter_table("leaderboard_snapshots", schema=None) as batch_op:
        batch_op.alter_column(
            "sprint_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.add_column(
            sa.Column(
                "period_type",
                sa.String(20),
                nullable=False,
                server_default="sprint",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("leaderboard_snapshots", schema=None) as batch_op:
        batch_op.drop_column("period_type")
        batch_op.alter_column(
            "sprint_id",
            existing_type=sa.Integer(),
            nullable=False,
        )

    with op.batch_alter_table("sp_adjustments", schema=None) as batch_op:
        batch_op.drop_column("player_id")
        batch_op.alter_column(
            "subtask_key",
            existing_type=sa.VARCHAR(20),
            nullable=False,
        )
