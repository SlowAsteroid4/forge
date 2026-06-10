"""Router del login de Arena (UC-09 / WP-18).

Selección de identidad sin password. No crea sesión de servidor: valida + devuelve
el perfil que el cliente persiste. Rutas montadas bajo {api_v1_prefix} (=/api):
  GET  /api/players/active
  POST /api/arena/login
  POST /api/arena/logout
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError, RuleViolationError
from forge.db.session import get_session
from forge.schemas.arena_auth import (
    ActivePlayerItem,
    ActivePlayersResponse,
    ArenaSessionProfile,
    LoginRequest,
    LogoutRequest,
)
from forge.services import arena_auth_service

router = APIRouter(tags=["arena-auth"])


@router.get("/players/active", response_model=ActivePlayersResponse)
def list_active_players(
    session: Session = Depends(get_session),
) -> ActivePlayersResponse:
    """Players activos para el grid de Arena (AC-9.7: inactivos no aparecen)."""
    players = arena_auth_service.list_active_players(session)
    return ActivePlayersResponse(
        players=[ActivePlayerItem.model_validate(p) for p in players],
        total=len(players),
    )


@router.post("/arena/login", response_model=ArenaSessionProfile)
def arena_login(
    body: LoginRequest,
    session: Session = Depends(get_session),
) -> ArenaSessionProfile:
    """Login por selección de identidad. Valida activo y devuelve needs_onboarding."""
    try:
        profile = arena_auth_service.login(session, body.player_id)
        session.commit()
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except RuleViolationError as e:
        raise HTTPException(status_code=403, detail=e.message) from e
    return profile


@router.post("/arena/logout")
def arena_logout(
    body: LogoutRequest,
    session: Session = Depends(get_session),
) -> dict[str, bool]:
    """Logout simbólico (no hay sesión de servidor); registra trazabilidad."""
    arena_auth_service.logout(session, body.player_id)
    session.commit()
    return {"ok": True}
