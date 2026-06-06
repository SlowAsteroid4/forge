"""PulseService — UC-16: Pulso Operativo (read-only, tiempo real).

REGLA CRÍTICA: Este servicio SOLO lee. Prohibido escribir en sp_adjustments,
leaderboard_snapshots o cualquier tabla de gamificación.

Rediseño WP-16:
  - CAMBIO 1: franja de contadores por estado en orden de flujo (Backlog→Done).
  - CAMBIO 2: cards por área (tareas activas → expand por estado → código+dueño),
    sin "WIP" ni semáforo de límite.
  - CAMBIO 3: drill-down por dev (sus tareas en progreso con estatus).
Conserva bloqueos, aging, movimientos del día y cola Ready.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from forge.core.time_utils import business_seconds
from forge.db.models.area_wip_limit import AreaWipLimit
from forge.db.models.player import Player
from forge.db.models.subtask import Subtask
from forge.schemas.pulse import (
    AgingItem,
    AreaCard,
    AreaStatusGroup,
    AreaTask,
    BlockItem,
    DayMovementItem,
    DevDrilldown,
    DevTask,
    FlowCounter,
    PulseSnapshot,
    ReadyQueueItem,
)

# ── Constantes de negocio ─────────────────────────────────────────────────────

_BIZ_HOURS_PER_DAY = 8.0
_BLOCK_CRITICAL_HOURS = 8.0
_AGING_CRITICAL_DAYS = 5.0
_READY_QUEUE_TOP_N = 10
_DAY_MOVEMENTS_WINDOW_HOURS = 24

# Terminal: excluidos del fetch operativo (cards, bloqueos, aging, drill-down).
_TERMINAL = frozenset({"Done", "Backlog", "Cancelled"})

# Cuentas-grupo agregadas (WP-15): no son devs individuales. Se etiquetan en UI.
# HUECO conocido: no hay columna que las marque; se detectan por display_name.
_AGGREGATE_TEAM_NAMES = frozenset({"Equipo de Producto"})

# Estados que cuentan para aging crítico (conservado de WP-08/09, sin cambios).
_WIP_STATUSES = frozenset(
    {
        "Active",
        "Implementation",
        "In Design",
        "In Progress",
        "In Review",
        "UI Implementation",
        "Blocked",
    }
)

# ── Mapeo de estado → zona de color (paleta JPDS WP-07b, por zona) ─────────────
# dev #60A5FA · review #C7D2FE · qa #FCA5A5 · blocked #F87171 · neutral #E5E7EB
_STATUS_ZONE: dict[str, str] = {
    "Backlog": "neutral",
    "Ready": "neutral",
    "In Progress": "dev",
    "Active": "dev",
    "Implementation": "dev",
    "In Design": "dev",
    "UI Implementation": "dev",
    "In Review": "review",
    "Ready for QA": "qa",
    "In QA": "qa",
    "Blocked": "blocked",
    "Done": "done",
}

# ── Franja de flujo (CAMBIO 1): (key, label, [statuses reales plegados], zona) ──
# AUDITORÍA WP-16: "Code Review" en la BD es "In Review". Los sub-estados de
# trabajo activo (Active/Implementation/In Design/UI Implementation) se pliegan
# en "In Progress" — el contador expone raw_statuses para que sea auditable.
_FLOW: list[tuple[str, str, list[str], str]] = [
    ("backlog", "Backlog", ["Backlog"], "neutral"),
    ("ready", "Ready", ["Ready"], "neutral"),
    (
        "in_progress",
        "In Progress",
        ["In Progress", "Active", "Implementation", "In Design", "UI Implementation"],
        "dev",
    ),
    ("in_review", "Code Review", ["In Review"], "review"),
    ("ready_for_qa", "Ready for QA", ["Ready for QA"], "qa"),
    ("in_qa", "In QA", ["In QA"], "qa"),
    ("done", "Done", ["Done"], "done"),
]

# Orden de flujo para ordenar grupos por estado dentro de una card de área.
_STATUS_FLOW_ORDER: dict[str, int] = {
    "Ready": 1,
    "In Progress": 2,
    "Active": 2,
    "Implementation": 2,
    "In Design": 2,
    "UI Implementation": 2,
    "In Review": 3,
    "Ready for QA": 4,
    "In QA": 5,
    "Blocked": 6,
}


def _zone(status: str) -> str:
    return _STATUS_ZONE.get(status, "neutral")


class PulseService:
    """Construye el snapshot del Pulso Operativo en tiempo real (read-only)."""

    def __init__(self, session: Session) -> None:
        self._s = session
        self._now = datetime.now(UTC)
        self._card_areas: list[str] = []
        self._player_cache: dict[int, str] = {}

    # ── Punto de entrada ──────────────────────────────────────────────────────

    def get_pulse(
        self,
        areas: list[str] | None = None,
        project_code: str | None = None,
        player_id: int | None = None,
    ) -> PulseSnapshot:
        """Construye el PulseSnapshot completo con los filtros indicados."""
        self._load_card_areas()
        self._load_player_cache()
        rows = self._fetch_operational(areas, project_code, player_id)

        return PulseSnapshot(
            generated_at=self._now,
            filters_applied={
                "areas": areas,
                "project_code": project_code,
                "player_id": player_id,
            },
            flow_counters=self._build_flow_counters(areas, project_code, player_id),
            area_cards=self._build_area_cards(rows, areas),
            blocks=self._build_blocks(rows),
            day_movements=self._build_day_movements(rows),
            aging_critical=self._build_aging(rows),
            ready_queue=self._build_ready_queue(rows),
        )

    def get_dev_drilldown(self, player_id: int) -> DevDrilldown:
        """CAMBIO 3: tareas en progreso de un dev (o cuenta-grupo) con estatus."""
        self._load_player_cache()
        player = self._s.get(Player, player_id)
        if player is None:
            return DevDrilldown(
                player_id=player_id,
                display_name=f"#{player_id}",
                is_aggregate_team=False,
                area=None,
                total=0,
                tasks=[],
            )

        rows = self._fetch_operational(None, None, player_id)
        tasks = [
            DevTask(
                jira_key=r.jira_key,
                summary=r.summary,
                status=r.status,
                zone=_zone(r.status),
                area=r.area or "—",
                dias_en_estado=round(
                    self._biz_hours_in_current_state(r) / _BIZ_HOURS_PER_DAY, 1
                ),
            )
            for r in rows
        ]
        tasks.sort(key=lambda t: t.dias_en_estado, reverse=True)

        return DevDrilldown(
            player_id=player_id,
            display_name=player.display_name,
            is_aggregate_team=player.display_name in _AGGREGATE_TEAM_NAMES,
            area=player.area,
            total=len(tasks),
            tasks=tasks,
        )

    # ── Carga de contexto ─────────────────────────────────────────────────────

    def _load_card_areas(self) -> None:
        """Áreas que reciben card: con límite configurado y no excluidas (QA/PO)."""
        stmt = select(AreaWipLimit).where(AreaWipLimit.exclude_from_wip.is_(False))
        self._card_areas = sorted(row.area for row in self._s.scalars(stmt).all())

    def _load_player_cache(self) -> None:
        stmt = select(Player.id, Player.display_name)
        for pid, name in self._s.execute(stmt):
            self._player_cache[pid] = name

    # ── Fetch principal ───────────────────────────────────────────────────────

    def _fetch_operational(
        self,
        areas: list[str] | None,
        project_code: str | None,
        player_id: int | None,
    ) -> list[Subtask]:
        """Subtasks operativas (no terminales) con filtros opcionales."""
        stmt = select(Subtask).where(Subtask.status.not_in(list(_TERMINAL)))

        if areas:
            stmt = stmt.where(Subtask.area.in_(areas))
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        if player_id is not None:
            stmt = stmt.where(Subtask.assignee_player_id == player_id)

        return list(self._s.scalars(stmt).all())

    def _count_by_status(
        self,
        areas: list[str] | None,
        project_code: str | None,
        player_id: int | None,
    ) -> dict[str, int]:
        """Conteo por status de TODAS las subtasks (incl. Backlog/Done) con filtros."""
        stmt = select(Subtask.status, func.count()).group_by(Subtask.status)
        if areas:
            stmt = stmt.where(Subtask.area.in_(areas))
        if project_code:
            stmt = stmt.where(Subtask.project_code == project_code)
        if player_id is not None:
            stmt = stmt.where(Subtask.assignee_player_id == player_id)
        result: dict[str, int] = {}
        for status, n in self._s.execute(stmt):
            result[status] = n
        return result

    # ── Helpers de nombre / agregado ──────────────────────────────────────────

    def _name(self, player_id: int | None) -> str | None:
        if player_id is None:
            return None
        return self._player_cache.get(player_id)

    def _is_aggregate(self, player_id: int | None) -> bool:
        name = self._name(player_id)
        return name in _AGGREGATE_TEAM_NAMES if name else False

    # ── CAMBIO 1: Franja de contadores por estado ─────────────────────────────

    def _build_flow_counters(
        self,
        areas: list[str] | None,
        project_code: str | None,
        player_id: int | None,
    ) -> list[FlowCounter]:
        counts = self._count_by_status(areas, project_code, player_id)
        counters: list[FlowCounter] = []
        for key, label, raw_statuses, zone in _FLOW:
            present = [s for s in raw_statuses if counts.get(s, 0) > 0]
            counters.append(
                FlowCounter(
                    key=key,
                    label=label,
                    count=sum(counts.get(s, 0) for s in raw_statuses),
                    raw_statuses=present or raw_statuses[:1],
                    zone=zone,
                )
            )
        return counters

    # ── CAMBIO 2: Cards por área ──────────────────────────────────────────────

    def _build_area_cards(
        self, rows: list[Subtask], requested_areas: list[str] | None
    ) -> list[AreaCard]:
        areas = self._card_areas
        if requested_areas:
            areas = [a for a in areas if a in requested_areas]

        cards: list[AreaCard] = []
        for area in areas:
            area_rows = [r for r in rows if r.area == area]

            by_status: dict[str, list[AreaTask]] = {}
            for r in area_rows:
                by_status.setdefault(r.status, []).append(
                    AreaTask(
                        jira_key=r.jira_key,
                        summary=r.summary,
                        status=r.status,
                        zone=_zone(r.status),
                        assignee_name=self._name(r.assignee_player_id),
                        assignee_player_id=r.assignee_player_id,
                        is_aggregate_team=self._is_aggregate(r.assignee_player_id),
                    )
                )

            groups = [
                AreaStatusGroup(
                    status=status,
                    zone=_zone(status),
                    count=len(tasks),
                    tasks=sorted(tasks, key=lambda t: t.jira_key),
                )
                for status, tasks in by_status.items()
            ]
            groups.sort(key=lambda g: _STATUS_FLOW_ORDER.get(g.status, 99))

            cards.append(
                AreaCard(area=area, total_active=len(area_rows), by_status=groups)
            )
        return cards

    # ── Sección 3: Bloqueos (conservado) ──────────────────────────────────────

    def _build_blocks(self, rows: list[Subtask]) -> list[BlockItem]:
        blocked = [r for r in rows if r.status == "Blocked"]
        items: list[BlockItem] = []
        for r in blocked:
            horas = self._biz_hours_in_current_state(r)
            items.append(
                BlockItem(
                    jira_key=r.jira_key,
                    summary=r.summary,
                    area=r.area,
                    assignee_name=self._name(r.assignee_player_id),
                    assignee_player_id=r.assignee_player_id,
                    horas_bloqueado=round(horas, 1),
                    es_critico=horas >= _BLOCK_CRITICAL_HOURS,
                    block_reason=None,  # HUECO: Jira no expone block_reason en changelog
                )
            )
        return sorted(items, key=lambda x: x.horas_bloqueado, reverse=True)

    # ── Sección 4: Movimientos del día (conservado) ───────────────────────────

    def _build_day_movements(self, rows: list[Subtask]) -> list[DayMovementItem]:
        cutoff = self._now - timedelta(hours=_DAY_MOVEMENTS_WINDOW_HOURS)
        movements: list[DayMovementItem] = []
        for r in rows:
            cl = _parse_changelog(r.raw_changelog)
            for hist in cl:
                ts = _parse_ts(hist.get("created", ""))
                if ts and ts.replace(tzinfo=UTC) >= cutoff:
                    for item in hist.get("items", []):
                        if item.get("field") == "status":
                            movements.append(
                                DayMovementItem(
                                    jira_key=r.jira_key,
                                    summary=r.summary,
                                    area=r.area,
                                    assignee_name=self._name(r.assignee_player_id),
                                    from_status=item.get("fromString", ""),
                                    to_status=item.get("toString", ""),
                                    moved_at=ts.replace(tzinfo=None),
                                )
                            )
        return sorted(movements, key=lambda m: m.moved_at, reverse=True)

    # ── Sección 5: Aging crítico (conservado) ─────────────────────────────────

    def _build_aging(self, rows: list[Subtask]) -> list[AgingItem]:
        active_rows = [r for r in rows if r.status in _WIP_STATUSES]
        critical: list[AgingItem] = []
        for r in active_rows:
            dias_en_estado = self._biz_hours_in_current_state(r) / _BIZ_HOURS_PER_DAY
            if dias_en_estado >= _AGING_CRITICAL_DAYS:
                edad_total = self._aging_biz_days(r)
                critical.append(
                    AgingItem(
                        jira_key=r.jira_key,
                        summary=r.summary,
                        area=r.area,
                        status=r.status,
                        assignee_name=self._name(r.assignee_player_id),
                        assignee_player_id=r.assignee_player_id,
                        dias_en_estado=round(dias_en_estado, 1),
                        edad_total_dias=round(edad_total, 1),
                    )
                )
        return sorted(critical, key=lambda x: x.dias_en_estado, reverse=True)

    # ── Sección 6: Cola Ready (conservado) ────────────────────────────────────

    def _build_ready_queue(self, rows: list[Subtask]) -> list[ReadyQueueItem]:
        ready = [r for r in rows if r.status == "Ready"]
        items: list[ReadyQueueItem] = []
        for r in ready:
            tiempo_en_ready = self._biz_hours_in_current_state(r)
            items.append(
                ReadyQueueItem(
                    jira_key=r.jira_key,
                    summary=r.summary,
                    area=r.area,
                    cp=r.cp,
                    assignee_name=self._name(r.assignee_player_id),
                    tiempo_en_ready_horas=round(tiempo_en_ready, 1),
                    priority=r.priority,
                )
            )
        items.sort(key=lambda x: (_priority_order(x.priority), -x.tiempo_en_ready_horas))
        return items[:_READY_QUEUE_TOP_N]

    # ── Helpers de tiempo ─────────────────────────────────────────────────────

    def _biz_hours_in_current_state(self, row: Subtask) -> float:
        """Horas hábiles desde el último cambio de estado hasta ahora."""
        last_change = _last_status_change_ts(row.raw_changelog)
        if last_change is None:
            last_change = row.updated_at  # fallback: updated_at como proxy
        if last_change is None:
            return 0.0
        ref = (
            last_change
            if isinstance(last_change, datetime)
            else datetime.combine(last_change, datetime.min.time())
        )
        ref_naive = ref.replace(tzinfo=None) if ref.tzinfo else ref
        now_naive = self._now.replace(tzinfo=None)
        secs = business_seconds(ref_naive, now_naive)
        return secs / 3600.0

    def _aging_biz_days(self, row: Subtask) -> float:
        """Días hábiles desde created_at hasta ahora."""
        if row.created_at is None:
            return 0.0
        created = row.created_at
        created_naive = (
            created.replace(tzinfo=None)
            if hasattr(created, "tzinfo") and created.tzinfo
            else created
        )
        now_naive = self._now.replace(tzinfo=None)
        secs = business_seconds(created_naive, now_naive)
        return secs / 3600.0 / _BIZ_HOURS_PER_DAY


# ── Helpers puros ─────────────────────────────────────────────────────────────


_PRIORITY_ORDER: dict[str, int] = {
    "Highest": 1,
    "High": 2,
    "Medium": 3,
    "Low": 4,
    "Lowest": 5,
}


def _priority_order(priority: str | None) -> int:
    """Orden numérico ascendente: Highest=1, sin prioridad=6."""
    return _PRIORITY_ORDER.get(priority or "", 6)


def _parse_changelog(raw: str | None) -> list[dict[str, Any]]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            histories: list[dict[str, Any]] = data.get("histories", [])
            return histories
        if isinstance(data, list):
            result: list[dict[str, Any]] = data
            return result
        return []
    except (json.JSONDecodeError, TypeError):
        return []


def _parse_ts(ts_str: str) -> datetime | None:
    if not ts_str:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None


def _last_status_change_ts(raw_changelog: str | None) -> datetime | None:
    """Timestamp del último cambio de status en el changelog de Jira."""
    histories = _parse_changelog(raw_changelog)
    # Jira ordena el changelog del más antiguo al más reciente; iteramos en reversa
    for hist in reversed(histories):
        for item in hist.get("items", []):
            if item.get("field") == "status":
                return _parse_ts(hist.get("created", ""))
    return None
