"""Modelo de LeaderboardSnapshot."""

from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class LeaderboardSnapshot(Base):
    """Snapshots históricos de leaderboard."""

    __tablename__ = "leaderboard_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sprint_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sprints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    sp_total: Mapped[float] = mapped_column(Float, nullable=False)
    cp_completed: Mapped[float] = mapped_column(Float, nullable=False)
    achievements_count: Mapped[int] = mapped_column(Integer, default=0)
    snapshot_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, index=True
    )
