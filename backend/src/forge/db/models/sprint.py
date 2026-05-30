"""Modelo de Sprint."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class Sprint(Base):
    """Sprints (periodos de competencia)."""

    __tablename__ = "sprints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    closed_at: Mapped[datetime | None]
    closed_by: Mapped[int | None]
    mvp_player_id: Mapped[int | None]
