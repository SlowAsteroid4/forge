"""API Router para UC-16 Pulso Operativo."""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from forge.db.models.audit_log import AuditLog
from forge.db.models.subtask import Subtask
from forge.db.session import get_session
from forge.schemas.pulse import FlagForReviewRequest, FlagForReviewResponse, PulseSnapshot
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


@router.post("/flag/{jira_key}", response_model=FlagForReviewResponse)
def flag_for_review(
    jira_key: str,
    body: FlagForReviewRequest,
    session: Session = Depends(get_session),
) -> FlagForReviewResponse:
    """
    UC-16.7: Marcar subtask para revisión.

    REGLA CRÍTICA: Solo escribe a audit_log. NO modifica el status de la subtask
    ni toca ninguna tabla de gamificación (sp_adjustments, leaderboard_snapshots).
    """
    subtask = session.get(Subtask, jira_key)
    if subtask is None:
        raise HTTPException(status_code=404, detail=f"Subtask {jira_key} no encontrada")

    status_before = subtask.status  # registrar para confirmar que no cambia

    log = AuditLog(
        event_type="flagged_for_review",
        entity_type="subtask",
        entity_id=jira_key,
        actor_player_id=None,
        changes=json.dumps(
            {
                "status_unchanged": status_before,
                "note": body.note,
            }
        ),
        timestamp=datetime.utcnow(),
    )
    session.add(log)
    session.commit()
    session.refresh(log)

    return FlagForReviewResponse(
        jira_key=jira_key,
        audit_log_id=log.id,
        message=f"Subtask {jira_key} marcada para revisión (status sin cambiar: {status_before})",
    )
