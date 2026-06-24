"""API Router — UC-08: Costos por área (read-only)."""

from __future__ import annotations

from datetime import date, timedelta
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from forge.db.session import get_session
from forge.schemas.cost import (
    AreaCostResponse,
    ComparisonResponse,
    DevCostResponse,
    EvolutionResponse,
)
from forge.services.cost_service import (
    CostService,
    require_cost_access,
    resolve_period,
)

router = APIRouter(tags=["costs"])


def _svc(session: Session = Depends(get_session)) -> CostService:
    return CostService(session)


def _guard() -> None:
    """Aplica guard de permisos placeholder."""
    require_cost_access()


@router.get("/by-area", response_model=AreaCostResponse)
def get_cost_by_area(
    period: str = Query(default="q_current", description="q_current|q_prev|last_12m|y_current|custom"),
    project_code: str | None = Query(default=None),
    custom_start: date | None = Query(default=None),
    custom_end: date | None = Query(default=None),
    svc: CostService = Depends(_svc),
) -> AreaCostResponse:
    """Costos agregados por área con desglose por player."""
    _guard()
    try:
        period_start, period_end = resolve_period(period, custom_start, custom_end)
        areas = svc.cost_by_area(period, custom_start, custom_end, project_code)
        total_cp = sum(a.cp_total for a in areas)
        costs = [a.cost_total for a in areas if a.cost_total is not None]
        total_cost = round(sum(costs), 2) if costs else None

        from forge.schemas.cost import AreaCostItem, PlayerCostItem

        return AreaCostResponse(
            areas=[
                AreaCostItem(
                    area=a.area,
                    players_active=a.players_active,
                    cp_total=a.cp_total,
                    sp_total=a.sp_total,
                    done_subtasks=a.done_subtasks,
                    cost_total=a.cost_total,
                    cost_per_cp=a.cost_per_cp,
                    cost_per_sp=a.cost_per_sp,
                    delta_pct=a.delta_pct,
                    players=[
                        PlayerCostItem(
                            player_id=p.player_id,
                            display_name=p.display_name,
                            area=p.area,
                            employment_type=p.employment_type,
                            cp_total=p.cp_total,
                            sp_total=p.sp_total,
                            done_subtasks=p.done_subtasks,
                            cost_total=p.cost_total,
                            cost_per_cp=p.cost_per_cp,
                            cost_per_sp=p.cost_per_sp,
                            cost_not_captured=p.cost_not_captured,
                            no_production=p.no_production,
                            cost_note=p.cost_note,
                        )
                        for p in a.players
                    ],
                )
                for a in areas
            ],
            period=period,
            period_start=period_start,
            period_end=period_end - timedelta(days=1),
            has_any_cost=svc.has_any_cost(),
            total_cp=total_cp,
            total_cost=total_cost,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "cost_error", "message": str(e)})


@router.get("/by-dev", response_model=DevCostResponse)
def get_cost_by_dev(
    period: str = Query(default="q_current"),
    area: str | None = Query(default=None),
    project_code: str | None = Query(default=None),
    custom_start: date | None = Query(default=None),
    custom_end: date | None = Query(default=None),
    svc: CostService = Depends(_svc),
) -> DevCostResponse:
    """Costos por developer individual."""
    _guard()
    try:
        period_start, period_end = resolve_period(period, custom_start, custom_end)
        players = svc.cost_by_dev(period, area, custom_start, custom_end, project_code)

        from forge.schemas.cost import PlayerCostItem

        return DevCostResponse(
            players=[
                PlayerCostItem(
                    player_id=p.player_id,
                    display_name=p.display_name,
                    area=p.area,
                    employment_type=p.employment_type,
                    cp_total=p.cp_total,
                    sp_total=p.sp_total,
                    done_subtasks=p.done_subtasks,
                    cost_total=p.cost_total,
                    cost_per_cp=p.cost_per_cp,
                    cost_per_sp=p.cost_per_sp,
                    cost_not_captured=p.cost_not_captured,
                    no_production=p.no_production,
                    cost_note=p.cost_note,
                )
                for p in players
            ],
            period=period,
            period_start=period_start,
            period_end=period_end - timedelta(days=1),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "cost_error", "message": str(e)})


@router.get("/comparison", response_model=ComparisonResponse)
def get_comparison(
    period: str = Query(default="q_current"),
    project_code: str | None = Query(default=None),
    custom_start: date | None = Query(default=None),
    custom_end: date | None = Query(default=None),
    svc: CostService = Depends(_svc),
) -> ComparisonResponse:
    """Comparativa costo/CP internos vs externos por área."""
    _guard()
    try:
        period_start, period_end = resolve_period(period, custom_start, custom_end)
        comparisons = svc.comparison_int_ext(period, custom_start, custom_end, project_code)

        from forge.schemas.cost import IntExtComparisonItem

        return ComparisonResponse(
            comparisons=[
                IntExtComparisonItem(
                    area=c.area,
                    int_cost_per_cp=c.int_cost_per_cp,
                    ext_cost_per_cp=c.ext_cost_per_cp,
                    int_players=c.int_players,
                    ext_players=c.ext_players,
                    multiplier=c.multiplier,
                    insight=c.insight,
                )
                for c in comparisons
            ],
            period=period,
            period_start=period_start,
            period_end=period_end - timedelta(days=1),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "cost_error", "message": str(e)})


@router.get("/evolution", response_model=EvolutionResponse)
def get_evolution(
    area: str | None = Query(default=None),
    project_code: str | None = Query(default=None),
    svc: CostService = Depends(_svc),
) -> EvolutionResponse:
    """Evolución costo/CP mensual, últimos 12 meses."""
    _guard()
    try:
        points = svc.evolution_12m(area, project_code)

        from forge.schemas.cost import EvolutionPointItem

        return EvolutionResponse(
            points=[
                EvolutionPointItem(
                    period_label=p.period_label,
                    period_start=p.period_start,
                    period_end=p.period_end,
                    cp_total=p.cp_total,
                    cost_total=p.cost_total,
                    cost_per_cp=p.cost_per_cp,
                )
                for p in points
            ],
            area=area,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "cost_error", "message": str(e)})


@router.get("/by-area.csv")
def export_csv(
    period: str = Query(default="q_current"),
    project_code: str | None = Query(default=None),
    custom_start: date | None = Query(default=None),
    custom_end: date | None = Query(default=None),
    svc: CostService = Depends(_svc),
) -> StreamingResponse:
    """Exporta costos por área + player como CSV."""
    _guard()
    try:
        period_start, period_end = resolve_period(period, custom_start, custom_end)
        areas = svc.cost_by_area(period, custom_start, custom_end, project_code)

        buf = StringIO()
        buf.write("area,player,employment_type,cp_total,sp_total,cost_total,cost_per_cp,cost_per_sp,cost_not_captured,no_production,cost_note\n")
        for a in areas:
            for p in a.players:
                row = [
                    a.area,
                    f'"{p.display_name}"',
                    p.employment_type,
                    str(p.cp_total),
                    str(round(p.sp_total, 2)),
                    str(p.cost_total) if p.cost_total is not None else "—",
                    str(p.cost_per_cp) if p.cost_per_cp is not None else "—",
                    str(p.cost_per_sp) if p.cost_per_sp is not None else "—",
                    str(p.cost_not_captured).lower(),
                    str(p.no_production).lower(),
                    f'"{p.cost_note or ""}"',
                ]
                buf.write(",".join(row) + "\n")

        buf.seek(0)
        filename = f"costos_{period}_{period_start}_{period_end}.csv"
        return StreamingResponse(
            buf,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "cost_error", "message": str(e)})
