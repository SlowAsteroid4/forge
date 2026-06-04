"""API Router — WP-07a: Analíticas de Flujo / Cuellos de botella."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from forge.db.session import get_session
from forge.schemas.analytics import (
    CpByAreaResponse,
    CpPerDayResponse,
    QaFirstPassResponse,
    TimeInStatusDetailResponse,
    TimeInStatusResponse,
    ThroughputResponse,
)
from forge.services.analytics_service import AnalyticsService

router = APIRouter(tags=["analytics"])


def _svc(session: Session = Depends(get_session)) -> AnalyticsService:
    return AnalyticsService(session)


@router.get("/throughput", response_model=ThroughputResponse)
def get_throughput(
    last_n: int = Query(default=8, ge=1, le=52, description="Número de ciclos a retornar"),
    svc: AnalyticsService = Depends(_svc),
) -> ThroughputResponse:
    """Serie temporal de CP y subtasks Done por ciclo (N ciclos más recientes)."""
    try:
        cycles = svc.throughput_by_cycle(last_n=last_n)
        from forge.schemas.analytics import ThroughputPoint

        return ThroughputResponse(
            cycles=[ThroughputPoint(**c) for c in cycles],
            total_cycles=len(cycles),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "analytics_error", "message": str(e)})


@router.get("/cp-by-area", response_model=CpByAreaResponse)
def get_cp_by_area(
    scope: str = Query(
        default="cycle",
        pattern="^(cycle|window)$",
        description="'cycle' = ciclo activo, 'window' = 4 ciclos cerrados",
    ),
    cycle_id: int | None = Query(default=None, description="ID de ciclo específico"),
    svc: AnalyticsService = Depends(_svc),
) -> CpByAreaResponse:
    """CP Done agrupado por área técnica en el scope dado."""
    try:
        areas = svc.cp_by_area(scope=scope, cycle_id=cycle_id)
        from forge.schemas.analytics import AreaBreakdown

        return CpByAreaResponse(
            scope=scope,
            cycle_id=cycle_id,
            areas=[AreaBreakdown(**a) for a in areas],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "analytics_error", "message": str(e)})


@router.get("/cp-per-day-by-dev", response_model=CpPerDayResponse)
def get_cp_per_day_by_dev(
    scope: str = Query(
        default="cycle",
        pattern="^(cycle|window)$",
        description="'cycle' = ciclo activo, 'window' = 4 ciclos cerrados",
    ),
    svc: AnalyticsService = Depends(_svc),
) -> CpPerDayResponse:
    """CP Done normalizado por días hábiles, por dev."""
    try:
        devs = svc.cp_per_day_by_dev(scope=scope)
        from forge.schemas.analytics import DevCpPerDay

        biz_days = devs[0]["biz_days"] if devs else 0
        return CpPerDayResponse(
            scope=scope,
            biz_days=biz_days,
            devs=[DevCpPerDay(**d) for d in devs],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "analytics_error", "message": str(e)})


@router.get("/qa-first-pass-by-dev", response_model=QaFirstPassResponse)
def get_qa_first_pass_by_dev(
    scope: str = Query(
        default="historical",
        pattern="^(cycle|window|historical)$",
        description="'cycle' | 'window' | 'historical'",
    ),
    svc: AnalyticsService = Depends(_svc),
) -> QaFirstPassResponse:
    """% QA first-pass por dev en el scope dado."""
    try:
        devs = svc.qa_first_pass_by_dev(scope=scope)
        from forge.schemas.analytics import DevQaFirstPass

        return QaFirstPassResponse(
            scope=scope,
            devs=[DevQaFirstPass(**d) for d in devs],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "analytics_error", "message": str(e)})


@router.get("/time-in-status", response_model=TimeInStatusResponse)
def get_time_in_status(
    group_by: str = Query(
        default="area",
        pattern="^(area|player)$",
        description="'area' | 'player'",
    ),
    scope: str = Query(
        default="window",
        pattern="^(cycle|window|historical)$",
        description="'cycle' | 'window' | 'historical'",
    ),
    svc: AnalyticsService = Depends(_svc),
) -> TimeInStatusResponse:
    """Horas por bucket de estado (dev_resp / qa / review / blocked / waiting).

    Primer resultado = mayor cuello de botella en el scope.
    Granularidad: buckets pre-computados (rápido). Para estados Jira específicos
    usa GET /time-in-status-detail.
    """
    try:
        rows = svc.time_in_status(group_by=group_by, scope=scope)
        from forge.schemas.analytics import TimeInStatusRow

        return TimeInStatusResponse(
            scope=scope,
            group_by=group_by,
            rows=[TimeInStatusRow(**r) for r in rows],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "analytics_error", "message": str(e)})


@router.get("/time-in-status-detail", response_model=TimeInStatusDetailResponse)
def get_time_in_status_detail(
    group_by: str = Query(default="area", pattern="^(area|player)$"),
    scope: str = Query(default="window", pattern="^(cycle|window|historical)$"),
    svc: AnalyticsService = Depends(_svc),
) -> TimeInStatusDetailResponse:
    """Horas por estado Jira específico (parseo de raw_changelog).

    Más lento; incluye estados como 'Ready for QA', 'Active', 'In Design'.
    """
    try:
        rows = svc.time_in_status_detail(group_by=group_by, scope=scope)
        from forge.schemas.analytics import StatusDetailRow

        return TimeInStatusDetailResponse(
            scope=scope,
            group_by=group_by,
            rows=[StatusDetailRow(**r) for r in rows],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "analytics_error", "message": str(e)})
