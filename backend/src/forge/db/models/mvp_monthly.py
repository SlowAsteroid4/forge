"""Modelo de MvpMonthly (MVP del mes)."""

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class MvpMonthly(Base):
    """Registro del MVP mensual."""

    __tablename__ = "mvp_monthly"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    month: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reason: Mapped[str | None] = mapped_column(Text)
    sp_reward: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    assigned_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    assigned_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="RESTRICT"), nullable=False
    )
    period_label: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Ej: 2026-05"
    )
