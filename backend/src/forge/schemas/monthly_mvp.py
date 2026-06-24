"""Schemas Pydantic para UC-17: cierre mensual y MVP del Mes."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MonthlyCandidate(BaseModel):
    player_id: int
    display_name: str
    area: str
    mvp_cycles: list[str]
    mvp_cycle_ids: list[int]
    sp_total_month: float
    cp_total_month: int
    subtasks_done_month: int
    avg_m_calidad: float | None
    metric_highlight: str


class MonthCycleInfo(BaseModel):
    cycle_id: int
    name: str
    status: str
    mvp_player_id: int | None


class MonthKPIs(BaseModel):
    cp_done: int
    sp_generated: float
    subtasks_done: int
    cycles_total: int
    cycles_closed_or_archived: int


class MonthCloseSummary(BaseModel):
    year: int
    month: int
    period_label: str
    cycles: list[MonthCycleInfo]
    kpis: MonthKPIs
    candidates: list[MonthlyCandidate]
    already_closed: bool
    can_close: bool
    blocking_errors: list[str]
    warnings: list[str]


class MonthCloseRequest(BaseModel):
    mvp_player_id: int
    reason: str = Field(..., min_length=30, description="Justificación mínimo 30 caracteres")


class MonthlyMvpEditRequest(BaseModel):
    new_player_id: int
    reason: str = Field(..., min_length=30, description="Justificación mínimo 30 caracteres")


class MonthlyMvpHistoryItem(BaseModel):
    id: int
    period_label: str
    year: int
    month: int
    player_id: int
    display_name: str
    area: str | None
    reason: str | None
    sp_reward: int
    assigned_at: datetime
    assigned_by_name: str
    source_cycle_ids: list[int]


class MonthCloseResponse(BaseModel):
    period_label: str
    player_id: int
    display_name: str
    sp_awarded: float
    ach04_unlocked: bool
    message: str
