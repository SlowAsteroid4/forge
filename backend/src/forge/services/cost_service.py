"""CostService — UC-08: Costos por área (read-only)."""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from forge.db.models.player import Player
from forge.db.models.subtask import Subtask

_DONE = "Done"

# Áreas que participan en leaderboard / producen CP.
# PM y PO NO producen CP, pero pueden tener costo → caso div/0 legítimo.
_ALL_AREAS = ("BE", "FE", "DESIGN", "DB", "QA", "PO", "PM")


# ──────────────────────────────────────────────────────────────
# Dataclasses internos (resultados intermedios)
# ──────────────────────────────────────────────────────────────


@dataclass
class PlayerCost:
    player_id: int
    display_name: str
    area: str
    employment_type: str
    cp_total: int
    sp_total: float
    done_subtasks: int
    cost_total: float | None
    cost_per_cp: float | None
    cost_per_sp: float | None
    cost_not_captured: bool
    no_production: bool   # tiene costo pero 0 CP → div/0
    cost_note: str | None


@dataclass
class AreaCost:
    area: str
    players_active: int
    cp_total: int
    sp_total: float
    done_subtasks: int
    cost_total: float | None
    cost_per_cp: float | None
    cost_per_sp: float | None
    delta_pct: float | None
    players: list[PlayerCost] = field(default_factory=list)


@dataclass
class IntExtComparison:
    area: str
    int_cost_per_cp: float | None
    ext_cost_per_cp: float | None
    int_players: int
    ext_players: int
    multiplier: float | None   # ext / int
    insight: str               # calculado, nunca hardcodeado


@dataclass
class EvolutionPoint:
    period_label: str          # "2026-01"
    period_start: date
    period_end: date
    cp_total: int
    cost_total: float | None
    cost_per_cp: float | None


# ──────────────────────────────────────────────────────────────
# Guard de permisos placeholder
# TODO(UC-09): conectar al sistema de auth real.
#   - Debe permitir: Admin, Owner, Director.
#   - Debe rechazar con HTTP 403: Tech Lead, Player.
# ──────────────────────────────────────────────────────────────


def require_cost_access(role: str = "admin") -> bool:
    """Placeholder: hoy deja pasar a todos.

    TODO(UC-09): reemplazar con validación real de JWT/session.
    """
    return True


# ──────────────────────────────────────────────────────────────
# Helpers de periodo
# ──────────────────────────────────────────────────────────────


def resolve_period(
    period: str,
    custom_start: date | None = None,
    custom_end: date | None = None,
) -> tuple[date, date]:
    """Mapea un selector de periodo a (start_date_inclusive, end_date_exclusive)."""
    today = date.today()

    if period == "q_current":
        q = (today.month - 1) // 3
        start = date(today.year, q * 3 + 1, 1)
        end_month = q * 3 + 3
        end = date(today.year, end_month, calendar.monthrange(today.year, end_month)[1]) + timedelta(days=1)
        return start, end

    if period == "q_prev":
        q = (today.month - 1) // 3
        if q == 0:
            prev_year = today.year - 1
            start = date(prev_year, 10, 1)
            end = date(today.year, 1, 1)
        else:
            start = date(today.year, (q - 1) * 3 + 1, 1)
            end = date(today.year, q * 3 + 1, 1)
        return start, end

    if period == "last_12m":
        # últimos 12 meses completos (no incluye el mes actual en curso)
        if today.month == 1:
            end = date(today.year, 1, 1)
            start = date(today.year - 1, 1, 1)
        else:
            end = date(today.year, today.month, 1)
            start_month = today.month  # mismo mes del año anterior
            start = date(today.year - 1, start_month, 1)
        return start, end

    if period == "y_current":
        return date(today.year, 1, 1), date(today.year + 1, 1, 1)

    if period == "custom":
        if custom_start is None or custom_end is None:
            raise ValueError("custom_start y custom_end son requeridos para period='custom'")
        return custom_start, custom_end

    # fallback: trimestre actual
    return resolve_period("q_current")


def _months_in_period(start: date, end: date) -> list[tuple[date, date]]:
    """Lista de (month_start, month_end_exclusive) que se solapan con el periodo."""
    months: list[tuple[date, date]] = []
    cur = date(start.year, start.month, 1)
    while cur < end:
        _, days_in = calendar.monthrange(cur.year, cur.month)
        m_start = cur
        m_end = date(cur.year, cur.month, days_in) + timedelta(days=1)
        months.append((m_start, m_end))
        # avanzar al siguiente mes
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)
    return months


def _calc_months_fraction(period_start: date, period_end: date, joined_at: date | None) -> float:
    """Calcula la fracción de meses de costo para un player internal.

    - Si joined_at es anterior al periodo, suma meses completos.
    - Si joined_at cae dentro del periodo, proratea el primer mes.
    - Si no hay joined_at, suma meses completos (nota en el servicio).
    """
    effective_start = period_start
    if joined_at is not None and joined_at > period_start:
        effective_start = joined_at

    if effective_start >= period_end:
        return 0.0

    months = _months_in_period(effective_start, period_end)
    if not months:
        return 0.0

    total_fraction = 0.0
    for m_start, m_end in months:
        _, days_in = calendar.monthrange(m_start.year, m_start.month)
        # días activos en este mes
        active_start = max(m_start, effective_start)
        active_end = min(m_end, period_end)
        active_days = (active_end - active_start).days
        total_fraction += active_days / days_in

    return total_fraction


def _calc_player_cost(
    p: Player,
    period_start: date,
    period_end: date,
) -> tuple[float | None, str | None]:
    """Devuelve (costo_total, nota). costo_total=None si no calculable."""
    joined = p.joined_at.date() if isinstance(p.joined_at, datetime) else p.joined_at

    if p.employment_type == "internal":
        if p.monthly_salary is None:
            return None, "Costo no capturado"
        months_fraction = _calc_months_fraction(period_start, period_end, joined)
        cost = float(p.monthly_salary) * months_fraction
        note = None if joined is not None else "sin joined_at — meses completos"
        return cost, note

    # external
    if p.hourly_rate is None:
        return None, "Costo no capturado"
    if p.monthly_hours_cap is None:
        return None, "Estimación manual pendiente (sin monthly_hours_cap)"
    months_fraction = _calc_months_fraction(period_start, period_end, joined)
    cost = float(p.hourly_rate) * float(p.monthly_hours_cap) * months_fraction
    note = None if joined is not None else "sin joined_at — meses completos"
    return cost, note


# ──────────────────────────────────────────────────────────────
# CostService
# ──────────────────────────────────────────────────────────────


class CostService:
    """Servicio de costos por área — read-only (0 escrituras)."""

    def __init__(self, session: Session) -> None:
        self._s = session

    # ── CP/SP por player en un rango de fechas ──────────────────

    def _cp_sp_by_player(
        self,
        period_start: date,
        period_end: date,
        project_code: str | None = None,
    ) -> dict[int, tuple[int, float, int]]:
        """Devuelve {player_id: (cp_total, sp_total, done_subtasks)}."""
        filters = [
            Subtask.status == _DONE,
            Subtask.done_at >= datetime.combine(period_start, datetime.min.time()),
            Subtask.done_at < datetime.combine(period_end, datetime.min.time()),
        ]
        if project_code:
            filters.append(Subtask.project_code == project_code)

        rows = self._s.execute(
            select(
                Subtask.assignee_player_id,
                func.coalesce(func.sum(Subtask.cp), 0).label("cp"),
                func.coalesce(func.sum(Subtask.sp_final), 0).label("sp"),
                func.count(Subtask.jira_key).label("done"),
            )
            .where(*filters)
            .group_by(Subtask.assignee_player_id)
        ).all()

        return {
            row.assignee_player_id: (int(row.cp), float(row.sp), int(row.done))
            for row in rows
            if row.assignee_player_id is not None
        }

    def _build_player_cost(
        self,
        p: Player,
        cp: int,
        sp: float,
        done: int,
        period_start: date,
        period_end: date,
    ) -> PlayerCost:
        cost_total, cost_note = _calc_player_cost(p, period_start, period_end)
        cost_not_captured = cost_total is None
        no_production = (not cost_not_captured) and (cp == 0)

        if cost_not_captured or cost_total is None:
            cost_per_cp = None
            cost_per_sp = None
        elif cp == 0:
            cost_per_cp = None  # div/0 → "—"
            cost_per_sp = None if sp == 0.0 else None
        else:
            cost_per_cp = round(cost_total / cp, 2) if cp > 0 else None
            cost_per_sp = round(cost_total / sp, 2) if sp > 0 else None

        return PlayerCost(
            player_id=p.id,
            display_name=p.display_name,
            area=p.area,
            employment_type=p.employment_type,
            cp_total=cp,
            sp_total=sp,
            done_subtasks=done,
            cost_total=round(cost_total, 2) if cost_total is not None else None,
            cost_per_cp=cost_per_cp,
            cost_per_sp=cost_per_sp,
            cost_not_captured=cost_not_captured,
            no_production=no_production,
            cost_note=cost_note,
        )

    # ── API pública ────────────────────────────────────────────

    def cost_by_area(
        self,
        period: str = "q_current",
        custom_start: date | None = None,
        custom_end: date | None = None,
        project_code: str | None = None,
    ) -> list[AreaCost]:
        """Costos agrupados por área técnica con desglose por player."""
        period_start, period_end = resolve_period(period, custom_start, custom_end)
        cp_map = self._cp_sp_by_player(period_start, period_end, project_code)
        prev_start, prev_end = resolve_period("q_prev") if period not in ("q_prev", "custom") else (period_start, period_end)
        cp_map_prev = self._cp_sp_by_player(prev_start, prev_end, project_code)

        players = self._s.execute(select(Player).where(Player.is_active == True)).scalars().all()  # noqa: E712

        area_map: dict[str, list[PlayerCost]] = {}
        # Incluir todos los players activos que produjeron CP o tienen costo
        for p in players:
            cp, sp, done = cp_map.get(p.id, (0, 0.0, 0))
            pc = self._build_player_cost(p, cp, sp, done, period_start, period_end)
            # Incluir si tiene producción o si tiene costo capturado
            if cp > 0 or not pc.cost_not_captured:
                area_map.setdefault(p.area, []).append(pc)

        # Calcular costo previo del área para delta
        prev_area_cost: dict[str, float] = {}
        for p in players:
            cp_p, _, _ = cp_map_prev.get(p.id, (0, 0.0, 0))
            cost_p, _ = _calc_player_cost(p, prev_start, prev_end)
            if cost_p is not None:
                prev_area_cost[p.area] = prev_area_cost.get(p.area, 0.0) + cost_p

        results: list[AreaCost] = []
        for area in _ALL_AREAS:
            area_players = area_map.get(area, [])
            if not area_players and area not in ("BE", "FE", "DESIGN", "DB", "QA", "PO", "PM"):
                continue

            cp_total = sum(pc.cp_total for pc in area_players)
            sp_total = sum(pc.sp_total for pc in area_players)
            done_total = sum(pc.done_subtasks for pc in area_players)
            costs = [pc.cost_total for pc in area_players if pc.cost_total is not None]
            cost_total = round(sum(costs), 2) if costs else None

            cost_per_cp: float | None = None
            cost_per_sp: float | None = None
            if cost_total is not None and cp_total > 0:
                cost_per_cp = round(cost_total / cp_total, 2)
            if cost_total is not None and sp_total > 0:
                cost_per_sp = round(cost_total / sp_total, 2)

            delta_pct: float | None = None
            prev_cost = prev_area_cost.get(area)
            if cost_total is not None and prev_cost is not None and prev_cost > 0:
                delta_pct = round((cost_total - prev_cost) / prev_cost * 100, 1)

            if area_players:  # solo incluir áreas con datos
                results.append(
                    AreaCost(
                        area=area,
                        players_active=len(area_players),
                        cp_total=cp_total,
                        sp_total=sp_total,
                        done_subtasks=done_total,
                        cost_total=cost_total,
                        cost_per_cp=cost_per_cp,
                        cost_per_sp=cost_per_sp,
                        delta_pct=delta_pct,
                        players=area_players,
                    )
                )

        results.sort(key=lambda a: a.cp_total, reverse=True)
        return results

    def cost_by_dev(
        self,
        period: str = "q_current",
        area: str | None = None,
        custom_start: date | None = None,
        custom_end: date | None = None,
        project_code: str | None = None,
    ) -> list[PlayerCost]:
        """Costos por developer individual."""
        period_start, period_end = resolve_period(period, custom_start, custom_end)
        cp_map = self._cp_sp_by_player(period_start, period_end, project_code)

        filters = [Player.is_active == True]  # noqa: E712
        if area:
            filters.append(Player.area == area)

        players = self._s.execute(select(Player).where(*filters)).scalars().all()

        results: list[PlayerCost] = []
        for p in players:
            cp, sp, done = cp_map.get(p.id, (0, 0.0, 0))
            pc = self._build_player_cost(p, cp, sp, done, period_start, period_end)
            if cp > 0 or not pc.cost_not_captured:
                results.append(pc)

        results.sort(key=lambda p: p.cp_total, reverse=True)
        return results

    def comparison_int_ext(
        self,
        period: str = "q_current",
        custom_start: date | None = None,
        custom_end: date | None = None,
        project_code: str | None = None,
    ) -> list[IntExtComparison]:
        """Comparativa costo/CP internos vs externos por área."""
        area_results = self.cost_by_area(period, custom_start, custom_end, project_code)

        comparisons: list[IntExtComparison] = []
        for area_cost in area_results:
            int_costs = [
                pc for pc in area_cost.players
                if pc.employment_type == "internal" and pc.cost_total is not None and pc.cp_total > 0
            ]
            ext_costs = [
                pc for pc in area_cost.players
                if pc.employment_type == "external" and pc.cost_total is not None and pc.cp_total > 0
            ]

            int_cost_per_cp: float | None = None
            if int_costs:
                total_cp_int = sum(p.cp_total for p in int_costs)
                total_cost_int = sum(p.cost_total for p in int_costs if p.cost_total is not None)
                int_cost_per_cp = round(total_cost_int / total_cp_int, 2) if total_cp_int > 0 else None

            ext_cost_per_cp: float | None = None
            if ext_costs:
                total_cp_ext = sum(p.cp_total for p in ext_costs)
                total_cost_ext = sum(p.cost_total for p in ext_costs if p.cost_total is not None)
                ext_cost_per_cp = round(total_cost_ext / total_cp_ext, 2) if total_cp_ext > 0 else None

            multiplier: float | None = None
            insight: str

            if int_cost_per_cp is not None and ext_cost_per_cp is not None and int_cost_per_cp > 0:
                multiplier = round(ext_cost_per_cp / int_cost_per_cp, 2)
                if multiplier > 1:
                    insight = f"Externos en {area_cost.area} cuestan {multiplier}× más por CP que internos"
                elif multiplier < 1:
                    insight = f"Externos en {area_cost.area} cuestan {round(1/multiplier,2)}× menos por CP que internos"
                else:
                    insight = f"Costo/CP similar entre internos y externos en {area_cost.area}"
            elif int_cost_per_cp is not None:
                insight = f"Solo internos con costo medible en {area_cost.area}"
            elif ext_cost_per_cp is not None:
                insight = f"Solo externos con costo medible en {area_cost.area}"
            else:
                insight = f"Sin datos suficientes para comparar en {area_cost.area}"

            comparisons.append(
                IntExtComparison(
                    area=area_cost.area,
                    int_cost_per_cp=int_cost_per_cp,
                    ext_cost_per_cp=ext_cost_per_cp,
                    int_players=len(int_costs),
                    ext_players=len(ext_costs),
                    multiplier=multiplier,
                    insight=insight,
                )
            )

        return comparisons

    def evolution_12m(
        self,
        area: str | None = None,
        project_code: str | None = None,
    ) -> list[EvolutionPoint]:
        """Costo/CP mensual, últimos 12 meses calendario."""
        today = date.today()
        # últimos 12 meses completos
        points: list[EvolutionPoint] = []

        players = self._s.execute(select(Player).where(Player.is_active == True)).scalars().all()  # noqa: E712
        if area:
            players = [p for p in players if p.area == area]

        for i in range(11, -1, -1):  # 11..0 → 12 meses pasados
            # mes M meses atrás
            target_month = today.month - i
            target_year = today.year
            while target_month <= 0:
                target_month += 12
                target_year -= 1

            m_start = date(target_year, target_month, 1)
            _, days_in = calendar.monthrange(target_year, target_month)
            m_end = date(target_year, target_month, days_in) + timedelta(days=1)

            cp_map = self._cp_sp_by_player(m_start, m_end, project_code)

            cp_total = 0
            cost_total = 0.0
            has_cost = False
            for p in players:
                cp, _, _ = cp_map.get(p.id, (0, 0.0, 0))
                cp_total += cp
                cost, _ = _calc_player_cost(p, m_start, m_end)
                if cost is not None:
                    cost_total += cost
                    has_cost = True

            cost_per_cp: float | None = None
            if has_cost and cp_total > 0:
                cost_per_cp = round(cost_total / cp_total, 2)

            points.append(
                EvolutionPoint(
                    period_label=f"{target_year}-{target_month:02d}",
                    period_start=m_start,
                    period_end=m_end - timedelta(days=1),
                    cp_total=cp_total,
                    cost_total=round(cost_total, 2) if has_cost else None,
                    cost_per_cp=cost_per_cp,
                )
            )

        return points

    def has_any_cost(self) -> bool:
        """True si hay al menos 1 player activo con costo capturado."""
        result = self._s.execute(
            select(func.count(Player.id)).where(
                Player.is_active == True,  # noqa: E712
                (Player.monthly_salary.is_not(None)) | (Player.hourly_rate.is_not(None)),
            )
        ).scalar_one_or_none()
        return (result or 0) > 0

    def row_counts(self) -> dict[str, int]:
        """Conteo de filas para validar que no hay escrituras (demo read-only)."""
        from forge.db.models.sp_adjustment import SpAdjustment

        return {
            "players": self._s.execute(select(func.count(Player.id))).scalar_one(),
            "subtasks": self._s.execute(select(func.count(Subtask.jira_key))).scalar_one(),
            "sp_adjustments": self._s.execute(select(func.count(SpAdjustment.id))).scalar_one(),
        }
