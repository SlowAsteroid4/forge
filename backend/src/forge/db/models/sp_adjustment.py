"""Modelo de SpAdjustment (append-only)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base

# Tipos de ajuste de SP:
#   bonus          — bonos planos positivos (mvp bonus manual, etc.)
#   penalty        — penalizaciones automáticas del motor (D01, D03...)
#   mvp_bonus      — bono MVP semanal (+5 SP al player)
#   mvp_reversal   — reversal de MVP semanal (append-only)
#   debuff_manual  — penalización manual aplicada por PM (UC-06)
#   reversal       — revierte total o parcialmente un debuff_manual (UC-06, append-only)
_ADJUSTMENT_TYPES = (
    "bonus",
    "penalty",
    "mvp_bonus",
    "mvp_reversal",
    "debuff_manual",
    "reversal",
    # Reversal de poda: ledger-only, amount_sp = -original.amount_sp.
    # El motor lo ignora; la exclusión real viene del filtro pruned_at IS NULL.
    "prune_reversal",
)

# Valores válidos para appeal_resolution
_APPEAL_RESOLUTIONS = ("upheld", "reversed", "reduced")


class SpAdjustment(Base):
    """Ajustes manuales de SP (append-only, inmutable)."""

    __tablename__ = "sp_adjustments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subtask_key: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("subtasks.jira_key", ondelete="CASCADE"), nullable=True, index=True
    )
    player_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=True, index=True
    )
    adjustment_type: Mapped[str] = mapped_column(
        Enum(*_ADJUSTMENT_TYPES, name="adjustment_type_enum"),
        nullable=False,
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

    # ── Metadatos de apelación (solo estos campos pueden hacerse UPDATE) ──
    # El valor de SP (amount_sp) NUNCA se modifica — siempre INSERT opuesto.
    is_appealed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    appeal_resolution: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # upheld | reversed | reduced
    appeal_resolved_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="SET NULL"), nullable=True
    )
    appeal_resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    appeal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
