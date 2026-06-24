"""AnalyticsService — WP-07a: Flujo / Cuellos de botella (analíticas de equipo)."""

from __future__ import annotations

import json
from datetime import datetime
from statistics import median
from typing import Any

from sqlalchemy import ColumnElement, case, func, or_, select
from sqlalchemy.orm import Session

from forge.core.time_utils import business_hours
from forge.db.models.cycle import Cycle
from forge.db.models.epic import Epic
from forge.db.models.player import Player
from forge.db.models.story import Story
from forge.db.models.subtask import Subtask
from forge.services.canonical_status import BUCKET_TO_CANONICAL, canonical_of

# Estados crudos (tal como se almacenan) que representan cola de QA pendiente.
_QA_PENDING_STATUSES = ["In QA", "Ready for QA"]

_DONE = "Done"
_WINDOW_SIZE = 4
_CYCLE_BIZ_DAYS = 5  # Cada ciclo = Lun–Vie

# Áreas con subtasks (leaderboard)
_DEV_AREAS = frozenset({"BE", "FE", "DESIGN", "DB", "QA"})

# WP-17b — Apartado (sub-división dentro de YAP, codificada como prefijo [XXX]
# del summary de la épica). Las subtasks sin prefijo de apartado caen aquí, como
# categoría de primera clase (no se esconden): 36% del dato vive bajo épicas
# "Version Container" de release, que no llevan prefijo de área.
SIN_APARTADO = "Sin apartado"

# WP-21 — Red de seguridad para la derivación dinámica de apartados. NO es una
# lista que filtre lo que se muestra (los apartados se derivan de los datos): sirve
# para (a) ORDENAR los conocidos primero, en este orden, y (b) DETECTAR prefijos
# sospechosos (typos en el summary de una épica, p. ej. [YPAP] en vez de [YPAPP]).
# Un prefijo nuevo y legítimo que no esté aquí igual se muestra (no se esconde).
KNOWN_APARTADOS: tuple[str, ...] = ("YAPI", "YPAPP", "YPNX", "CAY", "PLD")

# Un apartado no-conocido con <= N subtasks y parecido a un conocido se marca como
# sospechoso de typo (para revisión), en vez de crear un "apartado fantasma" silencioso.
_TYPO_MAX_SUBTASKS = 2


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

    def throughput_by_cycle(
        self, last_n: int = 8, apartado: str | None = None
    ) -> list[dict[str, Any]]:
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

        ap = self._apartado_filter(apartado)
        ap_filter = [ap] if ap is not None else []
        result = []
        for cycle in cycles:
            done_count, total_cp = self._s.execute(
                select(
                    func.count(Subtask.jira_key),
                    func.coalesce(func.sum(Subtask.cp), 0),
                ).where(Subtask.cycle_id == cycle.id, Subtask.status == _DONE, *ap_filter)
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
        apartado: str | None = None,
    ) -> list[dict[str, Any]]:
        """CP Done agrupado por área técnica.

        Args:
            scope: 'cycle' (ciclo activo/especificado) | 'window' (4 ciclos cerrados).
            cycle_id: ID del ciclo (solo aplica si scope='cycle'; None = activo).
            apartado: filtra por apartado (incluye 'Sin apartado').
        """
        cycle_ids = self._resolve_cycle_ids(scope, cycle_id)
        if not cycle_ids:
            return []

        ap = self._apartado_filter(apartado)
        ap_filter = [ap] if ap is not None else []
        rows = self._s.execute(
            select(
                Subtask.area,
                func.count(Subtask.jira_key).label("done_count"),
                func.coalesce(func.sum(Subtask.cp), 0).label("total_cp"),
            )
            .where(Subtask.cycle_id.in_(cycle_ids), Subtask.status == _DONE, *ap_filter)
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

    def cp_per_day_by_dev(
        self, scope: str = "cycle", apartado: str | None = None
    ) -> list[dict[str, Any]]:
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

        ap = self._apartado_filter(apartado)
        ap_filter = [ap] if ap is not None else []
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
                *ap_filter,
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

        Solo devs con área en DEV_AREAS. Subtasks sin paso por QA (qa_first_pass=NULL)
        se excluyen del denominador.

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
        apartado: str | None = None,
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
        ap = self._apartado_filter(apartado)
        if ap is not None:
            filters.append(ap)

        if group_by == "area":
            return self._detail_by_area(filters)
        return self._detail_by_player(filters)

    # ──────────────────────────────────────────────────────────────
    # WP-17a: Quality, comparativas vs ciclo anterior, agrupación canónica
    # ──────────────────────────────────────────────────────────────

    def quality_summary(
        self, cycle_id: int | None = None, apartado: str | None = None
    ) -> dict[str, Any]:
        """Métricas de Quality del ciclo de referencia + delta vs ciclo anterior.

        Métricas (read-only, derivadas de buckets WP-07h sin tocarlos):
        - tested (PROBADAS): Done en el ciclo con paso por QA (qa_first_pass IS NOT NULL).
        - pending (POR PROBAR): subtasks del ciclo en cola de QA ahora (In QA / Ready for QA).
        - avg_qa_hours: promedio de qa_biz_hours (tiempo de Edgar/In QA) sobre las Done con QA.

        El "ciclo anterior" es el closed/archived inmediato previo. Si no existe → previous=None
        (la UI muestra "sin comparativa"; no se inventan 0%).
        """
        ref = self._resolve_reference_cycle(cycle_id)
        if ref is None:
            return {"reference_cycle": None, "previous_cycle": None,
                    "tested": _empty_metric(), "pending": _empty_metric(),
                    "avg_qa_hours": _empty_metric()}

        cur = self._quality_for_cycle(ref.id, apartado)
        prev_cycle = self._previous_closed_cycle(ref)
        prev = self._quality_for_cycle(prev_cycle.id, apartado) if prev_cycle else None

        return {
            "reference_cycle": _cycle_brief(ref),
            "previous_cycle": _cycle_brief(prev_cycle) if prev_cycle else None,
            "tested": _delta_metric(cur["tested"], prev["tested"] if prev else None),
            "pending": _delta_metric(cur["pending"], prev["pending"] if prev else None),
            "avg_qa_hours": _delta_metric(
                cur["avg_qa_hours"], prev["avg_qa_hours"] if prev else None
            ),
        }

    def qa_first_pass_vs_previous(
        self, cycle_id: int | None = None, apartado: str | None = None
    ) -> dict[str, Any]:
        """QA first-pass por dev en el ciclo de referencia vs el ciclo anterior.

        Devuelve por dev: pct actual, pct anterior (o None) y delta en puntos.
        Si no hay ciclo previo, previous queda None → "sin comparativa".
        """
        ref = self._resolve_reference_cycle(cycle_id)
        if ref is None:
            return {"reference_cycle": None, "previous_cycle": None, "devs": []}

        prev_cycle = self._previous_closed_cycle(ref)
        cur_map = self._qa_first_pass_for_cycle(ref.id, apartado)
        prev_map = self._qa_first_pass_for_cycle(prev_cycle.id, apartado) if prev_cycle else {}

        devs = []
        for pid, cur in sorted(cur_map.items(), key=lambda kv: -kv[1]["first_pass_pct"]):
            prev = prev_map.get(pid)
            prev_pct = prev["first_pass_pct"] if prev else None
            devs.append(
                {
                    "player_id": pid,
                    "display_name": cur["display_name"],
                    "area": cur["area"],
                    "total": cur["total"],
                    "passed": cur["passed"],
                    "first_pass_pct": cur["first_pass_pct"],
                    "previous_pct": prev_pct,
                    "delta_pts": (
                        round(cur["first_pass_pct"] - prev_pct, 1)
                        if prev_pct is not None
                        else None
                    ),
                }
            )

        return {
            "reference_cycle": _cycle_brief(ref),
            "previous_cycle": _cycle_brief(prev_cycle) if prev_cycle else None,
            "devs": devs,
        }

    def time_canonical(
        self,
        group_by: str = "area",
        scope: str = "window",
        area_filter: str | None = None,
        apartado: str | None = None,
    ) -> list[dict[str, Any]]:
        """Horas por estado CANÓNICO (Manifiesto JPDS), agrupado por área o dev.

        Re-etiqueta los buckets WP-07h a los estados canónicos para AGRUPAR/MOSTRAR
        (capa de display). NO cambia la atribución de tiempo: las horas son
        exactamente las de WP-07h (dev_resp/qa/review/blocked/waiting).

        Args:
            group_by: 'area' | 'player'.
            scope: 'window' | 'cycle' | 'historical'.
            area_filter: si se da (ej. 'DESIGN'), restringe a esa área — usado por
                la sección de Design (Jesús + Equipo de Producto, ambos DESIGN).
        """
        cycle_ids = self._resolve_cycle_ids(scope)
        if not cycle_ids and scope != "historical":
            return []

        filters: list[Any] = [Subtask.status == _DONE]
        if scope != "historical":
            filters.append(Subtask.cycle_id.in_(cycle_ids))
        if area_filter:
            filters.append(Subtask.area == area_filter)
        ap = self._apartado_filter(apartado)
        if ap is not None:
            filters.append(ap)

        base = self._time_by_area(filters) if group_by == "area" else self._time_by_player(filters)

        bucket_keys = {
            "In Progress": "dev_resp_h",
            "In Review": "review_h",
            "In QA": "qa_h",
            "Blocked": "blocked_h",
            "Waiting": "waiting_h",
        }
        # Sanity: el mapeo canónico declarado coincide con el de buckets.
        assert {v: k for k, v in bucket_keys.items()} == BUCKET_TO_CANONICAL

        out = []
        for r in base:
            by_canonical = {canon: round(float(r[bk]), 2) for canon, bk in bucket_keys.items()}
            out.append(
                {
                    "group_key": r["group_key"],
                    "display_name": r["display_name"],
                    "area": r.get("area", r["group_key"]),
                    "done_count": r["done_count"],
                    "by_canonical": by_canonical,
                    "total_h": r["total_h"],
                }
            )
        return out

    # ──────────────────────────────────────────────────────────────
    # WP-17b: cycle/lead time, filtro por apartado, métricas por dev
    # ──────────────────────────────────────────────────────────────

    def apartados(self) -> list[dict[str, Any]]:
        """Apartados derivados dinámicamente del prefijo [XXX] de las épicas + conteo.

        WP-21 — el universo de apartados se deriva de los prefijos que existen en las
        ÉPICAS (fuente canónica), no de qué subtasks ya hay. Así un apartado real cuyo
        trabajo aún no empieza (p. ej. [YAPI]/[CAY], con épicas pero 0 subtasks Done)
        aparece igual, con conteo 0 — antes desaparecía porque la lista se derivaba de
        los conteos de subtasks.

        Orden: conocidos (KNOWN_APARTADOS) primero en ese orden, luego otros legítimos
        (alfabético), y 'Sin apartado' al final si hay subtasks sin prefijo. Cada
        apartado trae `known` y `suspected_typo` (no se esconde nada; los sospechosos
        de typo solo se marcan para revisión).
        """
        # Universo canónico: todo prefijo [XXX] presente en alguna épica.
        epic_summaries = self._s.execute(select(Epic.summary)).scalars().all()
        epic_apartados = {ap for s in epic_summaries if (ap := _apartado_of_summary(s))}

        # Conteo de subtasks por apartado (vía story → epic). 'Sin apartado' incluido.
        smap = self._story_apartado_map()
        story_keys = self._s.execute(select(Subtask.parent_story_key)).scalars().all()
        counts: dict[str, int] = {}
        for sk in story_keys:
            ap = smap.get(sk, SIN_APARTADO) if sk else SIN_APARTADO
            counts[ap] = counts.get(ap, 0) + 1

        # Universo = prefijos de épica ∪ apartados con subtasks (red por si un prefijo
        # vino de la cadena pero su épica ya no está; no se pierde el dato).
        universe = (epic_apartados | set(counts)) - {SIN_APARTADO}

        known = [a for a in KNOWN_APARTADOS if a in universe]
        others = sorted(universe - set(KNOWN_APARTADOS))

        result: list[dict[str, Any]] = []
        for a in known + others:
            n = counts.get(a, 0)
            result.append(
                {
                    "apartado": a,
                    "subtask_count": n,
                    "known": a in KNOWN_APARTADOS,
                    "suspected_typo": _is_suspected_typo(a, n),
                }
            )
        if counts.get(SIN_APARTADO):
            result.append(
                {
                    "apartado": SIN_APARTADO,
                    "subtask_count": counts[SIN_APARTADO],
                    "known": True,
                    "suspected_typo": False,
                }
            )
        return result

    def dev_list(
        self, apartado: str | None = None, scope: str = "historical"
    ) -> list[dict[str, Any]]:
        """Devs con subtasks Done en el scope (para el selector de métricas por dev).

        Filtra por el mismo scope que las métricas (cycle/window/historical) para no
        listar devs sin datos en el horizonte activo. Orden: más activos primero.
        """
        filters: list[Any] = [Subtask.status == _DONE, Subtask.assignee_player_id.is_not(None)]
        if scope in ("cycle", "window"):
            cycle_ids = self._resolve_cycle_ids(scope)
            if not cycle_ids:
                return []
            filters.append(Subtask.cycle_id.in_(cycle_ids))
        ap = self._apartado_filter(apartado)
        if ap is not None:
            filters.append(ap)

        rows = self._s.execute(
            select(
                Player.id,
                Player.display_name,
                Player.area,
                func.count(Subtask.jira_key).label("done_count"),
            )
            .join(Player, Subtask.assignee_player_id == Player.id)
            .where(*filters)
            .group_by(Player.id)
            .order_by(func.count(Subtask.jira_key).desc(), Player.display_name)
        ).all()
        return [
            {
                "player_id": r.id,
                "display_name": r.display_name,
                "area": r.area,
                "done_count": r.done_count,
            }
            for r in rows
        ]

    def cycle_lead_time(
        self,
        grouping: str = "cycle",
        apartado: str | None = None,
        area: str | None = None,
    ) -> dict[str, Any]:
        """Cycle time (In Progress→Done) y Lead time (Backlog/created→Done) en horas hábiles.

        CYCLE = In Progress→Done recalculado canónicamente desde raw_changelog (el changelog
        tiene crudos 'UI'/'Implementation'/'En progreso'… que mapean a 'In Progress'). LEAD =
        Backlog/creación→Done reusando `lt_biz_hours` de WP-07h, porque la fecha de creación
        REAL de Jira no vive en raw_changelog y `created_at` de la BD es la fecha de import.
        Ninguno toca/escribe los buckets de WP-07h (read-only).

        Args:
            grouping: 'cycle' (por ciclo) | 'month' (por mes de done_at) | 'historical' (1 bucket).
            apartado: filtra por apartado (incluye 'Sin apartado').
            area: filtra por área técnica.
        """
        filters: list[Any] = [Subtask.status == _DONE, Subtask.raw_changelog.is_not(None)]
        if area:
            filters.append(Subtask.area == area)
        ap = self._apartado_filter(apartado)
        if ap is not None:
            filters.append(ap)

        rows = self._s.execute(
            select(
                Subtask.cycle_id,
                Subtask.done_at,
                Subtask.lt_biz_hours,
                Subtask.raw_changelog,
            ).where(*filters)
        ).all()

        # Acumula (cycle_h, lead_h) por clave de periodo.
        buckets: dict[str, list[tuple[float | None, float | None]]] = {}
        overall: list[tuple[float | None, float | None]] = []
        for r in rows:
            cyc_h = _canonical_cycle_hours(r.raw_changelog, r.done_at)
            lead_h = r.lt_biz_hours
            overall.append((cyc_h, lead_h))
            if grouping == "month":
                key = r.done_at.strftime("%Y-%m") if r.done_at else "sin-fecha"
            elif grouping == "historical":
                key = "historical"
            else:  # cycle
                key = str(r.cycle_id) if r.cycle_id is not None else "sin-ciclo"
            buckets.setdefault(key, []).append((cyc_h, lead_h))

        periods: list[dict[str, Any]] = [
            p
            for k, vals in buckets.items()
            if (p := self._period_stats(k, vals, grouping)) is not None
        ]
        periods.sort(key=lambda p: p["sort_key"])

        return {
            "grouping": grouping,
            "apartado": apartado,
            "area": area,
            "periods": periods,
            "overall": self._aggregate_stats(overall),
        }

    def dev_metrics(
        self,
        player_id: int,
        scope: str = "historical",
        apartado: str | None = None,
    ) -> dict[str, Any] | None:
        """Métricas promedio de un dev: tiempo por estado crudo (37) y canónico (9).

        - raw_states: horas hábiles promedio en cada estado crudo de Jira por el que
          pasaron sus subtasks Done (parseo de raw_changelog, como time_in_status_detail).
        - canonical_states: lo mismo agregado a los 9 canónicos vía CANONICAL_STATUS_MAP.
        - cycle/lead promedio, qa first-pass %, throughput (done_count).

        Funciona igual para 'Equipo de Producto' (cuenta-grupo, WP-15) → is_aggregate=True.
        """
        player = self._s.get(Player, player_id)
        if player is None:
            return None

        filters: list[Any] = [
            Subtask.status == _DONE,
            Subtask.assignee_player_id == player_id,
            Subtask.raw_changelog.is_not(None),
        ]
        if scope in ("cycle", "window"):
            cycle_ids = self._resolve_cycle_ids(scope)
            if not cycle_ids:
                return self._empty_dev_metrics(player, scope, apartado)
            filters.append(Subtask.cycle_id.in_(cycle_ids))
        ap = self._apartado_filter(apartado)
        if ap is not None:
            filters.append(ap)

        rows = self._s.execute(
            select(
                Subtask.done_at,
                Subtask.lt_biz_hours,
                Subtask.qa_first_pass,
                Subtask.raw_changelog,
            ).where(*filters)
        ).all()

        if not rows:
            return self._empty_dev_metrics(player, scope, apartado)

        # Tiempo por estado crudo (sum + n subtasks que pasaron por él) → promedio.
        raw_sum: dict[str, float] = {}
        raw_n: dict[str, int] = {}
        cycles: list[float] = []
        leads: list[float] = []
        qa_total = 0
        qa_passed = 0
        for r in rows:
            per_status = _parse_time_per_status(r.raw_changelog)
            for status, hours in per_status.items():
                raw_sum[status] = raw_sum.get(status, 0.0) + hours
                raw_n[status] = raw_n.get(status, 0) + 1
            cyc_h = _canonical_cycle_hours(r.raw_changelog, r.done_at)
            if cyc_h is not None:
                cycles.append(cyc_h)
            if r.lt_biz_hours is not None:
                leads.append(r.lt_biz_hours)
            if r.qa_first_pass is not None:
                qa_total += 1
                if r.qa_first_pass:
                    qa_passed += 1

        # Agregación canónica: sumar crudos por su canónico.
        canon_sum: dict[str, float] = {}
        canon_n: dict[str, int] = {}
        for status in raw_sum:
            canon = canonical_of(status)
            canon_sum[canon] = canon_sum.get(canon, 0.0) + raw_sum[status]
            canon_n[canon] = canon_n.get(canon, 0) + raw_n[status]

        raw_states = [
            {
                "status": s,
                "canonical": canonical_of(s),
                "avg_h": round(raw_sum[s] / raw_n[s], 2) if raw_n[s] else 0.0,
                "total_h": round(raw_sum[s], 2),
                "n": raw_n[s],
            }
            for s in sorted(raw_sum, key=lambda x: -raw_sum[x])
        ]
        canonical_states = [
            {
                "status": c,
                "avg_h": round(canon_sum[c] / canon_n[c], 2) if canon_n[c] else 0.0,
                "total_h": round(canon_sum[c], 2),
                "n": canon_n[c],
            }
            for c in sorted(canon_sum, key=lambda x: -canon_sum[x])
        ]

        return {
            "player_id": player.id,
            "display_name": player.display_name,
            "area": player.area,
            "is_aggregate": player.display_name == "Equipo de Producto",
            "scope": scope,
            "apartado": apartado,
            "done_count": len(rows),
            "cycle_avg_h": round(sum(cycles) / len(cycles), 2) if cycles else None,
            "lead_avg_h": round(sum(leads) / len(leads), 2) if leads else None,
            "qa_first_pass_pct": round(qa_passed / qa_total * 100, 1) if qa_total else None,
            "raw_states": raw_states,
            "canonical_states": canonical_states,
        }

    # ──────────────────────────────────────────────────────────────
    # Helpers internos
    # ──────────────────────────────────────────────────────────────

    def _story_apartado_map(self) -> dict[str, str]:
        """story_key → apartado (solo stories cuya épica tiene prefijo [XXX] de área)."""
        rows = self._s.execute(
            select(Story.jira_key, Epic.summary).join(
                Epic, Story.parent_epic_key == Epic.jira_key
            )
        ).all()
        out: dict[str, str] = {}
        for story_key, epic_summary in rows:
            ap = _apartado_of_summary(epic_summary)
            if ap:
                out[story_key] = ap
        return out

    def _apartado_filter(self, apartado: str | None) -> ColumnElement[bool] | None:
        """Filtro SQL de subtasks por apartado. None = sin filtro (todos los apartados).

        'Sin apartado' = subtasks sin story, o cuya story cuelga de una épica sin prefijo.
        """
        if not apartado:
            return None
        smap = self._story_apartado_map()
        with_apartado = list(smap.keys())

        if apartado == SIN_APARTADO:
            if not with_apartado:
                return None  # todo es "sin apartado" → sin filtro efectivo
            return or_(
                Subtask.parent_story_key.is_(None),
                Subtask.parent_story_key.notin_(with_apartado),
            )

        keys = [k for k, v in smap.items() if v == apartado]
        if not keys:
            return Subtask.parent_story_key.is_(None) & Subtask.parent_story_key.is_not(None)
        return Subtask.parent_story_key.in_(keys)

    def _period_stats(
        self, key: str, vals: list[tuple[float | None, float | None]], grouping: str
    ) -> dict[str, Any] | None:
        stats = self._aggregate_stats(vals)
        if stats["done_count"] == 0:
            return None
        label = key
        sort_key: Any = key
        cycle_id: int | None = None
        if grouping == "cycle" and key.isdigit():
            cycle_id = int(key)
            cyc = self._s.get(Cycle, cycle_id)
            if cyc is not None:
                label = cyc.name
                sort_key = cyc.start_date.isoformat()
        return {
            "key": key,
            "label": label,
            "cycle_id": cycle_id,
            "sort_key": sort_key,
            **stats,
        }

    @staticmethod
    def _aggregate_stats(vals: list[tuple[float | None, float | None]]) -> dict[str, Any]:
        cyc = [c for c, _ in vals if c is not None]
        lead = [ld for _, ld in vals if ld is not None]
        return {
            "done_count": len(vals),
            "cycle_avg_h": round(sum(cyc) / len(cyc), 2) if cyc else None,
            "cycle_median_h": round(median(cyc), 2) if cyc else None,
            "lead_avg_h": round(sum(lead) / len(lead), 2) if lead else None,
            "lead_median_h": round(median(lead), 2) if lead else None,
        }

    def _empty_dev_metrics(
        self, player: Player, scope: str, apartado: str | None
    ) -> dict[str, Any]:
        return {
            "player_id": player.id,
            "display_name": player.display_name,
            "area": player.area,
            "is_aggregate": player.display_name == "Equipo de Producto",
            "scope": scope,
            "apartado": apartado,
            "done_count": 0,
            "cycle_avg_h": None,
            "lead_avg_h": None,
            "qa_first_pass_pct": None,
            "raw_states": [],
            "canonical_states": [],
        }

    def _resolve_reference_cycle(self, cycle_id: int | None = None) -> Cycle | None:
        """Ciclo de referencia para Quality/comparativas.

        Prioridad: cycle_id explícito → ciclo activo (si tiene Done) → ciclo más
        reciente con Done>0. Devuelve None si no hay ningún ciclo con datos.
        """
        if cycle_id is not None:
            return self._s.get(Cycle, cycle_id)

        active = self._s.execute(
            select(Cycle).where(Cycle.status == "active").order_by(Cycle.start_date.desc())
        ).scalars().first()
        if active is not None:
            done = self._s.execute(
                select(func.count(Subtask.jira_key)).where(
                    Subtask.cycle_id == active.id, Subtask.status == _DONE
                )
            ).scalar_one()
            if done > 0:
                return active

        ref = self._s.execute(
            select(Cycle)
            .join(Subtask, Subtask.cycle_id == Cycle.id)
            .where(Subtask.status == _DONE)
            .group_by(Cycle.id)
            .order_by(Cycle.start_date.desc())
            .limit(1)
        ).scalars().first()
        return ref or active

    def _previous_closed_cycle(self, ref: Cycle) -> Cycle | None:
        """Ciclo closed/archived inmediato previo al de referencia (por fecha)."""
        return self._s.execute(
            select(Cycle)
            .where(
                Cycle.status.in_(["closed", "archived"]),
                Cycle.start_date < ref.start_date,
            )
            .order_by(Cycle.start_date.desc())
            .limit(1)
        ).scalars().first()

    def _quality_for_cycle(
        self, cycle_id: int, apartado: str | None = None
    ) -> dict[str, float]:
        ap = self._apartado_filter(apartado)
        ap_filter = [ap] if ap is not None else []
        tested = self._s.execute(
            select(func.count(Subtask.jira_key)).where(
                Subtask.cycle_id == cycle_id,
                Subtask.status == _DONE,
                Subtask.qa_first_pass.is_not(None),
                *ap_filter,
            )
        ).scalar_one()
        pending = self._s.execute(
            select(func.count(Subtask.jira_key)).where(
                Subtask.cycle_id == cycle_id,
                Subtask.status.in_(_QA_PENDING_STATUSES),
                *ap_filter,
            )
        ).scalar_one()
        avg_qa = self._s.execute(
            select(func.avg(Subtask.qa_biz_hours)).where(
                Subtask.cycle_id == cycle_id,
                Subtask.status == _DONE,
                Subtask.qa_biz_hours > 0,
                *ap_filter,
            )
        ).scalar_one()
        return {
            "tested": int(tested),
            "pending": int(pending),
            "avg_qa_hours": round(float(avg_qa), 2) if avg_qa is not None else 0.0,
        }

    def _qa_first_pass_for_cycle(
        self, cycle_id: int, apartado: str | None = None
    ) -> dict[int, dict[str, Any]]:
        ap = self._apartado_filter(apartado)
        ap_filter = [ap] if ap is not None else []
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
            .where(
                Subtask.cycle_id == cycle_id,
                Subtask.status == _DONE,
                Subtask.qa_first_pass.is_not(None),
                Player.area.in_(_DEV_AREAS),
                *ap_filter,
            )
            .group_by(Player.id)
        ).all()

        out: dict[int, dict[str, Any]] = {}
        for row in rows:
            total = row.total or 0
            passed = int(row.passed or 0)
            out[row.id] = {
                "display_name": row.display_name,
                "area": row.area,
                "total": total,
                "passed": passed,
                "first_pass_pct": round(passed / total * 100, 1) if total else 0.0,
            }
        return out

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
# Utilidades de comparativas (WP-17a)
# ──────────────────────────────────────────────────────────────

def _cycle_brief(cycle: Cycle | None) -> dict[str, Any] | None:
    if cycle is None:
        return None
    return {
        "cycle_id": cycle.id,
        "name": cycle.name,
        "iso_year": cycle.iso_year,
        "iso_week": cycle.iso_week,
        "status": cycle.status,
    }


def _delta_metric(current: float, previous: float | None) -> dict[str, Any]:
    """Métrica con comparativa vs ciclo anterior.

    previous=None → "sin comparativa" (delta_abs/delta_pct = None). delta_pct solo
    se calcula si previous > 0 (evita divisiones por cero o +inf falsos).
    """
    delta_abs = round(current - previous, 2) if previous is not None else None
    delta_pct: float | None = None
    if previous is not None and previous != 0:
        delta_pct = round((current - previous) / previous * 100, 1)
    return {
        "current": current,
        "previous": previous,
        "delta_abs": delta_abs,
        "delta_pct": delta_pct,
    }


def _empty_metric() -> dict[str, Any]:
    return {"current": 0, "previous": None, "delta_abs": None, "delta_pct": None}


# ──────────────────────────────────────────────────────────────
# Utilidades de changelog
# ──────────────────────────────────────────────────────────────

def _apartado_of_summary(summary: str | None) -> str | None:
    """Extrae el apartado (prefijo [XXX]) del summary de una épica.

    Devuelve None si no hay prefijo al inicio, o si el corchete es una versión
    numérica (ej. 'Version Container - [3.0]' → None, cae en 'Sin apartado').
    """
    if not summary:
        return None
    s = summary.strip()
    if not s.startswith("[") or "]" not in s:
        return None
    inner = s[1 : s.index("]")].strip().upper()
    # Excluir versiones tipo [2.1]/[3.0]: un apartado de área no empieza por dígito.
    if not inner or inner[0].isdigit():
        return None
    return inner


def _is_suspected_typo(apartado: str, subtask_count: int) -> bool:
    """Marca un apartado como posible typo del summary de una épica.

    Heurística (WP-21): no es conocido, tiene poco volumen (<= _TYPO_MAX_SUBTASKS)
    y se parece a uno conocido (substring o distancia de edición 1, p. ej. 'YPAP'
    vs 'YPAPP'). No lo esconde: lo separa para revisión. Un apartado nuevo legítimo
    (volumen real o sin parecido a un conocido) no se marca.
    """
    if apartado in KNOWN_APARTADOS or apartado == SIN_APARTADO:
        return False
    if subtask_count > _TYPO_MAX_SUBTASKS:
        return False
    return any(_looks_similar(apartado, k) for k in KNOWN_APARTADOS)


def _looks_similar(a: str, b: str) -> bool:
    """True si a y b se parecen: uno contenido en el otro, o distancia de edición ≤ 1."""
    if a == b:
        return False
    if a in b or b in a:
        return True
    return _edit_distance_le1(a, b)


def _edit_distance_le1(a: str, b: str) -> bool:
    """¿La distancia de edición (Levenshtein) entre a y b es ≤ 1?"""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:  # una sola sustitución permitida
        return sum(x != y for x, y in zip(a, b)) <= 1
    # longitudes difieren en 1: ¿una sola inserción/eliminación?
    shorter, longer = (a, b) if la < lb else (b, a)
    i = j = 0
    skipped = False
    while i < len(shorter) and j < len(longer):
        if shorter[i] == longer[j]:
            i += 1
            j += 1
        elif skipped:
            return False
        else:
            skipped = True
            j += 1
    return True


def _canonical_cycle_hours(
    raw_changelog_json: str | None,
    done_at: datetime | None,
) -> float | None:
    """Cycle Time (In Progress→Done) en horas hábiles, detectado vía canónico.

    Detecta la PRIMERA transición a un estado crudo que mapea a 'In Progress' canónico
    ('UI', 'Implementation', 'En progreso'…) y la ÚLTIMA a 'Done' canónico. Si falta un
    extremo → None (no se inventa).

    NOTA — el Lead Time (Backlog/creación→Done) NO se calcula aquí: la fecha de creación
    real de Jira NO vive en raw_changelog (solo histories de cambios) y la columna
    `created_at` de la BD es la fecha de IMPORT, no la de creación. El lead real lo capturó
    WP-07h en `lt_biz_hours` al sincronizar (fields.created → done). Por eso cycle_lead_time
    recalcula el cycle canónicamente pero reutiliza `lt_biz_hours` para el lead.
    """
    if not raw_changelog_json:
        return None
    try:
        histories = json.loads(raw_changelog_json).get("histories", [])
    except (json.JSONDecodeError, AttributeError, TypeError):
        return None

    # Las histories de Jira NO vienen garantizadas en orden cronológico → recolectar
    # todas las transiciones de estado y ordenar por timestamp antes de elegir extremos.
    transitions: list[tuple[datetime, str]] = []
    for history in histories:
        ts = _parse_dt(history.get("created"))
        if ts is None:
            continue
        for item in history.get("items", []):
            if item.get("field") == "status":
                transitions.append((ts, canonical_of(item.get("toString", ""))))
    transitions.sort(key=lambda x: x[0])

    # Primer In Progress canónico (inicio del trabajo) y último Done canónico (cierre).
    first_in_progress = next((ts for ts, c in transitions if c == "In Progress"), None)
    last_done = next((ts for ts, c in reversed(transitions) if c == "Done"), None)

    done_end = last_done or done_at
    if first_in_progress is None or done_end is None:
        return None
    try:
        return business_hours(first_in_progress, done_end)
    except Exception:
        return None


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
