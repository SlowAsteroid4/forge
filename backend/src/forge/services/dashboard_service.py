"""DashboardService — UC-02: Dashboard general del sprint en curso."""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError
from forge.db.models.player import Player
from forge.db.models.project import Project
from forge.db.models.sprint import Sprint
from forge.db.models.subtask import Subtask
from forge.schemas.dashboard import (
    AlertItem,
    AreaProgress,
    DashboardResponse,
    KPICards,
    KPIValue,
    PlayerStatus,
    ProjectSummary,
    SprintHeader,
    SprintSummary,
)

# ──────────────────────────────────────────────
# Constantes de negocio
# ──────────────────────────────────────────────

_DONE = "Done"
_TERMINAL = frozenset({"Done", "Cancelled"})
_BLOCKED = frozenset({"Blocked", "Waiting"})
_LEADERBOARD_AREAS = ["BE", "FE", "DESIGN", "DB", "QA"]

# Umbral de WIP por área (CU-02)
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
    """Calcula todos los datos del dashboard de sprint.

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
        sprint_id: int | None = None,
    ) -> DashboardResponse:
        """Construye la respuesta completa del dashboard.

        Args:
            project_code: Filtro de proyecto (None = todos).
            sprint_id:    Sprint específico (None = sprint activo).
        """
        sprint = self._get_sprint(sprint_id)
        available_projects = self._get_available_projects()
        available_sprints = self._get_available_sprints()

        if sprint is None:
            return DashboardResponse(
                no_sprint_message="No hay un sprint activo. Crea uno en la sección de configuración.",
                available_projects=available_projects,
                available_sprints=available_sprints,
            )

        prev_sprint = self._get_previous_sprint(sprint)

        return DashboardResponse(
            sprint=self._build_sprint_header(sprint),
            kpis=self._build_kpis(sprint, project_code, prev_sprint),
            area_progress=self._build_area_progress(sprint, project_code),
            player_status=self._build_player_status(sprint, project_code),
            alerts=self._build_alerts(sprint, project_code),
            available_projects=available_projects,
            available_sprints=available_sprints,
            last_synced_at=self._get_last_sync(sprint.id, project_code),
        )

    # ──────────────────────────────────────────
    # Sprint helpers
    # ──────────────────────────────────────────

    def _get_sprint(self, sprint_id: int | None) -> Sprint | None:
        """Retorna el sprint solicitado o el activo si sprint_id es None."""
        if sprint_id is not None:
            sprint = self._s.get(Sprint, sprint_id)
            if sprint is None:
                raise NotFoundError(f"Sprint {sprint_id} no encontrado")
            return sprint
        # Sprint activo = no cerrado, fechas cubren hoy
        today = date.today()
        stmt = (
            select(Sprint)
            .where(Sprint.is_closed.is_(False))
            .where(Sprint.start_date <= today)
            .where(Sprint.end_date >= today)
            .order_by(Sprint.start_date.desc())
            .limit(1)
        )
        return self._s.scalars(stmt).first()

    def _get_previous_sprint(self, current: Sprint) -> Sprint | None:
        """Sprint inmediatamente anterior al actual, por fecha de fin."""
        stmt = (
            select(Sprint)
            .where(Sprint.end_date < current.start_date)
            .order_by(Sprint.end_date.desc())
            .limit(1)
        )
        return self._s.scalars(stmt).first()

    def _build_sprint_header(self, sprint: Sprint) -> SprintHeader:
        today = date.today()
        start = sprint.start_date
        end = sprint.end_date
        days_total = max((end - start).days + 1, 1)
        days_elapsed = min(max((today - start).days + 1, 0), days_total)
        return SprintHeader(
            id=sprint.id,
            name=sprint.name,
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
        sprint: Sprint,
        project_code: str | None,
        prev_sprint: Sprint | None,
    ) -> KPICards:
        cp_done_current = self._cp_done(sprint.id, project_code)
        cp_done_prev = self._cp_done(prev_sprint.id, project_code) if prev_sprint else None
        delta = _delta_pct(cp_done_current, cp_done_prev)

        return KPICards(
            cp_done=KPIValue(
                value=cp_done_current,
                previous_value=cp_done_prev,
                delta_pct=delta,
            ),
            cp_pending=self._cp_pending(sprint.id, project_code),
            sp_total=self._sp_total(sprint.id, project_code),
            bugs_derived=self._bugs_derived(sprint.id, project_code),
        )

    def _cp_done(self, sprint_id: int, project_code: str | None) -> float:
        stmt = (
            select(func.coalesce(func.sum(Subtask.cp), 0))
            .where(Subtask.sprint_id == sprint_id)
            .where(Subtask.status == _DONE)
            .where(Subtask.cp.is_not(None))
        )
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        return float(self._s.scalar(stmt) or 0)

    def _cp_pending(self, sprint_id: int, project_code: str | None) -> float:
        stmt = (
            select(func.coalesce(func.sum(Subtask.cp), 0))
            .where(Subtask.sprint_id == sprint_id)
            .where(Subtask.status.not_in(list(_TERMINAL)))
            .where(Subtask.cp.is_not(None))
        )
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        return float(self._s.scalar(stmt) or 0)

    def _sp_total(self, sprint_id: int, project_code: str | None) -> float:
        stmt = (
            select(func.coalesce(func.sum(Subtask.sp_final), 0))
            .where(Subtask.sprint_id == sprint_id)
            .where(Subtask.status == _DONE)
            .where(Subtask.sp_final.is_not(None))
        )
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        return float(self._s.scalar(stmt) or 0)

    def _bugs_derived(self, sprint_id: int, project_code: str | None) -> int:
        stmt = (
            select(func.count())
            .select_from(Subtask)
            .where(Subtask.sprint_id == sprint_id)
            .where(Subtask.issue_type == "Bug")
        )
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        return int(self._s.scalar(stmt) or 0)

    # ──────────────────────────────────────────
    # Progreso por área
    # ──────────────────────────────────────────

    def _build_area_progress(
        self,
        sprint: Sprint,
        project_code: str | None,
    ) -> list[AreaProgress]:
        result = []
        for area in _LEADERBOARD_AREAS:
            cp_done = self._area_cp_done(sprint.id, area, project_code)
            cp_total = self._area_cp_total(sprint.id, area, project_code)
            active_devs = self._area_active_devs(sprint.id, area, project_code)
            has_bottleneck = self._area_has_wip_bottleneck(sprint.id, area, project_code)

            result.append(
                AreaProgress(
                    area=area,
                    cp_done=cp_done,
                    cp_total=cp_total,
                    progress_pct=round(cp_done / cp_total * 100, 1) if cp_total > 0 else 0.0,
                    active_devs=active_devs,
                    has_wip_bottleneck=has_bottleneck,
                )
            )
        return result

    def _area_cp_done(self, sprint_id: int, area: str, project_code: str | None) -> float:
        stmt = (
            select(func.coalesce(func.sum(Subtask.cp), 0))
            .where(Subtask.sprint_id == sprint_id, Subtask.area == area, Subtask.status == _DONE)
            .where(Subtask.cp.is_not(None))
        )
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        return float(self._s.scalar(stmt) or 0)

    def _area_cp_total(self, sprint_id: int, area: str, project_code: str | None) -> float:
        stmt = (
            select(func.coalesce(func.sum(Subtask.cp), 0))
            .where(Subtask.sprint_id == sprint_id, Subtask.area == area)
            .where(Subtask.status != "Cancelled")
            .where(Subtask.cp.is_not(None))
        )
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        return float(self._s.scalar(stmt) or 0)

    def _area_active_devs(self, sprint_id: int, area: str, project_code: str | None) -> int:
        stmt = (
            select(func.count(Subtask.assignee_player_id.distinct()))
            .where(
                Subtask.sprint_id == sprint_id,
                Subtask.area == area,
                Subtask.status.not_in(list(_TERMINAL)),
                Subtask.assignee_player_id.is_not(None),
            )
        )
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        return int(self._s.scalar(stmt) or 0)

    def _area_has_wip_bottleneck(
        self, sprint_id: int, area: str, project_code: str | None
    ) -> bool:
        threshold = _WIP_THRESHOLDS.get(area, _DEFAULT_WIP)
        # Cuenta WIP activo por assignee en el área
        inner = (
            select(
                Subtask.assignee_player_id,
                func.count().label("wip"),
            )
            .where(
                Subtask.sprint_id == sprint_id,
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
        sprint: Sprint,
        project_code: str | None,
    ) -> list[PlayerStatus]:
        # IDs de players con subtasks en el sprint
        id_stmt = select(Subtask.assignee_player_id.distinct()).where(
            Subtask.sprint_id == sprint.id,
            Subtask.assignee_player_id.is_not(None),
        )
        if project_code:
            id_stmt = id_stmt.where(Subtask.project_code == project_code)
        player_ids: list[int] = [r[0] for r in self._s.execute(id_stmt)]

        result: list[PlayerStatus] = []
        for pid in player_ids:
            player = self._s.get(Player, pid)
            if player is None or not player.is_active:
                continue

            active_count = self._player_active_count(sprint.id, pid, project_code)
            done_count = self._player_done_count(sprint.id, pid, project_code)
            sp_total = self._player_sp(sprint.id, pid, project_code)
            status = self._player_status_label(sprint.id, pid, player.area, active_count, project_code)

            result.append(
                PlayerStatus(
                    player_id=player.id,
                    display_name=player.display_name,
                    area=player.area,
                    avatar_code=player.avatar_code,
                    active_subtasks=active_count,
                    done_subtasks=done_count,
                    sp_sprint=sp_total,
                    status=status,
                )
            )

        return sorted(result, key=lambda p: p.sp_sprint, reverse=True)

    def _player_active_count(
        self, sprint_id: int, player_id: int, project_code: str | None
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Subtask)
            .where(
                Subtask.sprint_id == sprint_id,
                Subtask.assignee_player_id == player_id,
                Subtask.status.not_in(list(_TERMINAL)),
            )
        )
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        return int(self._s.scalar(stmt) or 0)

    def _player_done_count(
        self, sprint_id: int, player_id: int, project_code: str | None
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Subtask)
            .where(
                Subtask.sprint_id == sprint_id,
                Subtask.assignee_player_id == player_id,
                Subtask.status == _DONE,
            )
        )
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        return int(self._s.scalar(stmt) or 0)

    def _player_sp(self, sprint_id: int, player_id: int, project_code: str | None) -> float:
        stmt = (
            select(func.coalesce(func.sum(Subtask.sp_final), 0))
            .where(
                Subtask.sprint_id == sprint_id,
                Subtask.assignee_player_id == player_id,
                Subtask.status == _DONE,
                Subtask.sp_final.is_not(None),
            )
        )
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        return float(self._s.scalar(stmt) or 0)

    def _player_status_label(
        self,
        sprint_id: int,
        player_id: int,
        area: str,
        active_count: int,
        project_code: str | None,
    ) -> str:
        if active_count == 0:
            return "inactive"

        # Cuántas de las activas están bloqueadas
        blocked_stmt = (
            select(func.count())
            .select_from(Subtask)
            .where(
                Subtask.sprint_id == sprint_id,
                Subtask.assignee_player_id == player_id,
                Subtask.status.in_(list(_BLOCKED)),
            )
        )
        if project_code:
            blocked_stmt = blocked_stmt.where(Subtask.project_code == project_code)
        blocked_count = int(self._s.scalar(blocked_stmt) or 0)

        if blocked_count >= active_count:
            return "blocked"

        threshold = _WIP_THRESHOLDS.get(area, _DEFAULT_WIP)
        if active_count > threshold:
            return "wip_high"

        return "productive"

    # ──────────────────────────────────────────
    # Alertas
    # ──────────────────────────────────────────

    def _build_alerts(
        self,
        sprint: Sprint,
        project_code: str | None,
    ) -> list[AlertItem]:
        alerts: list[AlertItem] = []
        alerts.extend(self._alerts_abandoned(sprint, project_code))
        alerts.extend(self._alerts_waiting_long(sprint, project_code))
        alerts.extend(self._alerts_cp_pending(sprint, project_code))
        alerts.extend(self._alerts_wip_exceeded(sprint, project_code))
        return alerts

    def _alerts_abandoned(self, sprint: Sprint, project_code: str | None) -> list[AlertItem]:
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=_ABANDONED_DAYS)
        stmt = (
            select(Subtask.jira_key, Subtask.assignee_player_id)
            .where(
                Subtask.sprint_id == sprint.id,
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

    def _alerts_waiting_long(self, sprint: Sprint, project_code: str | None) -> list[AlertItem]:
        """Subtasks bloqueadas/en espera con >18h hábiles acumuladas."""
        stmt = (
            select(Subtask.jira_key, Subtask.assignee_player_id)
            .where(
                Subtask.sprint_id == sprint.id,
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

    def _alerts_cp_pending(self, sprint: Sprint, project_code: str | None) -> list[AlertItem]:
        """L/XL sin CP aprobado."""
        stmt = (
            select(Subtask.jira_key, Subtask.assignee_player_id)
            .where(
                Subtask.sprint_id == sprint.id,
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

    def _alerts_wip_exceeded(self, sprint: Sprint, project_code: str | None) -> list[AlertItem]:
        """Devs que superan su umbral de WIP."""
        alerts: list[AlertItem] = []
        for area in _LEADERBOARD_AREAS:
            threshold = _WIP_THRESHOLDS.get(area, _DEFAULT_WIP)
            wip_stmt = (
                select(
                    Subtask.assignee_player_id,
                    func.count().label("wip"),
                )
                .where(
                    Subtask.sprint_id == sprint.id,
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

    def _get_available_sprints(self) -> list[SprintSummary]:
        stmt = select(Sprint).order_by(Sprint.start_date.desc())
        sprints = self._s.scalars(stmt).all()
        return [
            SprintSummary(
                id=s.id,
                name=s.name,
                start_date=s.start_date,
                end_date=s.end_date,
                is_closed=s.is_closed,
            )
            for s in sprints
        ]

    def _get_last_sync(self, sprint_id: int, project_code: str | None) -> datetime | None:
        """Max(last_synced_at) del sprint. Si no hay datos, devuelve el global."""
        stmt = select(func.max(Subtask.last_synced_at)).where(Subtask.sprint_id == sprint_id)
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        result = self._s.scalar(stmt)
        if result is None:
            # Fallback: max global (útil cuando las subtasks no tienen sprint asignado)
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
