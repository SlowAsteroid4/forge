"""Modelo de EngineVersion."""

from datetime import datetime

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class EngineVersion(Base):
    """Versiones del motor de cálculo."""

    __tablename__ = "engine_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version_tag: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    rules_snapshot: Mapped[str | None] = mapped_column(Text, comment="JSON con todas las reglas")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activated_at: Mapped[datetime | None]
