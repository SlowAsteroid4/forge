"""Modelo de Epic."""

from datetime import datetime
from typing import Literal

from sqlalchemy import CheckConstraint, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base

EpicKind = Literal["normal", "coordination", "version_container"]

_EPIC_KIND_CHECK = CheckConstraint(
    "epic_kind IN ('normal', 'coordination', 'version_container')",
    name="ck_epics_epic_kind",
)


class Epic(Base):
    """Épicas de Jira con rollup CP.

    epic_kind es clasificación de Forge (NO de Jira) — el ETL nunca la sobreescribe
    porque no está en epic_data del sync_orchestrator.
    """

    __tablename__ = "epics"
    __table_args__ = (_EPIC_KIND_CHECK,)

    jira_key: Mapped[str] = mapped_column(String(20), primary_key=True)
    project_code: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("projects.code", ondelete="RESTRICT"), index=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    cp_total: Mapped[float] = mapped_column(Float, default=0.0)
    # Clasificación de contenedor — 'normal' va al forecast; los demás solo a métricas de flujo
    epic_kind: Mapped[str] = mapped_column(
        String(20), nullable=False, default="normal", server_default="normal", index=True
    )
    last_synced_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    last_calculated_at: Mapped[datetime | None]
