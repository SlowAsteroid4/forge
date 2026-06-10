"""Pydantic schemas — UC-07: Forecast P30/P50/P85."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel


class AreaForecastSchema(BaseModel):
    area: str
    cp_done: float
    cp_pending: float
    n_cycles_data: int
    velocity_avg: float
    velocity_best: float
    velocity_cons: float
    weeks_optimistic: float
    weeks_realistic: float
    weeks_conservative: float
    date_optimistic: date
    date_realistic: date
    date_conservative: date
    preliminary: bool


class EpicForecastItem(BaseModel):
    epic_key: str
    summary: str
    project_code: str
    status: str
    epic_kind: str = "normal"
    cp_total: float
    cp_done: float
    cp_pending: float
    pct_done: float
    date_optimistic: date | None
    date_realistic: date | None
    date_conservative: date | None
    preliminary: bool
    warning: str | None
    blocked_count: int


class EpicForecastDetail(EpicForecastItem):
    areas: list[AreaForecastSchema]


class EpicForecastListResponse(BaseModel):
    epics: list[EpicForecastItem]
    total: int
    n_closed_cycles: int
    window_size: int = 4
    calculated_at: str


class RecalculateResponse(BaseModel):
    message: str
    total: int
    calculated_at: str
