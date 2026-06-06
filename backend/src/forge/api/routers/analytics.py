"""API Router — WP-07a: Analíticas de Flujo / Cuellos de botella."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from forge.db.session import get_session
from forge.schemas.analytics import (
    ApartadoOption,
    ApartadosResponse,
    CanonicalTimeResponse,
    CpByAreaResponse,
    CpPerDayResponse,
    CycleLeadTimeResponse,
    DevListItem,
    DevListResponse,
    DevMetricsResponse,
    QaFirstPassResponse,
    QaFirstPassVsPreviousResponse,
    QualitySummaryResponse,
    ThroughputResponse,
    TimeInStatusDetailResponse,
    TimeInStatusResponse,
)
from forge.services.analytics_service import AnalyticsService

router = APIRouter(tags=["analytics"])


def _svc(session: Session = Depends(get_session)) -> AnalyticsService:
    return AnalyticsService(session)


@router.get("/throughput", response_model=ThroughputResponse)
def get_throughput(
    last_n: int = Query(default=8, ge=1, le=52, description="Número de ciclos a retornar"),
    apartado: str | None = Query(default=None, description="Filtra por apartado"),
    svc: AnalyticsService = Depends(_svc),
) -> ThroughputResponse:
    """Serie temporal de CP y subtasks Done por ciclo (N ciclos más recientes)."""
    try:
        cycles = svc.throughput_by_cycle(last_n=last_n, apartado=apartado)
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
    apartado: str | None = Query(default=None, description="Filtra por apartado"),
    svc: AnalyticsService = Depends(_svc),
) -> CpByAreaResponse:
    """CP Done agrupado por área técnica en el scope dado."""
    try:
        areas = svc.cp_by_area(scope=scope, cycle_id=cycle_id, apartado=apartado)
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
    apartado: str | None = Query(default=None, description="Filtra por apartado"),
    svc: AnalyticsService = Depends(_svc),
) -> CpPerDayResponse:
    """CP Done normalizado por días hábiles, por dev."""
    try:
        devs = svc.cp_per_day_by_dev(scope=scope, apartado=apartado)
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


@router.get("/quality", response_model=QualitySummaryResponse)
def get_quality(
    cycle_id: int | None = Query(
        default=None, description="Ciclo de referencia (None = activo/más reciente con datos)"
    ),
    apartado: str | None = Query(default=None, description="Filtra por apartado"),
    svc: AnalyticsService = Depends(_svc),
) -> QualitySummaryResponse:
    """Sección Quality: probadas / por probar / tiempo prom. en QA + delta vs ciclo anterior."""
    try:
        data = svc.quality_summary(cycle_id=cycle_id, apartado=apartado)
        return QualitySummaryResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "analytics_error", "message": str(e)})


@router.get("/qa-first-pass-vs-previous", response_model=QaFirstPassVsPreviousResponse)
def get_qa_first_pass_vs_previous(
    cycle_id: int | None = Query(
        default=None, description="Ciclo de referencia (None = activo/más reciente con datos)"
    ),
    apartado: str | None = Query(default=None, description="Filtra por apartado"),
    svc: AnalyticsService = Depends(_svc),
) -> QaFirstPassVsPreviousResponse:
    """% QA first-pass por dev: ciclo de referencia vs ciclo anterior."""
    try:
        data = svc.qa_first_pass_vs_previous(cycle_id=cycle_id, apartado=apartado)
        return QaFirstPassVsPreviousResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "analytics_error", "message": str(e)})


@router.get("/time-canonical", response_model=CanonicalTimeResponse)
def get_time_canonical(
    group_by: str = Query(default="area", pattern="^(area|player)$"),
    scope: str = Query(default="window", pattern="^(cycle|window|historical)$"),
    area: str | None = Query(
        default=None, description="Filtra a un área (ej. 'DESIGN' para la sección de Design)"
    ),
    apartado: str | None = Query(default=None, description="Filtra por apartado"),
    svc: AnalyticsService = Depends(_svc),
) -> CanonicalTimeResponse:
    """Horas por estado CANÓNICO (Manifiesto JPDS) por área o dev.

    Las horas vienen de los buckets WP-07h (atribución intacta); solo se re-etiquetan
    a estados canónicos para mostrar. `total_h` = suma de `by_canonical`.
    """
    try:
        rows = svc.time_canonical(
            group_by=group_by, scope=scope, area_filter=area, apartado=apartado
        )
        from forge.schemas.analytics import CanonicalTimeRow

        return CanonicalTimeResponse(
            scope=scope,
            group_by=group_by,
            area_filter=area,
            rows=[CanonicalTimeRow(**r) for r in rows],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "analytics_error", "message": str(e)})


@router.get("/time-in-status-detail", response_model=TimeInStatusDetailResponse)
def get_time_in_status_detail(
    group_by: str = Query(default="area", pattern="^(area|player)$"),
    scope: str = Query(default="window", pattern="^(cycle|window|historical)$"),
    apartado: str | None = Query(default=None, description="Filtra por apartado"),
    svc: AnalyticsService = Depends(_svc),
) -> TimeInStatusDetailResponse:
    """Horas por estado Jira específico (parseo de raw_changelog).

    Más lento; incluye estados como 'Ready for QA', 'Active', 'In Design'.
    """
    try:
        rows = svc.time_in_status_detail(group_by=group_by, scope=scope, apartado=apartado)
        from forge.schemas.analytics import StatusDetailRow

        return TimeInStatusDetailResponse(
            scope=scope,
            group_by=group_by,
            rows=[StatusDetailRow(**r) for r in rows],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "analytics_error", "message": str(e)})


# ──────────────────────────────────────────────────────────────
# WP-17b — apartado, cycle/lead time, métricas por dev
# ──────────────────────────────────────────────────────────────


@router.get("/apartados", response_model=ApartadosResponse)
def get_apartados(svc: AnalyticsService = Depends(_svc)) -> ApartadosResponse:
    """Apartados disponibles (prefijo [XXX] de la épica) + conteo. Incluye 'Sin apartado'."""
    try:
        rows = svc.apartados()
        return ApartadosResponse(apartados=[ApartadoOption(**r) for r in rows])
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "analytics_error", "message": str(e)})


@router.get("/cycle-lead-time", response_model=CycleLeadTimeResponse)
def get_cycle_lead_time(
    grouping: str = Query(
        default="cycle",
        pattern="^(cycle|month|historical)$",
        description="'cycle' | 'month' | 'historical'",
    ),
    apartado: str | None = Query(default=None, description="Filtra por apartado"),
    area: str | None = Query(default=None, description="Filtra por área técnica"),
    svc: AnalyticsService = Depends(_svc),
) -> CycleLeadTimeResponse:
    """Cycle time (In Progress→Done) y Lead time (Backlog→Done) en horas hábiles.

    Detección canónica desde raw_changelog (WP-17a). Serie por ciclo/mes + agregado histórico.
    """
    try:
        data = svc.cycle_lead_time(grouping=grouping, apartado=apartado, area=area)
        return CycleLeadTimeResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "analytics_error", "message": str(e)})


@router.get("/dev-list", response_model=DevListResponse)
def get_dev_list(
    apartado: str | None = Query(default=None, description="Filtra por apartado"),
    scope: str = Query(
        default="historical",
        pattern="^(cycle|window|historical)$",
        description="'cycle' | 'window' | 'historical'",
    ),
    svc: AnalyticsService = Depends(_svc),
) -> DevListResponse:
    """Devs con subtasks Done en el scope (para el selector de métricas por dev)."""
    try:
        devs = svc.dev_list(apartado=apartado, scope=scope)
        return DevListResponse(devs=[DevListItem(**d) for d in devs])
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "analytics_error", "message": str(e)})


@router.get("/dev-metrics", response_model=DevMetricsResponse)
def get_dev_metrics(
    player_id: int = Query(description="ID del dev"),
    scope: str = Query(
        default="historical",
        pattern="^(cycle|window|historical)$",
        description="'cycle' | 'window' | 'historical'",
    ),
    apartado: str | None = Query(default=None, description="Filtra por apartado"),
    svc: AnalyticsService = Depends(_svc),
) -> DevMetricsResponse:
    """Métricas promedio de un dev: tiempo por estado crudo (37) y canónico (9) + cycle/lead/qa."""
    try:
        data = svc.dev_metrics(player_id=player_id, scope=scope, apartado=apartado)
        if data is None:
            raise HTTPException(status_code=404, detail={"error": "player_not_found"})
        return DevMetricsResponse(**data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "analytics_error", "message": str(e)})
