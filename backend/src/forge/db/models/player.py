"""Modelo de Player (miembro del equipo)."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base

if TYPE_CHECKING:
    pass


class Player(Base):
    """
    Player: miembro del equipo.

    Un player es una persona real del equipo de desarrollo.
    Solo players activos con area en (BE, FE, DESIGN, DB, QA) participan en leaderboards.
    """

    __tablename__ = "players"

    # PK
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identificación en Jira
    jira_account_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(120), unique=True)

    # Área del player
    area: Mapped[str] = mapped_column(
        Enum("BE", "FE", "DESIGN", "DB", "QA", "PO", "PM", name="area_enum"),
        nullable=False,
        index=True,
        comment="BE/FE/DESIGN/DB/QA participan en leaderboards, PO/PM no",
    )

    # Employment
    employment_type: Mapped[str] = mapped_column(
        Enum("internal", "external", name="employment_type_enum"),
        nullable=False,
    )

    is_lead: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Rol de gobierno opcional (WP-15). Metadata pura: NO altera 'area' ni la
    # participación en producción/leaderboard. Ej: Jesús = PO pero area=DESIGN.
    role: Mapped[str | None] = mapped_column(
        String(20),
        comment="Rol de gobierno opcional (ej. 'PO'); independiente de 'area'",
    )

    # Identidad gamificada (Arena)
    class_code: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("classes.code", ondelete="RESTRICT")
    )
    avatar_code: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("avatars.code", ondelete="RESTRICT")
    )
    class_last_changed_at: Mapped[datetime | None] = mapped_column(
        comment="Fecha del último cambio de clase (restricción: 1 vez por trimestre)"
    )

    # Costos (privados, solo PM/Owner/Director ven)
    monthly_salary: Mapped[float | None] = mapped_column(
        Numeric(10, 2), comment="Salario mensual bruto (si es interno)"
    )
    hourly_rate: Mapped[float | None] = mapped_column(
        Numeric(8, 2), comment="Tarifa por hora (si es externo)"
    )
    monthly_hours_cap: Mapped[int | None] = mapped_column(
        Integer, comment="Tope de horas mensual (si es externo)"
    )

    # Metadata
    joined_at: Mapped[datetime | None] = mapped_column(comment="Fecha de ingreso al equipo")

    # Relationships
    # class_: Mapped["Class"] = relationship("Class", back_populates="players")
    # avatar: Mapped["Avatar"] = relationship("Avatar", back_populates="players")
