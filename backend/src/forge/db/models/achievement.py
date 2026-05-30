"""Modelo de Achievement."""

from sqlalchemy import Boolean, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class Achievement(Base):
    """Achievements desbloqueables."""

    __tablename__ = "achievements"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rarity: Mapped[str] = mapped_column(
        Enum("common", "rare", "epic", "legendary", "mythic", name="rarity_enum"), nullable=False
    )
    sp_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unlock_condition_code: Mapped[str] = mapped_column(String(50), nullable=False)
    unlock_condition_params: Mapped[str | None] = mapped_column(Text)
    icon_code: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
