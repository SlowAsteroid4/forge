"""API Router para el Dashboard de Forge Ops (UC-02)."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError
from forge.db.session import get_session
from forge.schemas.dashboard import DashboardResponse
from forge.services.dashboard_service import DashboardService

router = APIRouter(tags=["dashboard"])


@router.get("/cycle", response_model=DashboardResponse)
def get_cycle_dashboard(
    project_code: str | None = Query(
        default=None,
        description="Filtrar por código de proyecto (ej. 'YAP'). Sin valor = todos.",
    ),
    cycle_id: int | None = Query(
        default=None,
        description="ID del ciclo (sin valor = ciclo activo).",
    ),
    session: Session = Depends(get_session),
) -> DashboardResponse:
    """
    UC-02: Dashboard general del ciclo (Ritmo Operativo).

    Retorna todos los datos necesarios para la vista principal de Forge Ops:
    - Header del ciclo (fechas, progreso temporal)
    - KPI cards (CP Done, CP Pendientes, SP Total, Bugs)
    - Progreso por área técnica (BE, FE, Design, DB, QA)
    - Estado de cada developer activo en el ciclo
    - Alertas accionables (abandonadas, bloqueadas, WIP excedido, CP pendiente)

    Cuando no hay ciclo activo devuelve `cycle=null` con `no_cycle_message`.
    """
    service = DashboardService(session)
    try:
        return service.get_dashboard(project_code=project_code, cycle_id=cycle_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": e.message})
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "dashboard_error", "message": str(e)},
        )


@router.get("/sprint", response_model=DashboardResponse, deprecated=True)
def get_sprint_dashboard_deprecated(
    project_code: str | None = Query(default=None),
    sprint_id: int | None = Query(default=None, description="[DEPRECATED] Usar cycle_id"),
    cycle_id: int | None = Query(default=None),
    response: Response = None,  # type: ignore[assignment]
    session: Session = Depends(get_session),
) -> DashboardResponse:
    """
    [DEPRECATED] Usar GET /api/dashboard/cycle en su lugar.

    Alias de compatibilidad. Mapea sprint_id → cycle_id y delega al endpoint /cycle.
    Se eliminará en WP-02.
    """
    if response is not None:
        response.headers["X-Deprecated"] = (
            "This endpoint is deprecated. Use /api/dashboard/cycle instead."
        )
    effective_cycle_id = cycle_id or sprint_id
    service = DashboardService(session)
    try:
        return service.get_dashboard(project_code=project_code, cycle_id=effective_cycle_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": e.message})
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "dashboard_error", "message": str(e)},
        )


@router.get("/cycle/projects")
def get_available_projects(
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Lista de proyectos activos disponibles para el filtro del dashboard."""
    service = DashboardService(session)
    projects = service._get_available_projects()
    return {"projects": [p.model_dump() for p in projects]}


@router.get("/sprint/projects")
def get_available_projects_deprecated(
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """[DEPRECATED] Usar /api/dashboard/cycle/projects."""
    service = DashboardService(session)
    projects = service._get_available_projects()
    return {"projects": [p.model_dump() for p in projects]}
