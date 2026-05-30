"""Modelo de Story."""

from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class Story(Base):
    """Historias con CP agregado."""

    __tablename__ = "stories"

    jira_key: Mapped[str] = mapped_column(String(20), primary_key=True)
    parent_epic_key: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("epics.jira_key", ondelete="SET NULL"), index=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)

    # Rollup CP
    cp_raw: Mapped[float] = mapped_column(Float, default=0.0)
    cp_total: Mapped[float] = mapped_column(Float, default=0.0)
    n_areas: Mapped[int] = mapped_column(Integer, default=0)
    has_dependency_chain: Mapped[bool] = mapped_column(Boolean, default=False)
    overhead_factor: Mapped[float] = mapped_column(Float, default=1.0)
    dependency_factor: Mapped[float] = mapped_column(Float, default=1.0)

    last_synced_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    last_calculated_at: Mapped[datetime | None]
