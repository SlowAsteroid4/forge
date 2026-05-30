"""Modelo de Avatar (catálogo)."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class Avatar(Base):
    """Avatares predefinidos (sprites pixel-art)."""

    __tablename__ = "avatars"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    style: Mapped[str | None] = mapped_column(String(100))
    sprite_url: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
