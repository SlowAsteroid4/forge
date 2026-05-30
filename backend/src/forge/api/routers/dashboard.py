"""API Router para UC-02: Dashboard del sprint."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError
from forge.db.session import get_session
from forge.schemas.dashboard import DashboardResponse
from forge.services.dashboard_service import DashboardService

router = APIRouter(tags=["dashboard"])


@router.get("/sprint", response_model=DashboardResponse)
def get_sprint_dashboard(
    project_code: str | None = Query(
        default=None,
        description="Filtrar por código de proyecto (ej. 'YAP'). Sin valor = todos los proyectos.",
    ),
    sprint_id: int | None = Query(
        default=None,
        description="ID del sprint (sin valor = sprint activo).",
    ),
    session: Session = Depends(get_session),
) -> DashboardResponse:
    """
    UC-02: Dashboard general del sprint.

    Retorna todos los datos necesarios para la vista principal de Forge Ops:
    - Header del sprint (fechas, progreso temporal)
    - KPI cards (CP Done, CP Pendientes, SP Total, Bugs)
    - Progreso por área técnica (BE, FE, Design, DB, QA)
    - Estado de cada developer activo en el sprint
    - Alertas accionables (abandonadas, bloqueadas, WIP excedido, CP pendiente)

    Cuando no hay sprint activo devuelve `sprint=null` con `no_sprint_message`
    — el frontend renderiza el empty state con CTA para crear sprint.
    """
    service = DashboardService(session)
    try:
        return service.get_dashboard(project_code=project_code, sprint_id=sprint_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": e.message})
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "dashboard_error", "message": str(e)},
        )


@router.get("/sprint/projects")
def get_available_projects(
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Lista de proyectos activos disponibles para el filtro del dashboard."""
    service = DashboardService(session)
    projects = service._get_available_projects()
    return {"projects": [p.model_dump() for p in projects]}
