"""Schemas Pydantic para el login de Arena (UC-09 / WP-18).

"Auth" en Forge = SELECCIÓN DE IDENTIDAD, sin password (modelo local OQ-03:
corre en la laptop del PM, se proyecta en weekly). No hay sesión de servidor;
la sesión vive en el cliente. Estos endpoints solo validan + devuelven el perfil.
"""

from __future__ import annotations

from pydantic import BaseModel


class ActivePlayerItem(BaseModel):
    """Player activo para el grid de selección de identidad de Arena."""

    id: int
    display_name: str
    area: str
    class_code: str | None
    avatar_code: str | None
    role: str | None

    model_config = {"from_attributes": True}


class ActivePlayersResponse(BaseModel):
    players: list[ActivePlayerItem]
    total: int


class LoginRequest(BaseModel):
    player_id: int


class LogoutRequest(BaseModel):
    # Opcional: solo para trazabilidad en audit_log. No hay sesión de servidor.
    player_id: int | None = None


class ArenaSessionProfile(BaseModel):
    """Perfil de sesión devuelto al cliente tras login. Vive en el cliente."""

    id: int
    display_name: str
    area: str
    class_code: str | None
    avatar_code: str | None
    role: str | None
    # True si falta clase o avatar → el cliente redirige a /arena/onboarding (UC-15).
    needs_onboarding: bool

    model_config = {"from_attributes": True}
