"""API Router para UC-16 Pulso Operativo (read-only)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from forge.db.session import get_session
from forge.schemas.pulse import PulseSnapshot
from forge.services.pulse_service import PulseService

router = APIRouter(tags=["pulse"])


@router.get("/now", response_model=PulseSnapshot)
def get_pulse_now(
    area: list[str] | None = Query(
        default=None,
        description="Filtrar por area(s) tecnica(s). Ej: ?area=BE&area=FE",
    ),
    project_code: str | None = Query(
        default=None,
        description="Filtrar por codigo de proyecto (ej. 'YAP').",
    ),
    player_id: int | None = Query(
        default=None,
        description="Filtrar por ID de player (dev).",
    ),
    session: Session = Depends(get_session),
) -> PulseSnapshot:
    """
    UC-16: Pulso Operativo en tiempo real.

    Retorna el snapshot operativo completo:
    - globals: activas, bloqueadas, en espera, cola Ready, aging máximo
    - wip_by_area: semaforos WIP por area (verde/amarillo/rojo). QA excluida.
    - blocks: subtasks en Blocked ordenadas por horas bloqueado desc; >8h = critico
    - day_movements: cambios de estado en las ultimas 24h
    - aging_critical: activas con >5 dias habiles en estado actual
    - ready_queue: top 10 en Ready por antiguedad

    Este endpoint es estrictamente READ-ONLY: no escribe en ninguna tabla.
    """
    service = PulseService(session)
    return service.get_pulse(areas=area, project_code=project_code, player_id=player_id)
