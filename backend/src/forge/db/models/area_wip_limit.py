"""Catálogo de límites WIP por área (configurable sin tocar código)."""

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from forge.db.base import Base


class AreaWipLimit(Base):
    """Umbral de WIP por área técnica.

    Editable directamente en la BD o re-sembrando desde seed/area_wip_limits.yaml.
    QA se marca con exclude_from_wip=True: no genera semáforo, se mide por tiempo de revisión.
    """

    __tablename__ = "area_wip_limits"

    area: Mapped[str] = mapped_column(String(20), primary_key=True)
    wip_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    exclude_from_wip: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="Si True, área excluida del semáforo WIP"
    )
