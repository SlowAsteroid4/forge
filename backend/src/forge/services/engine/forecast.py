"""Forecast calculator — UC-07: P30/P50/P85 por épica.

Fórmulas JPDS v2.0 §7.5 (ciclos):
  - Velocidad global por área = CP Done del área en últimos 4 ciclos cerrados / n_ciclos_con_datos
  - Optimista  : cp_pend / best_velocity  × 1.00  (best = mejor ciclo, ventana hasta 13 ciclos)
  - Realista   : cp_pend / avg_velocity   × 1.20
  - Conservador: cp_pend / (avg − σ)      × 1.30  (piso VELOCITY_FLOOR)
  - Fecha épica = max de las fechas por área (termina con su área más lenta)
  - Áreas con cp_pending == 0 se ignoran
  - preliminary = True si algún área tiene <4 ciclos con datos
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from forge.db.models.cycle import Cycle
from forge.db.models.epic import Epic
from forge.db.models.story import Story
from forge.db.models.subtask import Subtask

_WINDOW_SIZE = 4
_QUARTER_SIZE = 13
_VELOCITY_FLOOR = 1.0  # CP/ciclo mínimo para evitar división por cero
_OPT_FACTOR = 1.00
_REAL_FACTOR = 1.20
_CONS_FACTOR = 1.30

_DONE = "Done"
_CANCELLED = "Cancelled"


@dataclass
class AreaForecast:
    area: str
    cp_done: float
    cp_pending: float
    n_cycles_data: int
    velocity_avg: float
    velocity_best: float
    velocity_cons: float
    weeks_optimistic: float
    weeks_realistic: float
    weeks_conservative: float
    date_optimistic: date
    date_realistic: date
    date_conservative: date
    preliminary: bool


@dataclass
class EpicForecast:
    epic_key: str
    summary: str
    project_code: str
    status: str
    epic_kind: str
    cp_total: float
    cp_done: float
    cp_pending: float
    pct_done: float
    areas: list[AreaForecast] = field(default_factory=list)
    date_optimistic: date | None = None
    date_realistic: date | None = None
    date_conservative: date | None = None
    preliminary: bool = False
    warning: str | None = None
    blocked_count: int = 0


def _add_weeks(base: date, weeks: float) -> date:
    """Suma semanas calendario (redondeadas arriba) a una fecha."""
    return base + timedelta(weeks=math.ceil(weeks))


class ForecastCalculator:
    """Calcula escenarios P30/P50/P85 para épicas activas.

    Read-only: no escribe ninguna tabla de negocio.
    """

    def __init__(self, session: Session, today: date | None = None) -> None:
        self._s = session
        self._today = today or date.today()
        self._window_cycle_ids: list[int] = []
        self._quarter_cycle_ids: list[int] = []
        self._n_closed: int = 0
        self._area_velocity_cache: dict[str, dict[int, float]] | None = None

    # ──────────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────────

    def compute_all(
        self,
        project_code: str | None = None,
        epic_status: str | None = None,
    ) -> list[EpicForecast]:
        self._preload_cycles()
        velocity_map = self._area_velocity_by_cycle()  # {area: {cycle_id: cp}}

        epics = self._fetch_active_epics(project_code, epic_status)
        results = []
        for epic in epics:
            ef = self._compute_one(epic, velocity_map)
            results.append(ef)

        results.sort(key=lambda e: (e.pct_done, e.cp_pending), reverse=False)
        return results

    def compute_one(self, epic_key: str) -> EpicForecast | None:
        self._preload_cycles()
        velocity_map = self._area_velocity_by_cycle()
        epic = self._s.execute(
            select(Epic).where(Epic.jira_key == epic_key)
        ).scalar_one_or_none()
        if epic is None:
            return None
        return self._compute_one(epic, velocity_map)

    # ──────────────────────────────────────────────────────────────
    # Internals
    # ──────────────────────────────────────────────────────────────

    def _preload_cycles(self) -> None:
        if self._window_cycle_ids:
            return

        closed_ids = (
            self._s.execute(
                select(Cycle.id)
                .where(Cycle.status.in_(["closed", "archived"]))
                .order_by(Cycle.start_date.desc())
                .limit(_QUARTER_SIZE)
            )
            .scalars()
            .all()
        )
        self._quarter_cycle_ids = list(closed_ids)
        self._window_cycle_ids = self._quarter_cycle_ids[:_WINDOW_SIZE]
        self._n_closed = len(self._window_cycle_ids)

    def _area_velocity_by_cycle(self) -> dict[str, dict[int, float]]:
        """Returns {area: {cycle_id: cp_done}} for all closed cycles in quarter."""
        if self._area_velocity_cache is not None:
            return self._area_velocity_cache

        if not self._quarter_cycle_ids:
            self._area_velocity_cache = {}
            return {}

        rows = self._s.execute(
            select(
                Subtask.area,
                Subtask.cycle_id,
                func.coalesce(func.sum(Subtask.cp), 0).label("cp"),
            )
            .where(
                Subtask.cycle_id.in_(self._quarter_cycle_ids),
                Subtask.status == _DONE,
                Subtask.cp.is_not(None),
            )
            .group_by(Subtask.area, Subtask.cycle_id)
        ).all()

        result: dict[str, dict[int, float]] = {}
        for row in rows:
            area_map = result.setdefault(row.area, {})
            area_map[row.cycle_id] = float(row.cp)

        self._area_velocity_cache = result
        return result

    def _fetch_active_epics(
        self,
        project_code: str | None,
        epic_status: str | None,
    ) -> list[Epic]:
        # Solo épicas 'normal' van al forecast de fechas de cierre.
        # coordination/version_container nunca cierran → no tiene sentido proyectar ETA.
        q = select(Epic).where(
            Epic.status.not_in([_DONE, _CANCELLED]),
            Epic.epic_kind == "normal",
        )
        if project_code:
            q = q.where(Epic.project_code == project_code)
        if epic_status:
            q = q.where(Epic.status == epic_status)
        return list(self._s.execute(q).scalars().all())

    def _epic_subtask_cp(self, epic_key: str) -> tuple[dict[str, float], dict[str, float], int]:
        """Returns (cp_done_by_area, cp_pending_by_area, blocked_count) for an epic."""
        rows = self._s.execute(
            select(
                Subtask.area,
                Subtask.status,
                Subtask.cp,
            )
            .join(Story, Subtask.parent_story_key == Story.jira_key)
            .where(Story.parent_epic_key == epic_key, Subtask.cp.is_not(None))
        ).all()

        cp_done: dict[str, float] = {}
        cp_pending: dict[str, float] = {}
        blocked = 0
        for row in rows:
            area = row.area or "unknown"
            cp = float(row.cp)
            if row.status == _DONE:
                cp_done[area] = cp_done.get(area, 0.0) + cp
            elif row.status != _CANCELLED:
                cp_pending[area] = cp_pending.get(area, 0.0) + cp
                if "block" in row.status.lower():
                    blocked += 1

        return cp_done, cp_pending, blocked

    def _compute_one(
        self,
        epic: Epic,
        velocity_map: dict[str, dict[int, float]],
    ) -> EpicForecast:
        cp_done_area, cp_pending_area, blocked = self._epic_subtask_cp(epic.jira_key)

        total_done = sum(cp_done_area.values())
        total_pending = sum(cp_pending_area.values())
        total_cp = total_done + total_pending
        pct = round(total_done / total_cp * 100, 1) if total_cp > 0 else 0.0

        area_forecasts: list[AreaForecast] = []
        epic_preliminary = self._n_closed < _WINDOW_SIZE

        for area, pend_cp in cp_pending_area.items():
            if pend_cp <= 0:
                continue
            af = self._compute_area(area, pend_cp, cp_done_area.get(area, 0.0), velocity_map)
            area_forecasts.append(af)
            if af.preliminary:
                epic_preliminary = True

        # Epic date = max across areas
        opt_date = (
            max(af.date_optimistic for af in area_forecasts)
            if area_forecasts
            else self._today
        )
        real_date = (
            max(af.date_realistic for af in area_forecasts)
            if area_forecasts
            else self._today
        )
        cons_date = (
            max(af.date_conservative for af in area_forecasts)
            if area_forecasts
            else self._today
        )

        warning = None
        if epic_preliminary:
            warning = "Forecast preliminar (menos de 4 ciclos de historia)"
        if total_cp == 0:
            warning = "Sin CP estimado — forecast no disponible"

        return EpicForecast(
            epic_key=epic.jira_key,
            summary=epic.summary,
            project_code=epic.project_code or "",
            status=epic.status,
            epic_kind=epic.epic_kind,
            cp_total=total_cp,
            cp_done=total_done,
            cp_pending=total_pending,
            pct_done=pct,
            areas=area_forecasts,
            date_optimistic=opt_date,
            date_realistic=real_date,
            date_conservative=cons_date,
            preliminary=epic_preliminary,
            warning=warning,
            blocked_count=blocked,
        )

    def _compute_area(
        self,
        area: str,
        cp_pending: float,
        cp_done: float,
        velocity_map: dict[str, dict[int, float]],
    ) -> AreaForecast:
        area_cycles = velocity_map.get(area, {})

        # Window values (last 4 cycles) — missing cycles count as 0 CP
        window_vals = [area_cycles.get(cid, 0.0) for cid in self._window_cycle_ids]
        n_data = sum(1 for v in window_vals if v > 0)

        # Best velocity from full quarter
        quarter_vals = [area_cycles.get(cid, 0.0) for cid in self._quarter_cycle_ids]
        best_velocity = max(quarter_vals) if quarter_vals else 0.0

        avg_velocity = (
            sum(window_vals) / max(len(self._window_cycle_ids), 1)
            if self._window_cycle_ids
            else 0.0
        )

        sigma = 0.0
        if len(window_vals) >= 2:
            try:
                sigma = statistics.pstdev(window_vals)
            except statistics.StatisticsError:
                sigma = 0.0

        cons_velocity = max(avg_velocity - sigma, _VELOCITY_FLOOR)

        # Avoid zero-velocity edge cases
        eff_best = max(best_velocity, _VELOCITY_FLOOR)
        eff_avg = max(avg_velocity, _VELOCITY_FLOOR)

        weeks_opt = (cp_pending / eff_best) * _OPT_FACTOR
        weeks_real = (cp_pending / eff_avg) * _REAL_FACTOR
        weeks_cons = (cp_pending / cons_velocity) * _CONS_FACTOR

        preliminary = n_data < _WINDOW_SIZE

        return AreaForecast(
            area=area,
            cp_done=cp_done,
            cp_pending=cp_pending,
            n_cycles_data=n_data,
            velocity_avg=round(avg_velocity, 2),
            velocity_best=round(best_velocity, 2),
            velocity_cons=round(cons_velocity, 2),
            weeks_optimistic=round(weeks_opt, 2),
            weeks_realistic=round(weeks_real, 2),
            weeks_conservative=round(weeks_cons, 2),
            date_optimistic=_add_weeks(self._today, weeks_opt),
            date_realistic=_add_weeks(self._today, weeks_real),
            date_conservative=_add_weeks(self._today, weeks_cons),
            preliminary=preliminary,
        )
