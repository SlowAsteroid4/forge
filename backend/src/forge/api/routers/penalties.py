"""Router UC-06: penalizaciones manuales + apelaciones."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError, RuleViolationError
from forge.db.session import get_session
from forge.schemas.penalty import (
    ApplyPenaltyRequest,
    DebuffCatalogResponse,
    PendingAppealsResponse,
    PenaltyActionResponse,
    PenaltyListResponse,
    ResolveAppealRequest,
    ReversePenaltyRequest,
)
from forge.services import penalty_service

router = APIRouter(tags=["penalties"])

# Hardcoded hasta WP-08 auth
_DEFAULT_ADMIN_ID = 1


@router.post("", response_model=PenaltyActionResponse, status_code=201)
def apply_penalty(
    body: ApplyPenaltyRequest,
    session: Session = Depends(get_session),
) -> PenaltyActionResponse:
    """Aplicar penalización manual (catálogo o custom) a una subtask."""
    try:
        adj = penalty_service.apply_penalty(
            session=session,
            subtask_key=body.subtask_key,
            reason=body.reason,
            admin_id=_DEFAULT_ADMIN_ID,
            catalog_code=body.catalog_code,
            custom_sp=body.custom_sp,
        )
        session.commit()

        from forge.db.models.subtask import Subtask

        subtask = session.get(Subtask, body.subtask_key)
        return PenaltyActionResponse(
            ok=True,
            message="Penalización aplicada.",
            adjustment_id=adj.id,
            subtask_key=body.subtask_key,
            sp_final=subtask.sp_final if subtask else None,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e.message))
    except RuleViolationError as e:
        raise HTTPException(status_code=422, detail=str(e.message))


@router.post("/{adjustment_id}/reverse", response_model=PenaltyActionResponse)
def reverse_penalty(
    adjustment_id: int,
    body: ReversePenaltyRequest,
    session: Session = Depends(get_session),
) -> PenaltyActionResponse:
    """Revertir una penalización (total o parcialmente) — append-only."""
    try:
        reversal = penalty_service.reverse_penalty(
            session=session,
            adjustment_id=adjustment_id,
            reason=body.reason,
            admin_id=_DEFAULT_ADMIN_ID,
            partial_new_value=body.partial_new_value,
        )
        session.commit()

        from forge.db.models.sp_adjustment import SpAdjustment
        from forge.db.models.subtask import Subtask

        original = session.get(SpAdjustment, adjustment_id)
        subtask = session.get(Subtask, original.subtask_key) if original else None
        return PenaltyActionResponse(
            ok=True,
            message="Reversal registrado.",
            adjustment_id=reversal.id,
            subtask_key=original.subtask_key if original else None,
            sp_final=subtask.sp_final if subtask else None,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e.message))
    except RuleViolationError as e:
        raise HTTPException(status_code=422, detail=str(e.message))


@router.post("/{adjustment_id}/mark-appealed", response_model=PenaltyActionResponse)
def mark_appealed(
    adjustment_id: int,
    session: Session = Depends(get_session),
) -> PenaltyActionResponse:
    """Registrar que el player apeló (en la weekly) — pone en cola pendiente."""
    try:
        penalty_service.mark_appealed(session=session, adjustment_id=adjustment_id)
        session.commit()
        return PenaltyActionResponse(
            ok=True,
            message="Penalización marcada como apelada.",
            adjustment_id=adjustment_id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e.message))
    except RuleViolationError as e:
        raise HTTPException(status_code=422, detail=str(e.message))


@router.post("/{adjustment_id}/resolve-appeal", response_model=PenaltyActionResponse)
def resolve_appeal(
    adjustment_id: int,
    body: ResolveAppealRequest,
    session: Session = Depends(get_session),
) -> PenaltyActionResponse:
    """Resolver una apelación pendiente: upheld / reversed / reduced."""
    try:
        reversal = penalty_service.resolve_appeal(
            session=session,
            adjustment_id=adjustment_id,
            resolution=body.resolution,
            notes=body.notes,
            admin_id=_DEFAULT_ADMIN_ID,
            reduced_value=body.reduced_value,
        )
        session.commit()

        msg_map = {
            "upheld": "Apelación rechazada — penalización se mantiene.",
            "reversed": "Apelación aceptada — penalización revertida.",
            "reduced": "Apelación parcialmente aceptada — penalización reducida.",
        }
        return PenaltyActionResponse(
            ok=True,
            message=msg_map.get(body.resolution, "Apelación resuelta."),
            adjustment_id=reversal.id if reversal else adjustment_id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e.message))
    except RuleViolationError as e:
        raise HTTPException(status_code=422, detail=str(e.message))


@router.get("", response_model=PenaltyListResponse)
def list_penalties(
    cycle_id: int | None = Query(None),
    player_id: int | None = Query(None),
    adjustment_type: str | None = Query(None),
    applied_by: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> PenaltyListResponse:
    """Listar penalizaciones con filtros opcionales."""
    result = penalty_service.list_penalties(
        session=session,
        cycle_id=cycle_id,
        player_id=player_id,
        adjustment_type=adjustment_type,
        applied_by=applied_by,
        page=page,
        page_size=page_size,
    )
    return PenaltyListResponse(**result)


@router.get("/appeals/pending", response_model=PendingAppealsResponse)
def list_pending_appeals(
    session: Session = Depends(get_session),
) -> PendingAppealsResponse:
    """Listar apelaciones pendientes de resolver."""
    result = penalty_service.list_pending_appeals(session=session)
    return PendingAppealsResponse(**result)


@router.get("/debuffs", response_model=DebuffCatalogResponse)
def get_debuff_catalog(
    session: Session = Depends(get_session),
) -> DebuffCatalogResponse:
    """Catálogo de debuffs activos para el modal de aplicar penalización."""
    items = penalty_service.list_debuff_catalog(session=session)
    return DebuffCatalogResponse(total=len(items), items=items)
