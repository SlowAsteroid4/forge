"""Router admin de players — WP-13."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError, RuleViolationError
from forge.db.session import get_session
from forge.schemas.player_admin import (
    PlayerAdminItem,
    PlayerAdminListResponse,
    PlayerAdminUpdateResponse,
    PlayerUpdateRequest,
)
from forge.services import player_admin_service

router = APIRouter(tags=["player-admin"])

# Hardcoded hasta WP-08 auth
_DEFAULT_ADMIN_ID = 1


@router.get("/players", response_model=PlayerAdminListResponse)
def list_players(
    area: str | None = Query(default=None),
    employment_type: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    session: Session = Depends(get_session),
) -> PlayerAdminListResponse:
    """Listar todos los players con filtros opcionales."""
    players = player_admin_service.list_players(
        session=session,
        area=area,
        employment_type=employment_type,
        is_active=is_active,
    )
    return PlayerAdminListResponse(
        players=[PlayerAdminItem.model_validate(p) for p in players],
        total=len(players),
    )


@router.get("/players/{player_id}", response_model=PlayerAdminItem)
def get_player(
    player_id: int,
    session: Session = Depends(get_session),
) -> PlayerAdminItem:
    """Obtener detalle de un player."""
    try:
        player = player_admin_service.get_player(session, player_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return PlayerAdminItem.model_validate(player)


@router.patch("/players/{player_id}", response_model=PlayerAdminUpdateResponse)
def update_player(
    player_id: int,
    body: PlayerUpdateRequest,
    session: Session = Depends(get_session),
) -> PlayerAdminUpdateResponse:
    """Editar campos editables de un player (PATCH parcial)."""
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    try:
        player = player_admin_service.update_player(
            session=session,
            player_id=player_id,
            patch=patch,
            admin_id=_DEFAULT_ADMIN_ID,
        )
        session.commit()
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuleViolationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return PlayerAdminUpdateResponse(
        ok=True,
        message="Player actualizado.",
        player=PlayerAdminItem.model_validate(player),
    )
