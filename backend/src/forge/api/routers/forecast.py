"""API Router — UC-07: Forecast P30/P50/P85 por épica."""

from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from forge.db.session import get_session
from forge.schemas.forecast import (
    EpicForecastDetail,
    EpicForecastItem,
    EpicForecastListResponse,
    RecalculateResponse,
)
from forge.services.engine.forecast import AreaForecast, EpicForecast
from forge.services.forecast_service import ForecastService

router = APIRouter(tags=["forecast"])


def _svc(session: Session = Depends(get_session)) -> ForecastService:
    return ForecastService(session)


def _to_item(ef: EpicForecast) -> EpicForecastItem:
    return EpicForecastItem(
        epic_key=ef.epic_key,
        summary=ef.summary,
        project_code=ef.project_code,
        status=ef.status,
        cp_total=ef.cp_total,
        cp_done=ef.cp_done,
        cp_pending=ef.cp_pending,
        pct_done=ef.pct_done,
        date_optimistic=ef.date_optimistic,
        date_realistic=ef.date_realistic,
        date_conservative=ef.date_conservative,
        preliminary=ef.preliminary,
        warning=ef.warning,
        blocked_count=ef.blocked_count,
    )


def _to_detail(ef: EpicForecast) -> EpicForecastDetail:
    from forge.schemas.forecast import AreaForecastSchema

    return EpicForecastDetail(
        **_to_item(ef).model_dump(),
        areas=[
            AreaForecastSchema(
                area=af.area,
                cp_done=af.cp_done,
                cp_pending=af.cp_pending,
                n_cycles_data=af.n_cycles_data,
                velocity_avg=af.velocity_avg,
                velocity_best=af.velocity_best,
                velocity_cons=af.velocity_cons,
                weeks_optimistic=af.weeks_optimistic,
                weeks_realistic=af.weeks_realistic,
                weeks_conservative=af.weeks_conservative,
                date_optimistic=af.date_optimistic,
                date_realistic=af.date_realistic,
                date_conservative=af.date_conservative,
                preliminary=af.preliminary,
            )
            for af in ef.areas
        ],
    )


@router.get("/epics", response_model=EpicForecastListResponse)
def list_epic_forecasts(
    project_code: str | None = Query(default=None, description="Filtrar por proyecto"),
    epic_status: str | None = Query(default=None, description="Filtrar por estado de épica"),
    svc: ForecastService = Depends(_svc),
) -> EpicForecastListResponse:
    """Lista de épicas activas con sus 3 fechas de cierre estimadas."""
    try:
        result = svc.get_epic_forecasts(project_code=project_code, epic_status=epic_status)
        epics: list[EpicForecast] = result["epics"]
        return EpicForecastListResponse(
            epics=[_to_item(ef) for ef in epics],
            total=len(epics),
            n_closed_cycles=result["n_closed_cycles"],
            calculated_at=result["calculated_at"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "forecast_error", "message": str(e)})


@router.get("/epics/{epic_key}", response_model=EpicForecastDetail)
def get_epic_detail(
    epic_key: str,
    svc: ForecastService = Depends(_svc),
) -> EpicForecastDetail:
    """Detalle de forecast de una épica con desglose por área técnica."""
    try:
        ef = svc.get_epic_detail(epic_key)
        if ef is None:
            raise HTTPException(status_code=404, detail="Épica no encontrada")
        return _to_detail(ef)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "forecast_error", "message": str(e)})


@router.post("/recalculate", response_model=RecalculateResponse)
def recalculate(
    project_code: str | None = Query(default=None),
    svc: ForecastService = Depends(_svc),
) -> RecalculateResponse:
    """Fuerza recálculo del forecast (MVP: always on-the-fly, retorna resultado fresco)."""
    try:
        result = svc.get_epic_forecasts(project_code=project_code)
        epics: list[EpicForecast] = result["epics"]
        return RecalculateResponse(
            message="Forecast recalculado (on-the-fly, sin escritura a BD)",
            total=len(epics),
            calculated_at=result["calculated_at"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "forecast_error", "message": str(e)})


@router.get("/epics.csv")
def export_csv(
    project_code: str | None = Query(default=None),
    epic_status: str | None = Query(default=None),
    svc: ForecastService = Depends(_svc),
) -> StreamingResponse:
    """Exporta el forecast de épicas como CSV."""
    try:
        result = svc.get_epic_forecasts(project_code=project_code, epic_status=epic_status)
        epics: list[EpicForecast] = result["epics"]

        buf = StringIO()
        buf.write("epic_key,summary,project,status,cp_total,cp_done,cp_pending,pct_done,")
        buf.write("date_optimista,date_realista,date_conservador,preliminary,warning\n")
        for ef in epics:
            row = [
                ef.epic_key,
                f'"{ef.summary}"',
                ef.project_code,
                ef.status,
                str(ef.cp_total),
                str(ef.cp_done),
                str(ef.cp_pending),
                str(ef.pct_done),
                str(ef.date_optimistic) if ef.date_optimistic else "",
                str(ef.date_realistic) if ef.date_realistic else "",
                str(ef.date_conservative) if ef.date_conservative else "",
                str(ef.preliminary).lower(),
                f'"{ef.warning or ""}"',
            ]
            buf.write(",".join(row) + "\n")

        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=forecast.csv"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "forecast_error", "message": str(e)})
