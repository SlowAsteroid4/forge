"""Modelo de SpAdjustment (append-only)."""

from datetime import datetime

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class SpAdjustment(Base):
    """Ajustes manuales de SP (append-only, inmutable)."""

    __tablename__ = "sp_adjustments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subtask_key: Mapped[str] = mapped_column(
        String(20), ForeignKey("subtasks.jira_key", ondelete="CASCADE"), nullable=False, index=True
    )
    adjustment_type: Mapped[str] = mapped_column(
        Enum("bonus", "penalty", name="adjustment_type_enum"), nullable=False
    )
    catalog_code: Mapped[str | None] = mapped_column(String(10))
    amount_sp: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    applied_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="RESTRICT"), nullable=False
    )
    applied_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    cycle_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("cycles.id", ondelete="SET NULL"), index=True
    )
