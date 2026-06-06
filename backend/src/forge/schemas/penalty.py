"""Schemas Pydantic para UC-06: penalizaciones y apelaciones."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ApplyPenaltyRequest(BaseModel):
    subtask_key: str = Field(..., description="Jira key de la subtask")
    reason: str = Field(..., min_length=30, description="Justificación (mín. 30 chars)")
    catalog_code: str | None = Field(None, description="Código de debuff D01-D16")
    custom_sp: float | None = Field(None, gt=0, description="SP custom (positivo)")

    @field_validator("reason")
    @classmethod
    def reason_min_length(cls, v: str) -> str:
        if len(v.strip()) < 30:
            raise ValueError("La razón debe tener al menos 30 caracteres.")
        return v.strip()


class ReversePenaltyRequest(BaseModel):
    reason: str = Field(..., min_length=30)
    partial_new_value: float | None = Field(
        None,
        ge=0,
        description="Si se provee: reducción parcial al nuevo valor neto. Si None: reversión total.",
    )

    @field_validator("reason")
    @classmethod
    def reason_min_length(cls, v: str) -> str:
        if len(v.strip()) < 30:
            raise ValueError("La razón debe tener al menos 30 caracteres.")
        return v.strip()


class ResolveAppealRequest(BaseModel):
    resolution: Literal["upheld", "reversed", "reduced"]
    notes: str = Field(..., min_length=30)
    reduced_value: float | None = Field(
        None,
        ge=0,
        description="Requerido si resolution='reduced': nuevo valor neto de penalización.",
    )

    @field_validator("notes")
    @classmethod
    def notes_min_length(cls, v: str) -> str:
        if len(v.strip()) < 30:
            raise ValueError("Las notas deben tener al menos 30 caracteres.")
        return v.strip()


class PenaltyListItem(BaseModel):
    id: int
    subtask_key: str | None
    subtask_summary: str | None
    cycle_id: int | None
    player_id: int | None
    player_name: str | None
    adjustment_type: str
    catalog_code: str | None
    amount_sp: float
    reason: str
    applied_by: int
    applied_by_name: str | None
    applied_at: str | None
    is_appealed: bool
    appeal_resolution: str | None
    appeal_resolved_by: int | None
    appeal_resolved_by_name: str | None
    appeal_resolved_at: str | None
    appeal_notes: str | None
    sp_final_current: float | None


class PenaltyListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[PenaltyListItem]


class PendingAppealsResponse(BaseModel):
    total: int
    items: list[PenaltyListItem]


class DebuffCatalogItem(BaseModel):
    code: str
    narrative_name: str
    trigger_description: str
    penalty_type: str
    value: float
    is_appealable: bool
    icon_code: str | None
    is_auto: bool


class DebuffCatalogResponse(BaseModel):
    total: int
    items: list[DebuffCatalogItem]


class PenaltyActionResponse(BaseModel):
    ok: bool
    message: str
    adjustment_id: int
    subtask_key: str | None = None
    sp_final: float | None = None
