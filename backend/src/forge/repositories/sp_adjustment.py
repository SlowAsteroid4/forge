"""SpAdjustmentRepository — acceso a ajustes de SP (append-only)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from forge.core.exceptions import AppendOnlyViolationError
from forge.db.models.sp_adjustment import SpAdjustment
from forge.repositories.base import BaseRepository


class SpAdjustmentRepository(BaseRepository[SpAdjustment, int]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, SpAdjustment)

    def update(self, entity: SpAdjustment) -> SpAdjustment:
        """SpAdjustment es append-only — no se puede modificar."""
        raise AppendOnlyViolationError("sp_adjustments", entity.id)

    def delete(self, entity: SpAdjustment) -> None:
        """SpAdjustment es append-only — no se puede eliminar."""
        raise AppendOnlyViolationError("sp_adjustments", entity.id)

    def list_by_subtask(self, subtask_key: str) -> list[SpAdjustment]:
        """Historial completo de ajustes sobre una subtask."""
        stmt = (
            select(SpAdjustment)
            .where(SpAdjustment.subtask_key == subtask_key)
            .order_by(SpAdjustment.applied_at)
        )
        return list(self._session.scalars(stmt))

    def list_by_applier(self, applied_by: int) -> list[SpAdjustment]:
        """Ajustes realizados por un PM o TL específico."""
        stmt = (
            select(SpAdjustment)
            .where(SpAdjustment.applied_by == applied_by)
            .order_by(SpAdjustment.applied_at.desc())
        )
        return list(self._session.scalars(stmt))

    def get_net_delta(self, subtask_key: str) -> float:
        """Suma neta de amount_sp para una subtask (bonos - penalizaciones)."""
        stmt = select(func.coalesce(func.sum(SpAdjustment.amount_sp), 0)).where(
            SpAdjustment.subtask_key == subtask_key
        )
        return float(self._session.scalar(stmt) or 0)
