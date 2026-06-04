"""AnalyticsService — WP-07a: Flujo / Cuellos de botella (analíticas de equipo)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from forge.core.time_utils import business_hours
from forge.db.models.cycle import Cycle
from forge.db.models.player import Player
from forge.db.models.subtask import Subtask

_DONE = "Done"
_WINDOW_SIZE = 4
_CYCLE_BIZ_DAYS = 5  # Cada ciclo = Lun–Vie

# Áreas con subtasks (leaderboard)
_DEV_AREAS = frozenset({"BE", "FE", "DESIGN", "DB", "QA"})


class AnalyticsService:
    """Analíticas de flujo y cuellos de botella para Forge Ops.

    Todos los métodos son read-only; no hay side effects.
    Datos nulos/vacíos se devuelven como 0 / listas vacías (nunca levantan excepciones).
    """

    def __init__(self, session: Session) -> None:
        self._s = session

    # ──────────────────────────────────────────────────────────────
    # API pública
    # ──────────────────────────────────────────────────────────────

    def throughput_by_cycle(self, last_n: int = 8) -> list[dict[str, Any]]:
        """CP y subtasks Done por ciclo (serie temporal, N ciclos más recientes).

        Incluye ciclos activos y cerrados/archivados. Orden: más reciente primero.
        """
        cycles = (
            self._s.execute(
                select(Cycle)
                .where(Cycle.status.in_(["active", "closed", "archived"]))
                .order_by(Cycle.start_date.desc())
                .limit(last_n)
            )
            .scalars()
            .all()
        )

        result = []
        for cycle in cycles:
            done_count, total_cp = self._s.execute(
                select(
                    func.count(Subtask.jira_key),
                    func.coalesce(func.sum(Subtask.cp), 0),
                ).where(Subtask.cycle_id == cycle.id, Subtask.status == _DONE)
            ).one()

            result.append(
                {
                    "cycle_id": cycle.id,
                    "cycle_name": cycle.name,
                    "iso_year": cycle.iso_year,
                    "iso_week": cycle.iso_week,
                    "start_date": cycle.start_date.isoformat(),
                    "end_date": cycle.end_date.isoformat(),
                    "status": cycle.status,
                    "done_count": done_count,
                    "total_cp": int(total_cp),
                }
            )

        return result

    def cp_by_area(
        self,
        scope: str = "cycle",
        cycle_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """CP Done agrupado por área técnica.

        Args:
            scope: 'cycle' (ciclo activo/especificado) | 'window' (4 ciclos cerrados).
            cycle_id: ID del ciclo (solo aplica si scope='cycle'; None = activo).
        """
        cycle_ids = self._resolve_cycle_ids(scope, cycle_id)
        if not cycle_ids:
            return []

        rows = self._s.execute(
            select(
                Subtask.area,
                func.count(Subtask.jira_key).label("done_count"),
                func.coalesce(func.sum(Subtask.cp), 0).label("total_cp"),
            )
            .where(Subtask.cycle_id.in_(cycle_ids), Subtask.status == _DONE)
            .group_by(Subtask.area)
            .order_by(func.coalesce(func.sum(Subtask.cp), 0).desc())
        ).all()

        return [
            {
                "area": row.area,
                "done_count": row.done_count,
                "total_cp": int(row.total_cp),
            }
            for row in rows
        ]

    def cp_per_day_by_dev(self, scope: str = "cycle") -> list[dict[str, Any]]:
        """CP Done dividido por días hábiles del scope, por dev.

        Útil para comparar productividad normalizada entre devs con distinto tiempo activo.
        Solo devs con área en DEV_AREAS (excluye PO/PM).

        Args:
            scope: 'cycle' (ciclo activo) | 'window' (4 ciclos cerrados).
        """
        cycle_ids = self._resolve_cycle_ids(scope)
        if not cycle_ids:
            return []

        biz_days = len(cycle_ids) * _CYCLE_BIZ_DAYS

        rows = self._s.execute(
            select(
                Player.id,
                Player.display_name,
                Player.area,
                func.count(Subtask.jira_key).label("done_count"),
                func.coalesce(func.sum(Subtask.cp), 0).label("total_cp"),
            )
            .join(Player, Subtask.assignee_player_id == Player.id)
            .where(
                Subtask.cycle_id.in_(cycle_ids),
                Subtask.status == _DONE,
                Player.area.in_(_DEV_AREAS),
            )
            .group_by(Player.id)
            .order_by(func.coalesce(func.sum(Subtask.cp), 0).desc())
        ).all()

        return [
            {
                "player_id": row.id,
                "display_name": row.display_name,
                "area": row.area,
                "done_count": row.done_count,
                "total_cp": int(row.total_cp),
                "biz_days": biz_days,
                "cp_per_day": round(int(row.total_cp) / biz_days, 2) if biz_days else 0.0,
            }
            for row in rows
        ]

    def qa_first_pass_by_dev(self, scope: str = "historical") -> list[dict[str, Any]]:
        """Porcentaje de tareas que pasan QA en primer intento, por dev.

        ⚠️  Limitación de datos conocida (WP-07a): el ETL detecta fallo QA vía
        transición 'Testing'/'QA' → 'In Progress'/'To Do', pero los estados reales
        en Jira son 'In QA' y 'Ready for QA'. Hasta que el ETL se corrija, el campo
        `qa_first_pass` reporta 100% first-pass para todos los devs. Los valores se
        devuelven tal cual para que el frontend los muestre con advertencia.

        Solo devs con área en DEV_AREAS.

        Args:
            scope: 'cycle' | 'window' | 'historical'.
        """
        filters = [Subtask.status == _DONE, Subtask.qa_first_pass.is_not(None)]

        if scope in ("cycle", "window"):
            cycle_ids = self._resolve_cycle_ids(scope)
            if not cycle_ids:
                return []
            filters.append(Subtask.cycle_id.in_(cycle_ids))

        rows = self._s.execute(
            select(
                Player.id,
                Player.display_name,
                Player.area,
                func.count(Subtask.jira_key).label("total"),
                func.sum(
                    case((Subtask.qa_first_pass == True, 1), else_=0)  # noqa: E712
                ).label("passed"),
            )
            .join(Player, Subtask.assignee_player_id == Player.id)
            .where(*filters, Player.area.in_(_DEV_AREAS))
            .group_by(Player.id)
            .order_by(Player.display_name)
        ).all()

        result = []
        for row in rows:
            total = row.total or 0
            passed = int(row.passed or 0)
            result.append(
                {
                    "player_id": row.id,
                    "display_name": row.display_name,
                    "area": row.area,
                    "total": total,
                    "passed": passed,
                    "first_pass_pct": round(passed / total * 100, 1) if total else 0.0,
                    "data_caveat": "etl_status_mismatch",
                }
            )

        return result

    def time_in_status(
        self,
        group_by: str = "area",
        scope: str = "window",
    ) -> list[dict[str, Any]]:
        """Horas hábiles por bucket de estado, agrupado por área o dev.

        Ordena de mayor a menor tiempo total (el primero = mayor cuello de botella).

        Buckets disponibles (pre-computados en ETL):
        - dev_resp: tiempo en zona de responsabilidad del dev (Cycle - QA - Review)
        - qa: tiempo en estados Testing / In QA / Ready for QA
        - review: tiempo en In Review / Code Review
        - blocked: tiempo en Blocked / Bloqueado
        - waiting: tiempo en Waiting / Esperando

        Para detalle por estado Jira específico ('Ready for QA', 'Active', etc.),
        usa time_in_status_detail() — parsea raw_changelog y es más lento.

        Args:
            group_by: 'area' | 'player'.
            scope: 'window' (4 ciclos cerrados) | 'cycle' | 'historical'.
        """
        cycle_ids = self._resolve_cycle_ids(scope)
        if not cycle_ids and scope != "historical":
            return []

        filters = [Subtask.status == _DONE]
        if scope != "historical":
            filters.append(Subtask.cycle_id.in_(cycle_ids))

        if group_by == "area":
            return self._time_by_area(filters)
        return self._time_by_player(filters)

    def time_in_status_detail(
        self,
        group_by: str = "area",
        scope: str = "window",
    ) -> list[dict[str, Any]]:
        """Horas por estado Jira específico (parsea raw_changelog).

        Más lento que time_in_status() pero con granularidad por estado Jira real
        (ej. 'Ready for QA', 'In Design', 'UI Implementation').

        Solo incluye subtasks con raw_changelog no nulo.
        """
        cycle_ids = self._resolve_cycle_ids(scope)
        filters = [Subtask.status == _DONE, Subtask.raw_changelog.is_not(None)]
        if scope != "historical":
            if not cycle_ids:
                return []
            filters.append(Subtask.cycle_id.in_(cycle_ids))

        if group_by == "area":
            return self._detail_by_area(filters)
        return self._detail_by_player(filters)

    # ──────────────────────────────────────────────────────────────
    # Helpers internos
    # ──────────────────────────────────────────────────────────────

    def _resolve_cycle_ids(
        self,
        scope: str = "cycle",
        cycle_id: int | None = None,
    ) -> list[int]:
        """Devuelve la lista de IDs de ciclo para el scope dado."""
        if scope == "cycle":
            if cycle_id is not None:
                return [cycle_id]
            active = self._s.execute(
                select(Cycle.id).where(Cycle.status == "active")
            ).scalar_one_or_none()
            return [active] if active else []

        # window: 4 ciclos más recientes cerrados/archivados
        ids = (
            self._s.execute(
                select(Cycle.id)
                .where(Cycle.status.in_(["closed", "archived"]))
                .order_by(Cycle.start_date.desc())
                .limit(_WINDOW_SIZE)
            )
            .scalars()
            .all()
        )
        return list(ids)

    def _time_by_area(self, filters: list[Any]) -> list[dict[str, Any]]:
        rows = self._s.execute(
            select(
                Subtask.area,
                func.count(Subtask.jira_key).label("done_count"),
                func.coalesce(func.sum(Subtask.dev_resp_biz_hours), 0).label("dev_resp_h"),
                func.coalesce(func.sum(Subtask.qa_biz_hours), 0).label("qa_h"),
                func.coalesce(func.sum(Subtask.review_biz_hours), 0).label("review_h"),
                func.coalesce(func.sum(Subtask.blocked_biz_hours), 0).label("blocked_h"),
                func.coalesce(func.sum(Subtask.waiting_biz_hours), 0).label("waiting_h"),
            )
            .where(*filters)
            .group_by(Subtask.area)
        ).all()

        result = []
        for row in rows:
            total = row.dev_resp_h + row.qa_h + row.review_h + row.blocked_h + row.waiting_h
            result.append(
                {
                    "group_key": row.area,
                    "display_name": row.area,
                    "done_count": row.done_count,
                    "dev_resp_h": round(float(row.dev_resp_h), 2),
                    "qa_h": round(float(row.qa_h), 2),
                    "review_h": round(float(row.review_h), 2),
                    "blocked_h": round(float(row.blocked_h), 2),
                    "waiting_h": round(float(row.waiting_h), 2),
                    "total_h": round(float(total), 2),
                }
            )

        result.sort(key=lambda x: x["total_h"], reverse=True)
        return result

    def _time_by_player(self, filters: list[Any]) -> list[dict[str, Any]]:
        rows = self._s.execute(
            select(
                Player.id,
                Player.display_name,
                Player.area,
                func.count(Subtask.jira_key).label("done_count"),
                func.coalesce(func.sum(Subtask.dev_resp_biz_hours), 0).label("dev_resp_h"),
                func.coalesce(func.sum(Subtask.qa_biz_hours), 0).label("qa_h"),
                func.coalesce(func.sum(Subtask.review_biz_hours), 0).label("review_h"),
                func.coalesce(func.sum(Subtask.blocked_biz_hours), 0).label("blocked_h"),
                func.coalesce(func.sum(Subtask.waiting_biz_hours), 0).label("waiting_h"),
            )
            .join(Player, Subtask.assignee_player_id == Player.id)
            .where(*filters)
            .group_by(Player.id)
        ).all()

        result = []
        for row in rows:
            total = row.dev_resp_h + row.qa_h + row.review_h + row.blocked_h + row.waiting_h
            result.append(
                {
                    "group_key": str(row.id),
                    "display_name": row.display_name,
                    "area": row.area,
                    "done_count": row.done_count,
                    "dev_resp_h": round(float(row.dev_resp_h), 2),
                    "qa_h": round(float(row.qa_h), 2),
                    "review_h": round(float(row.review_h), 2),
                    "blocked_h": round(float(row.blocked_h), 2),
                    "waiting_h": round(float(row.waiting_h), 2),
                    "total_h": round(float(total), 2),
                }
            )

        result.sort(key=lambda x: x["total_h"], reverse=True)
        return result

    def _detail_by_area(self, filters: list[Any]) -> list[dict[str, Any]]:
        subtasks = (
            self._s.execute(
                select(Subtask.area, Subtask.raw_changelog).where(*filters)
            )
            .all()
        )

        area_hours: dict[str, dict[str, float]] = {}
        area_count: dict[str, int] = {}
        for row in subtasks:
            per_status = _parse_time_per_status(row.raw_changelog)
            bucket = area_hours.setdefault(row.area, {})
            area_count[row.area] = area_count.get(row.area, 0) + 1
            for status, hours in per_status.items():
                bucket[status] = bucket.get(status, 0.0) + hours

        return _format_detail_rows(area_hours, area_count, group_is_area=True)

    def _detail_by_player(self, filters: list[Any]) -> list[dict[str, Any]]:
        subtasks = (
            self._s.execute(
                select(
                    Player.id,
                    Player.display_name,
                    Player.area,
                    Subtask.raw_changelog,
                )
                .join(Player, Subtask.assignee_player_id == Player.id)
                .where(*filters)
            )
            .all()
        )

        player_meta: dict[str, tuple[str, str]] = {}
        player_hours: dict[str, dict[str, float]] = {}
        player_count: dict[str, int] = {}
        for row in subtasks:
            key = str(row.id)
            player_meta[key] = (row.display_name, row.area)
            per_status = _parse_time_per_status(row.raw_changelog)
            bucket = player_hours.setdefault(key, {})
            player_count[key] = player_count.get(key, 0) + 1
            for status, hours in per_status.items():
                bucket[status] = bucket.get(status, 0.0) + hours

        detail_rows = _format_detail_rows(player_hours, player_count, group_is_area=False)
        for entry in detail_rows:
            meta = player_meta.get(entry["group_key"], ("?", "?"))
            entry["display_name"] = meta[0]
            entry["area"] = meta[1]

        return detail_rows


# ──────────────────────────────────────────────────────────────
# Utilidades de changelog
# ──────────────────────────────────────────────────────────────

def _parse_dt(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _parse_time_per_status(raw_changelog_json: str | None) -> dict[str, float]:
    """Calcula horas hábiles por estado Jira parseando el raw_changelog.

    Devuelve un dict {status_name: business_hours}. Solo cubre los periodos
    entre transiciones de estado; el estado inicial (antes de la primera transición)
    no se mide (generalmente es 'Backlog' / 'To Do').
    """
    if not raw_changelog_json:
        return {}

    try:
        changelog = json.loads(raw_changelog_json)
        histories = changelog.get("histories", [])
    except (json.JSONDecodeError, AttributeError, TypeError):
        return {}

    # Extraer transiciones de estado en orden cronológico
    transitions: list[tuple[datetime, str]] = []
    for history in histories:
        ts = _parse_dt(history.get("created"))
        if ts is None:
            continue
        for item in history.get("items", []):
            if item.get("field") == "status":
                to_status = item.get("toString", "")
                if to_status:
                    transitions.append((ts, to_status))

    if not transitions:
        return {}

    transitions.sort(key=lambda x: x[0])

    result: dict[str, float] = {}
    for i in range(len(transitions) - 1):
        ts_start, status = transitions[i]
        ts_end = transitions[i + 1][0]
        try:
            hours = business_hours(ts_start, ts_end)
        except Exception:
            hours = 0.0
        if hours > 0:
            result[status] = result.get(status, 0.0) + hours

    return result


def _format_detail_rows(
    hours_map: dict[str, dict[str, float]],
    count_map: dict[str, int],
    group_is_area: bool,
) -> list[dict[str, Any]]:
    rows = []
    for key, status_hours in hours_map.items():
        total = sum(status_hours.values())
        entry: dict[str, Any] = {
            "group_key": key,
            "display_name": key if group_is_area else key,
            "done_count": count_map.get(key, 0),
            "total_h": round(total, 2),
            "by_status": {s: round(h, 2) for s, h in sorted(status_hours.items())},
        }
        rows.append(entry)

    rows.sort(key=lambda x: x["total_h"], reverse=True)
    return rows
