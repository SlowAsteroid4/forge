"""Router UC-05: cierre de ciclo semanal y MVP."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError, RuleViolationError
from forge.db.models import Player
from forge.db.session import get_session
from forge.schemas.cycle_close import (
    CycleCandidate,
    CycleCloseRequest,
    CycleCloseResponse,
    CycleCloseSummary,
    CycleRecalcResponse,
    MvpEditRequest,
    MvpHistoryItem,
)
from forge.services.cycle_service import CycleService

router = APIRouter(tags=["cycle-admin"])


class PlayerOption(BaseModel):
    id: int
    display_name: str
    area: str

# Hardcoded admin_id=1 until auth is built (WP-08)
_DEFAULT_ADMIN_ID = 1


def _service(session: Session = Depends(get_session)) -> CycleService:
    return CycleService(session)


@router.get("/players-options", response_model=list[PlayerOption])
def list_players_options(session: Session = Depends(get_session)) -> list[PlayerOption]:
    players = session.query(Player).filter(Player.is_active.is_(True)).order_by(Player.display_name).all()
    return [PlayerOption(id=p.id, display_name=p.display_name, area=p.area or "") for p in players]


@router.get("/cycles/{cycle_id}/mvp-candidates", response_model=list[CycleCandidate])
def get_mvp_candidates(
    cycle_id: int,
    svc: CycleService = Depends(_service),
) -> list[CycleCandidate]:
    try:
        candidates = svc.get_mvp_candidates(cycle_id)
        return [CycleCandidate(**c) for c in candidates]
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuleViolationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/cycles/{cycle_id}/close-summary", response_model=CycleCloseSummary)
def get_close_summary(
    cycle_id: int,
    svc: CycleService = Depends(_service),
) -> CycleCloseSummary:
    try:
        summary = svc.get_close_summary(cycle_id)
        return CycleCloseSummary(**summary)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/cycles/{cycle_id}/recalc", response_model=CycleRecalcResponse)
def recalc_cycle(
    cycle_id: int,
    admin_id: int = Query(default=_DEFAULT_ADMIN_ID),
    svc: CycleService = Depends(_service),
) -> CycleRecalcResponse:
    """Recalcula sp_final de las Done sin calcular del ciclo y re-evalúa el bloqueo."""
    try:
        result = svc.recalc_cycle_sp(cycle_id, system_player_id=admin_id)
        svc._session.commit()
        return CycleRecalcResponse(
            cycle_id=result["cycle_id"],
            recalculated=result["recalculated"],
            message=result["message"],
            summary=CycleCloseSummary(**result["summary"]),
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuleViolationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/cycles/{cycle_id}/close", response_model=CycleCloseResponse)
def close_cycle(
    cycle_id: int,
    body: CycleCloseRequest,
    admin_id: int = Query(default=_DEFAULT_ADMIN_ID),
    svc: CycleService = Depends(_service),
) -> CycleCloseResponse:
    try:
        cycle = svc.close_cycle(
            cycle_id=cycle_id,
            mvp_player_id=body.mvp_player_id,
            mvp_reason=body.mvp_reason,
            closed_by=admin_id,
        )
        svc._session.commit()
        return CycleCloseResponse(
            cycle_id=cycle.id,
            cycle_name=cycle.name,
            status=cycle.status,
            closed_at=cycle.closed_at,
            mvp_player_id=cycle.mvp_player_id,
            mvp_reason=cycle.mvp_reason,
            message=f"Ciclo {cycle.name} cerrado. MVP asignado a player_id={cycle.mvp_player_id}.",
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuleViolationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/cycles/{cycle_id}/edit-mvp", response_model=CycleCloseResponse)
def edit_mvp(
    cycle_id: int,
    body: MvpEditRequest,
    admin_id: int = Query(default=_DEFAULT_ADMIN_ID),
    svc: CycleService = Depends(_service),
) -> CycleCloseResponse:
    try:
        cycle = svc.edit_mvp(
            cycle_id=cycle_id,
            new_mvp_player_id=body.new_mvp_player_id,
            reason=body.reason,
            edited_by=admin_id,
        )
        svc._session.commit()
        return CycleCloseResponse(
            cycle_id=cycle.id,
            cycle_name=cycle.name,
            status=cycle.status,
            closed_at=cycle.closed_at,
            mvp_player_id=cycle.mvp_player_id,
            mvp_reason=cycle.mvp_reason,
            message=f"MVP de {cycle.name} actualizado a player_id={cycle.mvp_player_id}.",
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuleViolationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/cycles/mvp-history", response_model=list[MvpHistoryItem])
def get_mvp_history(
    area: str | None = Query(default=None),
    player_id: int | None = Query(default=None),
    svc: CycleService = Depends(_service),
) -> list[MvpHistoryItem]:
    history = svc.get_mvp_history(area=area, player_id=player_id)
    return [MvpHistoryItem(**item) for item in history]
