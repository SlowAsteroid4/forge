"""SubtaskRepository — acceso a datos de subtasks."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from forge.db.models.subtask import Subtask
from forge.repositories.base import BaseRepository

_DONE = "Done"


class SubtaskRepository(BaseRepository[Subtask, str]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Subtask)

    # ── cycle-aware (métodos actuales) ────────────────────────────────────

    def list_by_assignee(
        self, player_id: int, cycle_id: int | None = None
    ) -> list[Subtask]:
        """Subtasks de un dev, opcionalmente filtradas por ciclo."""
        stmt = select(Subtask).where(Subtask.assignee_player_id == player_id)
        if cycle_id is not None:
            stmt = stmt.where(Subtask.cycle_id == cycle_id)
        return list(self._session.scalars(stmt))

    def list_by_cycle(self, cycle_id: int, area: str | None = None) -> list[Subtask]:
        """Todas las subtasks de un ciclo, opcionalmente filtradas por área."""
        stmt = select(Subtask).where(Subtask.cycle_id == cycle_id)
        if area is not None:
            stmt = stmt.where(Subtask.area == area)
        return list(self._session.scalars(stmt))

    def list_done(
        self,
        cycle_id: int | None = None,
        player_id: int | None = None,
    ) -> list[Subtask]:
        """Subtasks con status='Done'. Acepta filtros opcionales de ciclo y player."""
        stmt = select(Subtask).where(Subtask.status == _DONE)
        if cycle_id is not None:
            stmt = stmt.where(Subtask.cycle_id == cycle_id)
        if player_id is not None:
            stmt = stmt.where(Subtask.assignee_player_id == player_id)
        return list(self._session.scalars(stmt))

    def list_xxl_detected(self) -> list[Subtask]:
        """Subtasks con talla XXL (deben dividirse)."""
        stmt = select(Subtask).where(Subtask.complexity_size == "XXL")
        return list(self._session.scalars(stmt))

    def get_cp_sum(self, player_id: int, cycle_id: int | None = None) -> float:
        """Suma de CP de subtasks Done del player (para leaderboard)."""
        stmt = (
            select(func.coalesce(func.sum(Subtask.cp), 0))
            .where(Subtask.assignee_player_id == player_id)
            .where(Subtask.status == _DONE)
            .where(Subtask.cp.is_not(None))
        )
        if cycle_id is not None:
            stmt = stmt.where(Subtask.cycle_id == cycle_id)
        return float(self._session.scalar(stmt) or 0)

    def get_sp_sum(self, player_id: int, cycle_id: int | None = None) -> float:
        """Suma de sp_final de subtasks Done del player (para wallet)."""
        stmt = (
            select(func.coalesce(func.sum(Subtask.sp_final), 0))
            .where(Subtask.assignee_player_id == player_id)
            .where(Subtask.status == _DONE)
            .where(Subtask.sp_final.is_not(None))
        )
        if cycle_id is not None:
            stmt = stmt.where(Subtask.cycle_id == cycle_id)
        return float(self._session.scalar(stmt) or 0)

    # ── DEPRECATED sprint_id aliases (WP-01b) — no usar en código nuevo ──

    def list_by_sprint(self, sprint_id: int, area: str | None = None) -> list[Subtask]:
        """DEPRECATED: usar list_by_cycle. Filtra por sprint_id (columna legacy)."""
        stmt = select(Subtask).where(Subtask.sprint_id == sprint_id)
        if area is not None:
            stmt = stmt.where(Subtask.area == area)
        return list(self._session.scalars(stmt))

    # ── Mutaciones ────────────────────────────────────────────────────────

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
