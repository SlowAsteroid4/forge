"""Schemas del worklist de CP (WP-24): subtasks sin CP por apartado + XXL."""

from pydantic import BaseModel


class CpWorklistItem(BaseModel):
    """Subtask sin CP asignado (cp IS NULL) — read-only."""

    jira_key: str
    summary: str
    area: str
    status: str
    assignee_player_id: int | None
    assignee_name: str | None
    age_days: int  # días desde el import a la BD (created_at NO es la creación en Jira)


class ApartadoGroup(BaseModel):
    """Grupo de subtasks sin CP bajo un apartado derivado (ADR-012)."""

    apartado: str
    known: bool
    count: int
    items: list[CpWorklistItem]


class XxlWorklistItem(BaseModel):
    """Subtask XXL detectada — talla rechazada, requiere ruptura."""

    jira_key: str
    summary: str
    area: str
    status: str
    assignee_player_id: int | None
    assignee_name: str | None
    cp: int | None


class CpWorklistResponse(BaseModel):
    """GET /api/cp-worklist — agrupado por apartado + sección XXL."""

    total: int
    groups: list[ApartadoGroup]
    xxl_total: int
    xxl_items: list[XxlWorklistItem]
    jira_base_url: str | None
