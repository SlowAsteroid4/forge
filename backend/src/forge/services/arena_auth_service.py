"""Lógica del login de Arena (UC-09 / WP-18).

No hay sesión de servidor ni passwords. El "login" valida que el player exista
y esté activo, registra trazabilidad en audit_log, y devuelve el perfil de sesión
(que el cliente persiste). No muta datos de negocio (sp/leaderboard/etc.).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError, RuleViolationError
from forge.db.models.audit_log import AuditLog
from forge.db.models.player import Player
from forge.repositories.player import PlayerRepository
from forge.schemas.arena_auth import ArenaSessionProfile


def list_active_players(session: Session) -> list[Player]:
    """Players activos para el grid de Arena. Los inactivos NO aparecen (AC-9.7)."""
    repo = PlayerRepository(session)
    players = repo.list_active()
    return sorted(players, key=lambda p: p.display_name.lower())


def _needs_onboarding(player: Player) -> bool:
    """True si falta clase o avatar → redirect stub a /arena/onboarding (UC-15)."""
    return player.class_code is None or player.avatar_code is None


def _build_profile(player: Player) -> ArenaSessionProfile:
    return ArenaSessionProfile(
        id=player.id,
        display_name=player.display_name,
        area=player.area,
        class_code=player.class_code,
        avatar_code=player.avatar_code,
        role=player.role,
        needs_onboarding=_needs_onboarding(player),
    )


def login(session: Session, player_id: int) -> ArenaSessionProfile:
    """Valida identidad y devuelve el perfil de sesión.

    Reglas:
    - El player debe existir (404 si no).
    - El player debe estar activo (rechaza inactivo — AC-9.7).
    Registra audit_log 'arena_login' (trazabilidad, no muta negocio).
    """
    repo = PlayerRepository(session)
    player = repo.get(player_id)
    if player is None:
        raise NotFoundError(f"Player {player_id} no existe")
    if not player.is_active:
        raise RuleViolationError(
            f"El player '{player.display_name}' está inactivo y no puede entrar a Arena"
        )

    session.add(
        AuditLog(
            event_type="arena_login",
            entity_type="player",
            entity_id=str(player.id),
            actor_player_id=player.id,
            timestamp=datetime.utcnow(),
        )
    )
    return _build_profile(player)


def logout(session: Session, player_id: int | None) -> None:
    """Cierre simbólico: no hay sesión de servidor. Solo trazabilidad."""
    session.add(
        AuditLog(
            event_type="arena_logout",
            entity_type="player",
            entity_id=str(player_id) if player_id is not None else "unknown",
            actor_player_id=player_id,
            timestamp=datetime.utcnow(),
        )
    )
