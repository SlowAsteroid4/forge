"""Modelo de Class RPG (catálogo)."""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class Class(Base):
    """Clases RPG (catálogo cosmético)."""

    __tablename__ = "classes"

    code: Mapped[str] = mapped_column(String(10), primary_key=True, comment="C01, C02...")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="Archmage, Paladin...")
    archetype: Mapped[str] = mapped_column(String(100), nullable=False)
    flavor_description: Mapped[str | None] = mapped_column(Text)
    sprite_url: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
