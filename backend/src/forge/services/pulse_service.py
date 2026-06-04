"""PulseService — UC-16: Pulso Operativo (read-only, tiempo real).

REGLA CRÍTICA: Este servicio SOLO lee. Prohibido escribir en sp_adjustments,
leaderboard_snapshots o cualquier tabla de gamificación.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from forge.core.time_utils import business_seconds
from forge.db.models.area_wip_limit import AreaWipLimit
from forge.db.models.player import Player
from forge.db.models.subtask import Subtask
from forge.schemas.pulse import (
    AgingItem,
    BlockItem,
    DayMovementItem,
    PulseGlobals,
    PulseSnapshot,
    ReadyQueueItem,
    WipAreaCard,
)

# ── Constantes de negocio ─────────────────────────────────────────────────────

_BIZ_HOURS_PER_DAY = 8.0
_BLOCK_CRITICAL_HOURS = 8.0
_AGING_CRITICAL_DAYS = 5.0
_READY_QUEUE_TOP_N = 10
_DAY_MOVEMENTS_WINDOW_HOURS = 24

# Terminal: excluidos del Pulso
_TERMINAL = frozenset({"Done", "Backlog", "Cancelled"})

# WIP del dev: estados que se cuentan para semáforo por área
# Excluye In QA, Ready for QA, Ready (cola) y terminales
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

# Todos los estados operativos (no terminales)
_OPERATIONAL = frozenset(
    _WIP_STATUSES | {"In QA", "Ready for QA", "Ready"}
)


class PulseService:
    """Construye el snapshot del Pulso Operativo en tiempo real.

    Todas las operaciones son de lectura. Consulta la tabla subtasks directamente
    (con LEFT JOIN a players), enriquece con horas hábiles y devuelve PulseSnapshot.
    """

    def __init__(self, session: Session) -> None:
        self._s = session
        self._now = datetime.now(UTC)
        self._wip_limits: dict[str, int] = {}
        self._excluded_areas: set[str] = set()
        self._player_cache: dict[int, str] = {}

    # ── Punto de entrada ──────────────────────────────────────────────────────

    def get_pulse(
        self,
        areas: list[str] | None = None,
        project_code: str | None = None,
        player_id: int | None = None,
    ) -> PulseSnapshot:
        """Construye el PulseSnapshot completo con los filtros indicados."""
        self._load_wip_config()
        self._load_player_cache()
        rows = self._fetch_operational(areas, project_code, player_id)

        return PulseSnapshot(
            generated_at=self._now,
            filters_applied={
                "areas": areas,
                "project_code": project_code,
                "player_id": player_id,
            },
            globals=self._build_globals(rows),
            wip_by_area=self._build_wip_by_area(rows, areas),
            blocks=self._build_blocks(rows),
            day_movements=self._build_day_movements(rows),
            aging_critical=self._build_aging(rows),
            ready_queue=self._build_ready_queue(rows),
        )

    # ── Configuración WIP ─────────────────────────────────────────────────────

    def _load_wip_config(self) -> None:
        stmt = select(AreaWipLimit)
        for row in self._s.scalars(stmt).all():
            self._wip_limits[row.area] = row.wip_limit
            if row.exclude_from_wip:
                self._excluded_areas.add(row.area)

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

    # ── Helpers de nombre ─────────────────────────────────────────────────────

    def _name(self, player_id: int | None) -> str | None:
        if player_id is None:
            return None
        return self._player_cache.get(player_id)

    # ── Sección 1: Globals ────────────────────────────────────────────────────

    def _build_globals(self, rows: list[Subtask]) -> PulseGlobals:
        activas = sum(1 for r in rows if r.status in _WIP_STATUSES)
        bloqueadas = sum(1 for r in rows if r.status == "Blocked")
        en_espera = 0  # "Waiting" no existe en la BD — HUECO documentado
        cola_ready = sum(1 for r in rows if r.status == "Ready")

        aging_days = [
            self._aging_biz_days(r) for r in rows if r.status in _WIP_STATUSES
        ]
        aging_max = max(aging_days) if aging_days else 0.0

        return PulseGlobals(
            activas=activas,
            bloqueadas=bloqueadas,
            en_espera=en_espera,
            cola_ready=cola_ready,
            aging_max_dias_habiles=round(aging_max, 1),
        )

    # ── Sección 2: WIP por área ───────────────────────────────────────────────

    def _build_wip_by_area(
        self, rows: list[Subtask], requested_areas: list[str] | None
    ) -> list[WipAreaCard]:
        semaphore_areas = sorted(
            a for a in self._wip_limits if a not in self._excluded_areas
        )
        if requested_areas:
            semaphore_areas = [a for a in semaphore_areas if a in requested_areas]

        cards: list[WipAreaCard] = []
        for area in semaphore_areas:
            # Solo subtasks ASIGNADAS cuentan para WIP (sin asignee no pertenecen a nadie)
            area_rows = [
                r for r in rows
                if r.area == area and r.status in _WIP_STATUSES and r.assignee_player_id is not None
            ]
            wip_limit = self._wip_limits.get(area, 5)

            # WIP por dev individual
            wip_per_dev: dict[int, int] = {}
            for r in area_rows:
                pid = r.assignee_player_id
                if pid is not None:
                    wip_per_dev[pid] = wip_per_dev.get(pid, 0) + 1

            wip_actual = len(area_rows)
            max_wip_individual = max(wip_per_dev.values()) if wip_per_dev else 0
            devs_over_limit = sum(1 for w in wip_per_dev.values() if w > wip_limit)

            # Semáforo basado en WIP INDIVIDUAL máximo vs límite por dev
            pct = round(max_wip_individual / wip_limit * 100, 1) if wip_limit > 0 else 0.0
            semaforo = _semaforo(pct)

            cards.append(
                WipAreaCard(
                    area=area,
                    wip_actual=wip_actual,
                    wip_limit=wip_limit,
                    max_wip_individual=max_wip_individual,
                    devs_over_limit=devs_over_limit,
                    pct_utilization=pct,
                    semaforo=semaforo,
                    activas=[
                        {
                            "jira_key": r.jira_key,
                            "summary": r.summary,
                            "status": r.status,
                            "assignee_name": self._name(r.assignee_player_id),
                            "assignee_player_id": r.assignee_player_id,
                        }
                        for r in area_rows
                    ],
                    assignee_count=len(wip_per_dev),
                )
            )
        return cards

    # ── Sección 3: Bloqueos ───────────────────────────────────────────────────

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

    # ── Sección 4: Movimientos del día ────────────────────────────────────────

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

    # ── Sección 5: Aging crítico ──────────────────────────────────────────────

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

    # ── Sección 6: Cola Ready ─────────────────────────────────────────────────

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
        # Ordenar: priority real (Highest>High>Medium>Low>Lowest) + antigüedad en Ready
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
        # Asegurar datetime naive (business_seconds espera naive o aware, gestiona ambos)
        ref = last_change if isinstance(last_change, datetime) else datetime.combine(last_change, datetime.min.time())
        ref_naive = ref.replace(tzinfo=None) if ref.tzinfo else ref
        now_naive = self._now.replace(tzinfo=None)
        secs = business_seconds(ref_naive, now_naive)
        return secs / 3600.0

    def _aging_biz_days(self, row: Subtask) -> float:
        """Días hábiles desde created_at hasta ahora."""
        if row.created_at is None:
            return 0.0
        created = row.created_at
        created_naive = created.replace(tzinfo=None) if hasattr(created, "tzinfo") and created.tzinfo else created
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


def _semaforo(pct: float) -> str:
    if pct < 80:
        return "verde"
    if pct <= 100:
        return "amarillo"
    return "rojo"


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
