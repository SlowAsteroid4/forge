"""Modelo de Epic."""

from datetime import datetime

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class Epic(Base):
    """Épicas de Jira con rollup CP."""

    __tablename__ = "epics"

    jira_key: Mapped[str] = mapped_column(String(20), primary_key=True)
    project_code: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("projects.code", ondelete="RESTRICT"), index=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    cp_total: Mapped[float] = mapped_column(Float, default=0.0)
    last_synced_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    last_calculated_at: Mapped[datetime | None]
