"""SubtaskRepository — acceso a datos de subtasks."""

from datetime import datetime, timedelta
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

    def list_pending_cp_approval(
        self,
        area: str | None = None,
        player_id: int | None = None,
        project_code: str | None = None,
        min_waiting_days: int | None = None,
        statuses: list[str] | None = None,
    ) -> list[Subtask]:
        """Subtasks L/XL pendientes de aprobación de CP, con filtros opcionales.

        El parámetro ``statuses`` permite aplicar un gate por status (p.ej.
        ``['Backlog']`` para aprobar antes de que arranque el trabajo, que es lo
        que indica AC-4.2).  El default ``None`` desactiva el filtro y muestra
        todas las tallas L/XL sin importar el status — comportamiento actual en
        producción mientras el equipo decide dónde colocar el gate.

        ⚠️ DECISIÓN PENDIENTE (chat maestro): la distribución real es
           Done=18, Ready=7, In QA=6, Ready for QA=2, Backlog=1, otros=1.
           Usar ``statuses=['Backlog']`` dejaría la cola con 1 item.
           ¿El gate va en Backlog (pre-work) o se valida post-trabajo?
        """
        stmt = select(Subtask).where(
            Subtask.cp_approval_required.is_(True),
            Subtask.cp_approved_at.is_(None),
        )
        if statuses is not None:
            stmt = stmt.where(Subtask.status.in_(statuses))
        if area is not None:
            stmt = stmt.where(Subtask.area == area)
        if player_id is not None:
            stmt = stmt.where(Subtask.assignee_player_id == player_id)
        if project_code is not None:
            stmt = stmt.where(Subtask.project_code == project_code)
        if min_waiting_days is not None:
            cutoff = datetime.utcnow() - timedelta(days=min_waiting_days)
            stmt = stmt.where(
                (Subtask.cp_proposed_at <= cutoff) | Subtask.cp_proposed_at.is_(None)
            )
        return list(self._session.scalars(stmt))

    def list_xxl_detected(self) -> list[Subtask]:
        """Subtasks con talla XXL (deben dividirse)."""
        stmt = select(Subtask).where(Subtask.complexity_size == "XXL")
        return list(self._session.scalars(stmt))

    def get_for_approval(self, jira_key: str) -> Subtask | None:
        """Subtask con contexto completo para el flujo de aprobación."""
        return self._session.get(Subtask, jira_key)

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
