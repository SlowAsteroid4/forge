"""Schemas Pydantic para UC-05: cierre de ciclo y MVP semanal."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CycleCandidate(BaseModel):
    player_id: int
    display_name: str
    area: str
    sp_total: float
    cp_total: int
    subtasks_done: int
    avg_m_calidad: float | None
    metric_highlight: str


class CycleKPIs(BaseModel):
    cp_done: int
    sp_generated: float
    subtasks_done: int
    bugs_derived: int


class TopPlayer(BaseModel):
    player_id: int
    display_name: str
    area: str
    sp: float


class CycleCloseSummary(BaseModel):
    cycle_id: int
    cycle_name: str
    cycle_status: str
    kpis: CycleKPIs
    top_players: list[TopPlayer]
    can_close: bool
    blocking_errors: list[str]
    warnings: list[str]


class CycleCloseRequest(BaseModel):
    mvp_player_id: int
    mvp_reason: str = Field(..., min_length=20)


class MvpEditRequest(BaseModel):
    new_mvp_player_id: int
    reason: str = Field(..., min_length=20)


class MvpHistoryItem(BaseModel):
    cycle_id: int
    cycle_name: str
    closed_at: datetime | None
    mvp_player_id: int
    mvp_display_name: str
    mvp_area: str
    mvp_reason: str | None


class CycleCloseResponse(BaseModel):
    cycle_id: int
    cycle_name: str
    status: str
    closed_at: datetime | None
    mvp_player_id: int | None
    mvp_reason: str | None
    message: str
