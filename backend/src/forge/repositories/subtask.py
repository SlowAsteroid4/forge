"""SubtaskRepository — acceso a datos de subtasks."""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from forge.core.exceptions import CPImmutableError, NotFoundError
from forge.db.models.subtask import Subtask
from forge.repositories.base import BaseRepository

_DONE = "Done"


class SubtaskRepository(BaseRepository[Subtask, str]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Subtask)

    def list_by_assignee(
        self, player_id: int, sprint_id: int | None = None
    ) -> list[Subtask]:
        """Subtasks de un dev, opcionalmente filtradas por sprint."""
        stmt = select(Subtask).where(Subtask.assignee_player_id == player_id)
        if sprint_id is not None:
            stmt = stmt.where(Subtask.sprint_id == sprint_id)
        return list(self._session.scalars(stmt))

    def list_by_sprint(self, sprint_id: int, area: str | None = None) -> list[Subtask]:
        """Todas las subtasks de un sprint, opcionalmente filtradas por área."""
        stmt = select(Subtask).where(Subtask.sprint_id == sprint_id)
        if area is not None:
            stmt = stmt.where(Subtask.area == area)
        return list(self._session.scalars(stmt))

    def list_done(
        self,
        sprint_id: int | None = None,
        player_id: int | None = None,
    ) -> list[Subtask]:
        """Subtasks con status='Done'. Acepta filtros opcionales de sprint y player."""
        stmt = select(Subtask).where(Subtask.status == _DONE)
        if sprint_id is not None:
            stmt = stmt.where(Subtask.sprint_id == sprint_id)
        if player_id is not None:
            stmt = stmt.where(Subtask.assignee_player_id == player_id)
        return list(self._session.scalars(stmt))

    def list_pending_cp_approval(self) -> list[Subtask]:
        """Subtasks L/XL que requieren aprobación de CP pero aún no la tienen."""
        stmt = select(Subtask).where(
            Subtask.cp_approval_required.is_(True),
            Subtask.cp_approved_at.is_(None),
        )
        return list(self._session.scalars(stmt))

    def get_cp_sum(self, player_id: int, sprint_id: int | None = None) -> float:
        """Suma de CP de subtasks Done del player (para leaderboard)."""
        stmt = (
            select(func.coalesce(func.sum(Subtask.cp), 0))
            .where(Subtask.assignee_player_id == player_id)
            .where(Subtask.status == _DONE)
            .where(Subtask.cp.is_not(None))
        )
        if sprint_id is not None:
            stmt = stmt.where(Subtask.sprint_id == sprint_id)
        return float(self._session.scalar(stmt) or 0)

    def get_sp_sum(self, player_id: int, sprint_id: int | None = None) -> float:
        """Suma de sp_final de subtasks Done del player (para wallet)."""
        stmt = (
            select(func.coalesce(func.sum(Subtask.sp_final), 0))
            .where(Subtask.assignee_player_id == player_id)
            .where(Subtask.status == _DONE)
            .where(Subtask.sp_final.is_not(None))
        )
        if sprint_id is not None:
            stmt = stmt.where(Subtask.sprint_id == sprint_id)
        return float(self._session.scalar(stmt) or 0)

    def upsert(self, data: dict[str, Any]) -> Subtask:
        """Crea o actualiza una subtask por jira_key (para ETL)."""
        subtask = self.get(data["jira_key"])
        if subtask is None:
            subtask = Subtask(**data)
            return self.create(subtask)
        for key, value in data.items():
            if key == "jira_key":
                continue
            setattr(subtask, key, value)
        return self.update(subtask)

    def approve_cp(
        self, jira_key: str, approver_id: int, approved_at: datetime
    ) -> Subtask:
        """Sella cp_approved_at. Lanza CPImmutableError si ya fue aprobado."""
        subtask = self.get(jira_key)
        if subtask is None:
            raise NotFoundError(f"Subtask {jira_key} no encontrada")
        if subtask.cp_approved_at is not None:
            raise CPImmutableError(jira_key)
        subtask.cp_approved_by = approver_id
        subtask.cp_approved_at = approved_at
        return self.update(subtask)
