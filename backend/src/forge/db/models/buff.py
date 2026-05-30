"""Modelo de Buff (multiplicadores positivos)."""

from sqlalchemy import Boolean, Enum, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class Buff(Base):
    """Buffs: multiplicadores positivos y bonos planos."""

    __tablename__ = "buffs"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    narrative_name: Mapped[str] = mapped_column(String(100), nullable=False)
    multiplier_type: Mapped[str] = mapped_column(String(50), nullable=False)
    trigger_description: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    mechanic: Mapped[str] = mapped_column(
        Enum("multiply", "add", "add_to_multiplier", name="buff_mechanic_enum"), nullable=False
    )
    applies_to_area: Mapped[str | None] = mapped_column(String(20))
    icon_code: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
