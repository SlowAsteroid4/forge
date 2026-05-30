"""Modelo de ForecastSnapshot (ventana móvil 4 ciclos)."""

from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class ForecastSnapshot(Base):
    """Snapshot de forecast generado al cerrar un ciclo."""

    __tablename__ = "forecast_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    generated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, index=True
    )
    trigger_cycle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cycles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    epic_key: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    area: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Percentiles de velocidad de la ventana móvil
    p30_cp_per_cycle: Mapped[float | None] = mapped_column(Float)
    p50_cp_per_cycle: Mapped[float | None] = mapped_column(Float)
    p85_cp_per_cycle: Mapped[float | None] = mapped_column(Float)

    # Estimaciones de entrega
    remaining_cp: Mapped[float | None] = mapped_column(Float)
    eta_p30_cycles: Mapped[float | None] = mapped_column(Float)
    eta_p50_cycles: Mapped[float | None] = mapped_column(Float)
    eta_p85_cycles: Mapped[float | None] = mapped_column(Float)

    snapshot_json: Mapped[str | None] = mapped_column(Text, comment="Datos completos del forecast")
