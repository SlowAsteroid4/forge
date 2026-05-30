"""Modelo de AchievementUnlock."""

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class AchievementUnlock(Base):
    """Desbloqueos de achievements."""

    __tablename__ = "achievement_unlocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True
    )
    achievement_code: Mapped[str] = mapped_column(
        String(10), ForeignKey("achievements.code", ondelete="RESTRICT"), nullable=False
    )
    unlocked_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    sprint_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sprints.id", ondelete="SET NULL")
    )
