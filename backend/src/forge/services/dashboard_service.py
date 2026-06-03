"""DashboardService — UC-02: Dashboard general del ciclo en curso (Ritmo Operativo)."""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError
from forge.db.models.cycle import Cycle
from forge.db.models.player import Player
from forge.db.models.project import Project
from forge.db.models.subtask import Subtask
from forge.schemas.dashboard import (
    AlertItem,
    AreaProgress,
    CycleHeader,
    CycleSummary,
    DashboardResponse,
    KPICards,
    KPIValue,
    PlayerStatus,
    ProjectSummary,
    QAFirstPass,
)

# ──────────────────────────────────────────────
# Constantes de negocio
# ──────────────────────────────────────────────

_DONE = "Done"
_TERMINAL = frozenset({"Done", "Cancelled"})
_BLOCKED = frozenset({"Blocked", "Waiting"})
_LEADERBOARD_AREAS = ["BE", "FE", "DESIGN", "DB", "QA"]

_WIP_THRESHOLDS: dict[str, int] = {
    "BE": 3,
    "FE": 3,
    "DESIGN": 4,
    "DB": 5,
    "QA": 5,
}
_DEFAULT_WIP = 5
_ABANDONED_DAYS = 14


class DashboardService:
    """Calcula todos los datos del dashboard de ciclo.

    Cada método `_build_*` es independiente y testeable.
    Todas las queries manejan NULL (sin datos) devolviendo 0 / listas vacías.
    """

    def __init__(self, session: Session) -> None:
        self._s = session

    # ──────────────────────────────────────────
    # Punto de entrada principal
    # ──────────────────────────────────────────

    def get_dashboard(
        self,
        project_code: str | None = None,
        cycle_id: int | None = None,
    ) -> DashboardResponse:
        """Construye la respuesta completa del dashboard.

        Args:
            project_code: Filtro de proyecto (None = todos).
            cycle_id:     Ciclo específico (None = ciclo activo).
        """
        cycle = self._get_cycle(cycle_id)
        available_projects = self._get_available_projects()
        available_cycles = self._get_available_cycles()

        if cycle is None:
            return DashboardResponse(
                no_cycle_message="No hay un ciclo activo. Crea uno en la sección de configuración.",
                available_projects=available_projects,
                available_cycles=available_cycles,
            )

        prev_cycle = self._get_previous_cycle(cycle)

        return DashboardResponse(
            cycle=self._build_cycle_header(cycle),
            kpis=self._build_kpis(cycle, project_code, prev_cycle),
            area_progress=self._build_area_progress(cycle, project_code),
            player_status=self._build_player_status(cycle, project_code),
            alerts=self._build_alerts(cycle, project_code),
            available_projects=available_projects,
            available_cycles=available_cycles,
            last_synced_at=self._get_last_sync(cycle.id, project_code),
        )

    # ──────────────────────────────────────────
    # Cycle helpers
    # ──────────────────────────────────────────

    def _get_cycle(self, cycle_id: int | None) -> Cycle | None:
        """Retorna el ciclo solicitado o el activo si cycle_id es None."""
        if cycle_id is not None:
            cycle = self._s.get(Cycle, cycle_id)
            if cycle is None:
                raise NotFoundError(f"Cycle {cycle_id} no encontrado")
            return cycle
        # Ciclo activo
        stmt = select(Cycle).where(Cycle.status == "active").limit(1)
        return self._s.scalars(stmt).first()

    def _get_previous_cycle(self, current: Cycle) -> Cycle | None:
        """Ciclo inmediatamente anterior al actual, por fecha de fin."""
        stmt = (
            select(Cycle)
            .where(Cycle.end_date < current.start_date)
            .order_by(Cycle.end_date.desc())
            .limit(1)
        )
        return self._s.scalars(stmt).first()

    def _build_cycle_header(self, cycle: Cycle) -> CycleHeader:
        today = date.today()
        start = cycle.start_date
        end = cycle.end_date
        days_total = max((end - start).days + 1, 1)
        days_elapsed = min(max((today - start).days + 1, 0), days_total)
        return CycleHeader(
            id=cycle.id,
            name=cycle.name,
            start_date=start,
            end_date=end,
            days_elapsed=days_elapsed,
            days_total=days_total,
            progress_pct=round(days_elapsed / days_total * 100, 1),
        )

    # ──────────────────────────────────────────
    # KPI cards
    # ──────────────────────────────────────────

    def _build_kpis(
        self,
        cycle: Cycle,
        project_code: str | None,
        prev_cycle: Cycle | None,
    ) -> KPICards:
        cp_done_current = self._cp_done(cycle.id, project_code)
        cp_done_prev = self._cp_done(prev_cycle.id, project_code) if prev_cycle else None
        delta = _delta_pct(cp_done_current, cp_done_prev)

        return KPICards(
            cp_done=KPIValue(
                value=cp_done_current,
                previous_value=cp_done_prev,
                delta_pct=delta,
            ),
            qa_first_pass=self._qa_first_pass(cycle.id, project_code),
        )

    def _cp_done(self, cycle_id: int, project_code: str | None) -> float:
        stmt = (
            select(func.coalesce(func.sum(Subtask.cp), 0))
            .where(Subtask.cycle_id == cycle_id)
            .where(Subtask.status == _DONE)
            .where(Subtask.cp.is_not(None))
        )
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        return float(self._s.scalar(stmt) or 0)

    def _qa_first_pass(self, cycle_id: int, project_code: str | None) -> QAFirstPass:
        """% de subtasks Done en el ciclo que pasaron QA al primer intento."""
        stmt = (
            select(Subtask.qa_first_pass)
            .where(Subtask.cycle_id == cycle_id)
            .where(Subtask.status == _DONE)
            .where(Subtask.qa_first_pass.is_not(None))
        )
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        rows = self._s.scalars(stmt).all()
        total = len(rows)
        passed = sum(1 for v in rows if v)
        rate = round(passed / total, 3) if total > 0 else 0.0
        return QAFirstPass(rate=rate, passed=passed, total=total)

    # ──────────────────────────────────────────
    # Progreso por área
    # ──────────────────────────────────────────

    def _build_area_progress(
        self,
        cycle: Cycle,
        project_code: str | None,
    ) -> list[AreaProgress]:
        result = []
        for area in _LEADERBOARD_AREAS:
            cp_done = self._area_cp_done(cycle.id, area, project_code)
            active_devs = self._area_live_devs(area, project_code)
            has_bottleneck = self._area_has_wip_bottleneck(area, project_code)

            result.append(
                AreaProgress(
                    area=area,
                    cp_done=cp_done,
                    active_devs=active_devs,
                    has_wip_bottleneck=has_bottleneck,
                )
            )
        return result

    def _area_cp_done(self, cycle_id: int, area: str, project_code: str | None) -> float:
        stmt = (
            select(func.coalesce(func.sum(Subtask.cp), 0))
            .where(Subtask.cycle_id == cycle_id, Subtask.area == area, Subtask.status == _DONE)
            .where(Subtask.cp.is_not(None))
        )
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        return float(self._s.scalar(stmt) or 0)

    def _area_live_devs(self, area: str, project_code: str | None) -> int:
        """Devs con WIP activo AHORA en esta área (sin filtro de ciclo)."""
        stmt = (
            select(func.count(Subtask.assignee_player_id.distinct()))
            .where(
                Subtask.area == area,
                Subtask.status.not_in(list(_TERMINAL)),
                Subtask.assignee_player_id.is_not(None),
            )
        )
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        return int(self._s.scalar(stmt) or 0)

    def _area_has_wip_bottleneck(self, area: str, project_code: str | None) -> bool:
        """Algún dev del área excede umbral de WIP (en vivo, sin filtro de ciclo)."""
        threshold = _WIP_THRESHOLDS.get(area, _DEFAULT_WIP)
        inner = (
            select(
                Subtask.assignee_player_id,
                func.count().label("wip"),
            )
            .where(
                Subtask.area == area,
                Subtask.status.not_in(list(_TERMINAL)),
                Subtask.assignee_player_id.is_not(None),
            )
            .group_by(Subtask.assignee_player_id)
        )
        if project_code:
            inner = inner.where(Subtask.project_code == project_code)
        rows = self._s.execute(inner).all()
        return any(r.wip > threshold for r in rows)

    # ──────────────────────────────────────────
    # Estado de devs
    # ──────────────────────────────────────────

    def _build_player_status(
        self,
        cycle: Cycle,
        project_code: str | None,
    ) -> list[PlayerStatus]:
        """Retorna TODOS los devs activos con WIP en vivo + done del ciclo."""
        players_stmt = select(Player).where(Player.is_active.is_(True))
        players = self._s.scalars(players_stmt).all()

        result: list[PlayerStatus] = []
        for player in players:
            wip = self._player_wip_live(player.id, project_code)
            done_count = self._player_done_count(cycle.id, player.id, project_code)
            status = self._player_status_label(player.id, player.area, wip, project_code)

            result.append(
                PlayerStatus(
                    player_id=player.id,
                    display_name=player.display_name,
                    area=player.area,
                    avatar_code=player.avatar_code,
                    wip_live=wip,
                    done_subtasks=done_count,
                    status=status,
                )
            )

        return sorted(result, key=lambda p: (p.wip_live == 0, -p.done_subtasks))

    def _player_wip_live(self, player_id: int, project_code: str | None) -> int:
        """WIP en vivo del dev (sin filtro de ciclo)."""
        stmt = (
            select(func.count())
            .select_from(Subtask)
            .where(
                Subtask.assignee_player_id == player_id,
                Subtask.status.not_in(list(_TERMINAL)),
            )
        )
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        return int(self._s.scalar(stmt) or 0)

    def _player_done_count(
        self, cycle_id: int, player_id: int, project_code: str | None
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Subtask)
            .where(
                Subtask.cycle_id == cycle_id,
                Subtask.assignee_player_id == player_id,
                Subtask.status == _DONE,
            )
        )
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        return int(self._s.scalar(stmt) or 0)

    def _player_status_label(
        self,
        player_id: int,
        area: str,
        wip_live: int,
        project_code: str | None,
    ) -> str:
        if wip_live == 0:
            return "inactive"

        blocked_stmt = (
            select(func.count())
            .select_from(Subtask)
            .where(
                Subtask.assignee_player_id == player_id,
                Subtask.status.in_(list(_BLOCKED)),
            )
        )
        if project_code:
            blocked_stmt = blocked_stmt.where(Subtask.project_code == project_code)
        blocked_count = int(self._s.scalar(blocked_stmt) or 0)

        if blocked_count >= wip_live:
            return "blocked"

        threshold = _WIP_THRESHOLDS.get(area, _DEFAULT_WIP)
        if wip_live > threshold:
            return "wip_high"

        return "productive"

    # ──────────────────────────────────────────
    # Alertas
    # ──────────────────────────────────────────

    def _build_alerts(
        self,
        cycle: Cycle,
        project_code: str | None,
    ) -> list[AlertItem]:
        alerts: list[AlertItem] = []
        alerts.extend(self._alerts_abandoned(cycle, project_code))
        alerts.extend(self._alerts_waiting_long(cycle, project_code))
        alerts.extend(self._alerts_cp_pending(cycle, project_code))
        alerts.extend(self._alerts_wip_exceeded(cycle, project_code))
        return alerts

    def _alerts_abandoned(self, cycle: Cycle, project_code: str | None) -> list[AlertItem]:
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=_ABANDONED_DAYS)
        stmt = (
            select(Subtask.jira_key, Subtask.assignee_player_id)
            .where(
                Subtask.cycle_id == cycle.id,
                Subtask.status.not_in(list(_TERMINAL)),
                Subtask.created_at < cutoff,
            )
        )
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        rows = self._s.execute(stmt).all()
        return [
            AlertItem(
                alert_type="abandoned_subtask",
                severity="critical",
                message=f"{r.jira_key} lleva más de {_ABANDONED_DAYS} días sin completarse.",
                subtask_key=r.jira_key,
                player_id=r.assignee_player_id,
            )
            for r in rows
        ]

    def _alerts_waiting_long(self, cycle: Cycle, project_code: str | None) -> list[AlertItem]:
        """Subtasks bloqueadas/en espera con >18h hábiles acumuladas."""
        stmt = (
            select(Subtask.jira_key, Subtask.assignee_player_id)
            .where(
                Subtask.cycle_id == cycle.id,
                Subtask.status.in_(list(_BLOCKED)),
            )
        )
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        rows = self._s.execute(stmt).all()
        return [
            AlertItem(
                alert_type="waiting_long",
                severity="warning",
                message=f"{r.jira_key} está en estado bloqueado/espera.",
                subtask_key=r.jira_key,
                player_id=r.assignee_player_id,
            )
            for r in rows
        ]

    def _alerts_cp_pending(self, cycle: Cycle, project_code: str | None) -> list[AlertItem]:
        """L/XL sin CP aprobado."""
        stmt = (
            select(Subtask.jira_key, Subtask.assignee_player_id)
            .where(
                Subtask.cycle_id == cycle.id,
                Subtask.cp_approval_required.is_(True),
                Subtask.cp_approved_at.is_(None),
            )
        )
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        rows = self._s.execute(stmt).all()
        return [
            AlertItem(
                alert_type="cp_pending_approval",
                severity="warning",
                message=f"{r.jira_key} requiere aprobación de CP (talla L/XL).",
                subtask_key=r.jira_key,
                player_id=r.assignee_player_id,
            )
            for r in rows
        ]

    def _alerts_wip_exceeded(self, cycle: Cycle, project_code: str | None) -> list[AlertItem]:
        """Devs que superan su umbral de WIP (en vivo, sin filtro de ciclo)."""
        alerts: list[AlertItem] = []
        for area in _LEADERBOARD_AREAS:
            threshold = _WIP_THRESHOLDS.get(area, _DEFAULT_WIP)
            wip_stmt = (
                select(
                    Subtask.assignee_player_id,
                    func.count().label("wip"),
                )
                .where(
                    Subtask.area == area,
                    Subtask.status.not_in(list(_TERMINAL)),
                    Subtask.assignee_player_id.is_not(None),
                )
                .group_by(Subtask.assignee_player_id)
            )
            if project_code:
                wip_stmt = wip_stmt.where(Subtask.project_code == project_code)
            for row in self._s.execute(wip_stmt):
                if row.wip > threshold:
                    player = self._s.get(Player, row.assignee_player_id)
                    name = player.display_name if player else f"Player {row.assignee_player_id}"
                    alerts.append(
                        AlertItem(
                            alert_type="wip_exceeded",
                            severity="warning",
                            message=(
                                f"{name} tiene {row.wip} subtasks activas en {area} "
                                f"(máximo {threshold})."
                            ),
                            player_id=row.assignee_player_id,
                        )
                    )
        return alerts

    # ──────────────────────────────────────────
    # Auxiliares de catálogos
    # ──────────────────────────────────────────

    def _get_available_projects(self) -> list[ProjectSummary]:
        stmt = select(Project).where(Project.is_active.is_(True))
        projects = self._s.scalars(stmt).all()
        return [
            ProjectSummary(
                code=p.code,
                internal_name=p.internal_name,
                jira_prefix=p.jira_prefix,
            )
            for p in projects
        ]

    def _get_available_cycles(self) -> list[CycleSummary]:
        stmt = select(Cycle).order_by(Cycle.start_date.desc())
        cycles = self._s.scalars(stmt).all()
        return [
            CycleSummary(
                id=c.id,
                name=c.name,
                start_date=c.start_date,
                end_date=c.end_date,
                status=c.status,
            )
            for c in cycles
        ]

    def _get_last_sync(self, cycle_id: int, project_code: str | None) -> datetime | None:
        """Max(last_synced_at) del ciclo. Si no hay datos, devuelve el global."""
        stmt = select(func.max(Subtask.last_synced_at)).where(Subtask.cycle_id == cycle_id)
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        result = self._s.scalar(stmt)
        if result is None:
            result = self._s.scalar(select(func.max(Subtask.last_synced_at)))
        return result


# ──────────────────────────────────────────────
# Helpers puros (sin estado)
# ──────────────────────────────────────────────


def _delta_pct(current: float, previous: float | None) -> float | None:
    """Calcula variación porcentual. Retorna None si no hay valor anterior."""
    if previous is None or previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)
