"""CycleRepository — acceso a datos del modelo Cycle (Ritmo Operativo)."""

import json
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError, RuleViolationError
from forge.db.models.cycle import Cycle
from forge.repositories.base import BaseRepository


class CycleRepository(BaseRepository[Cycle, int]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Cycle)

    def get_active(self) -> Cycle | None:
        """Retorna el ciclo con status='active', o None si no existe."""
        stmt = select(Cycle).where(Cycle.status == "active").limit(1)
        return self._session.scalars(stmt).first()

    def get_by_iso_week(self, iso_year: int, iso_week: int) -> Cycle | None:
        stmt = select(Cycle).where(
            Cycle.iso_year == iso_year, Cycle.iso_week == iso_week
        )
        return self._session.scalars(stmt).first()

    def get_by_date(self, ref_date: date) -> Cycle | None:
        """Retorna el ciclo cuyo rango [start_date, end_date] contiene ref_date."""
        stmt = (
            select(Cycle)
            .where(Cycle.start_date <= ref_date)
            .where(Cycle.end_date >= ref_date)
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def list_recent_closed(self, limit: int = 4) -> list[Cycle]:
        """Últimos N ciclos cerrados/archivados (Ventana Móvil)."""
        stmt = (
            select(Cycle)
            .where(Cycle.status.in_(["closed", "archived"]))
            .order_by(Cycle.end_date.desc())
            .limit(limit)
        )
        return list(self._session.scalars(stmt))

    def list_by_year_month(self, iso_year: int, iso_month: int) -> list[Cycle]:
        """Ciclos que pertenecen a un mes calendario (por start_date)."""
        stmt = (
            select(Cycle)
            .where(Cycle.iso_year == iso_year)
            .where(Cycle.start_date >= date(iso_year, iso_month, 1))
            .where(
                Cycle.start_date
                < (
                    date(iso_year, iso_month + 1, 1)
                    if iso_month < 12
                    else date(iso_year + 1, 1, 1)
                )
            )
            .order_by(Cycle.start_date)
        )
        return list(self._session.scalars(stmt))

    def get_previous(self, cycle_id: int) -> Cycle | None:
        """Ciclo inmediatamente anterior al dado, por fecha."""
        current = self.get(cycle_id)
        if current is None:
            return None
        stmt = (
            select(Cycle)
            .where(Cycle.end_date < current.start_date)
            .order_by(Cycle.end_date.desc())
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def close_cycle(
        self,
        cycle_id: int,
        mvp_player_id: int | None,
        mvp_reason: str | None,
        closed_by: int,
    ) -> Cycle:
        """Cierra un ciclo activo. La lógica ritual completa se implementa en WP-03."""
        cycle = self.get(cycle_id)
        if cycle is None:
            raise NotFoundError(f"Cycle id={cycle_id} no encontrado")
        if cycle.status not in ("active", "planned"):
            raise RuleViolationError(
                f"Cycle id={cycle_id} no se puede cerrar (status='{cycle.status}')",
                details={"cycle_id": cycle_id, "status": cycle.status},
            )

        cycle.status = "closed"
        cycle.closed_at = datetime.utcnow()
        cycle.closed_by = closed_by

        if mvp_player_id is not None:
            cycle.mvp_player_id = mvp_player_id
            cycle.mvp_reason = mvp_reason
            cycle.mvp_assigned_at = datetime.utcnow()
            cycle.mvp_assigned_by = closed_by

        cycle.closing_snapshot_json = json.dumps(
            {
                "closed_at": datetime.utcnow().isoformat(),
                "closed_by": closed_by,
                "mvp_player_id": mvp_player_id,
            }
        )
        return self.update(cycle)

    def archive_old_closed(self) -> int:
        """Archiva ciclos cerrados hace más de 7 días. Devuelve el número archivado."""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=7)
        stmt = select(Cycle).where(
            Cycle.status == "closed",
            Cycle.closed_at <= cutoff,
        )
        cycles = list(self._session.scalars(stmt))
        for cycle in cycles:
            cycle.status = "archived"
            cycle.archived_at = datetime.utcnow()
            self.update(cycle)
        return len(cycles)
