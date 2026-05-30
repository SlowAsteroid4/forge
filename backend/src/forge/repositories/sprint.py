"""SprintRepository — acceso a datos de sprints."""

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError, RuleViolationError
from forge.db.models.sprint import Sprint
from forge.repositories.base import BaseRepository


class SprintRepository(BaseRepository[Sprint, int]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Sprint)

    def get_active(self) -> Sprint | None:
        """Retorna el sprint en curso (no cerrado cuyas fechas cubren hoy).

        El modelo no tiene is_active explícito, se deriva de is_closed=False
        y que today esté dentro del rango start_date..end_date.
        Si hay múltiples (dato inválido), retorna el más reciente.
        """
        today = date.today()
        stmt = (
            select(Sprint)
            .where(Sprint.is_closed.is_(False))
            .where(Sprint.start_date <= today)
            .where(Sprint.end_date >= today)
            .order_by(Sprint.start_date.desc())
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def get_by_name(self, name: str) -> Sprint | None:
        stmt = select(Sprint).where(Sprint.name == name)
        return self._session.scalars(stmt).first()

    def list_all(self, include_closed: bool = False) -> list[Sprint]:  # type: ignore[override]
        """Lista todos los sprints. Por defecto excluye los cerrados."""
        stmt = select(Sprint).order_by(Sprint.start_date.desc())
        if not include_closed:
            stmt = stmt.where(Sprint.is_closed.is_(False))
        return list(self._session.scalars(stmt))

    def close(self, sprint_id: int, closed_by_id: int) -> Sprint:
        """Cierra un sprint. Lanza RuleViolationError si ya está cerrado."""
        sprint = self.get(sprint_id)
        if sprint is None:
            raise NotFoundError(f"Sprint {sprint_id} no encontrado")
        if sprint.is_closed:
            raise RuleViolationError(
                f"Sprint {sprint_id} ya está cerrado",
                details={"sprint_id": sprint_id},
            )
        sprint.is_closed = True
        sprint.closed_at = datetime.utcnow()
        sprint.closed_by = closed_by_id
        return self.update(sprint)

    def assign_mvp(self, sprint_id: int, player_id: int) -> Sprint:
        """Asigna el MVP del sprint."""
        sprint = self.get(sprint_id)
        if sprint is None:
            raise NotFoundError(f"Sprint {sprint_id} no encontrado")
        sprint.mvp_player_id = player_id
        return self.update(sprint)
