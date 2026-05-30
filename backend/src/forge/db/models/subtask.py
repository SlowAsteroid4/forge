"""Modelo de Subtask (núcleo del sistema)."""

from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class Subtask(Base):
    """
    Subtask: unidad ejecutable de trabajo.

    Dueña de CP y SP. La entidad más importante del modelo.
    """

    __tablename__ = "subtasks"

    # PK
    jira_key: Mapped[str] = mapped_column(String(20), primary_key=True)

    # Jerarquía
    parent_story_key: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("stories.jira_key", ondelete="SET NULL"), index=True
    )
    parent_epic_key: Mapped[str | None] = mapped_column(
        String(20), comment="Denormalizado para queries rápidas"
    )
    project_code: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("projects.code", ondelete="RESTRICT"), index=True
    )

    # Básico
    issue_type: Mapped[str] = mapped_column(String(40), nullable=False)
    area: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    assignee_player_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="SET NULL"), index=True
    )
    sprint_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sprints.id", ondelete="SET NULL"), index=True
    )
    cycle_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("cycles.id", ondelete="SET NULL"), index=True
    )

    # Complexity Points (estática post-aprobación)
    complexity_size: Mapped[str | None] = mapped_column(String(5))
    cp: Mapped[int | None] = mapped_column(Integer)
    cp_proposed_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="SET NULL")
    )
    cp_proposed_at: Mapped[datetime | None]
    cp_approved_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="SET NULL")
    )
    cp_approved_at: Mapped[datetime | None] = mapped_column(
        comment="REGLA: CP inmutable después de esta fecha"
    )
    cp_approval_required: Mapped[bool] = mapped_column(Boolean, default=False)

    # Tiempos (horas hábiles)
    done_at: Mapped[datetime | None] = mapped_column(index=True)
    lt_biz_hours: Mapped[float | None] = mapped_column(Float, comment="Lead Time")
    ct_biz_hours: Mapped[float | None] = mapped_column(Float, comment="Cycle Time")
    adj_ct_biz_hours: Mapped[float | None] = mapped_column(
        Float, comment="Cycle ajustado (sin blocked/waiting)"
    )
    dev_resp_biz_hours: Mapped[float | None] = mapped_column(
        Float, comment="Zona de responsabilidad del dev"
    )
    qa_biz_hours: Mapped[float | None] = mapped_column(Float)
    blocked_biz_hours: Mapped[float | None] = mapped_column(Float)
    waiting_biz_hours: Mapped[float | None] = mapped_column(Float)
    review_biz_hours: Mapped[float | None] = mapped_column(Float)

    # Calidad
    qa_first_pass: Mapped[bool | None] = mapped_column(Boolean)
    qa_attempts: Mapped[int] = mapped_column(Integer, default=0)
    review_rejections: Mapped[int] = mapped_column(Integer, default=0)

    # SP calculado (recalculable con engine_version)
    engine_version_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("engine_versions.id", ondelete="RESTRICT")
    )
    sp_base: Mapped[float | None] = mapped_column(Float, comment="= cp")
    m_calidad: Mapped[float] = mapped_column(Float, default=1.0)
    m_eficiencia: Mapped[float] = mapped_column(Float, default=1.0)
    m_dificultad: Mapped[float] = mapped_column(Float, default=1.0)
    m_lider: Mapped[float] = mapped_column(Float, default=1.0)
    m_cooperacion: Mapped[float] = mapped_column(Float, default=1.0)
    sp_flat_bonus: Mapped[float] = mapped_column(Float, default=0.0)
    sp_penalty: Mapped[float] = mapped_column(Float, default=0.0)
    sp_final: Mapped[float | None] = mapped_column(Float, comment="El que entra al leaderboard")
    sp_last_calculated_at: Mapped[datetime | None]

    # Difficulty modifier (custom field de Jira)
    difficulty_modifier_raw: Mapped[str | None] = mapped_column(String(50))

    # Auditoría
    last_synced_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    raw_changelog: Mapped[str | None] = mapped_column(Text, comment="JSON del changelog completo")
