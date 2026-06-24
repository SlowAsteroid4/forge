"""Schemas Pydantic para admin de players (WP-13)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

AREA_VALUES = Literal["BE", "FE", "DESIGN", "DB", "QA", "PO", "PM"]
EMPLOYMENT_VALUES = Literal["internal", "external"]


class PlayerAdminItem(BaseModel):
    """Player con todos sus campos, marcados como editables o read-only."""

    id: int
    # Read-only: vienen de seed/Jira; no editables por el PM
    jira_account_id: str
    display_name: str
    email: str | None

    # Editables por el PM
    area: str
    employment_type: str
    is_active: bool
    is_lead: bool
    monthly_salary: float | None
    hourly_rate: float | None
    monthly_hours_cap: int | None

    model_config = {"from_attributes": True}


class PlayerAdminListResponse(BaseModel):
    players: list[PlayerAdminItem]
    total: int


class PlayerUpdateRequest(BaseModel):
    """PATCH parcial — solo campos editables por el PM."""

    area: AREA_VALUES | None = None
    employment_type: EMPLOYMENT_VALUES | None = None
    is_active: bool | None = None
    is_lead: bool | None = None
    monthly_salary: float | None = Field(default=None, ge=0)
    hourly_rate: float | None = Field(default=None, ge=0)
    monthly_hours_cap: int | None = Field(default=None, ge=0)

    @field_validator("monthly_salary", "hourly_rate", mode="before")
    @classmethod
    def allow_null(cls, v: object) -> object:
        return v


class PlayerAdminUpdateResponse(BaseModel):
    ok: bool
    message: str
    player: PlayerAdminItem
