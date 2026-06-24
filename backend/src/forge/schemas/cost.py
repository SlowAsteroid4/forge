"""Schemas Pydantic para UC-08: Costos por área."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class PlayerCostItem(BaseModel):
    player_id: int
    display_name: str
    area: str
    employment_type: str
    cp_total: int
    sp_total: float
    done_subtasks: int
    cost_total: float | None
    cost_per_cp: float | None
    cost_per_sp: float | None
    cost_not_captured: bool
    no_production: bool
    cost_note: str | None


class AreaCostItem(BaseModel):
    area: str
    players_active: int
    cp_total: int
    sp_total: float
    done_subtasks: int
    cost_total: float | None
    cost_per_cp: float | None
    cost_per_sp: float | None
    delta_pct: float | None
    players: list[PlayerCostItem]


class AreaCostResponse(BaseModel):
    areas: list[AreaCostItem]
    period: str
    period_start: date
    period_end: date
    has_any_cost: bool
    total_cp: int
    total_cost: float | None


class DevCostResponse(BaseModel):
    players: list[PlayerCostItem]
    period: str
    period_start: date
    period_end: date


class IntExtComparisonItem(BaseModel):
    area: str
    int_cost_per_cp: float | None
    ext_cost_per_cp: float | None
    int_players: int
    ext_players: int
    multiplier: float | None
    insight: str


class ComparisonResponse(BaseModel):
    comparisons: list[IntExtComparisonItem]
    period: str
    period_start: date
    period_end: date


class EvolutionPointItem(BaseModel):
    period_label: str
    period_start: date
    period_end: date
    cp_total: int
    cost_total: float | None
    cost_per_cp: float | None


class EvolutionResponse(BaseModel):
    points: list[EvolutionPointItem]
    area: str | None
