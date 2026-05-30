"""Modelo de Debuff (penalizaciones)."""

from sqlalchemy import Boolean, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class Debuff(Base):
    """Debuffs: penalizaciones."""

    __tablename__ = "debuffs"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    narrative_name: Mapped[str] = mapped_column(String(100), nullable=False)
    trigger_description: Mapped[str] = mapped_column(Text, nullable=False)
    penalty_type: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    applies_to_area: Mapped[str | None] = mapped_column(String(20))
    icon_code: Mapped[str | None] = mapped_column(String(50))
    is_appealable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
