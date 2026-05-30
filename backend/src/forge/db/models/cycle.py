"""Modelo de Cycle (Ritmo Operativo — reemplaza Sprint en WP-01b)."""

from datetime import date, datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class Cycle(Base):
    """Ciclo semanal Lun–Vie del Ritmo Operativo."""

    __tablename__ = "cycles"
    __table_args__ = (
        UniqueConstraint("iso_year", "iso_week", name="uq_cycle_iso_week"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    iso_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    iso_week: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(nullable=False, index=True)

    # Estado del ciclo
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="planned", index=True
    )  # planned | active | closed | archived

    # MVP semanal
    mvp_player_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="SET NULL"), index=True
    )
    mvp_reason: Mapped[str | None] = mapped_column(Text)
    mvp_assigned_at: Mapped[datetime | None]
    mvp_assigned_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="SET NULL")
    )

    # Lifecycle timestamps
    opened_at: Mapped[datetime | None]
    closed_at: Mapped[datetime | None]
    closed_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="SET NULL")
    )
    archived_at: Mapped[datetime | None]

    # Snapshot JSON al cerrar
    closing_snapshot_json: Mapped[str | None] = mapped_column(Text)

    # Marca los ciclos migrados desde sprints históricos (no requieren MVP)
    is_legacy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
