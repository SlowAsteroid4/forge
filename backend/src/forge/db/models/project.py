"""Modelo de Project (Dungeon)."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class Project(Base):
    """Proyectos (Dungeons en Arena)."""

    __tablename__ = "projects"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    jira_prefix: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    internal_name: Mapped[str] = mapped_column(String(100), nullable=False)
    arena_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
