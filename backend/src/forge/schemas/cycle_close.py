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


class IssueBreakdown(BaseModel):
    """Una subtask Done que aportó CP/SP a un player en el ciclo."""

    jira_key: str
    title: str
    cp: int | None
    sp_final: float | None


class AdjustmentLine(BaseModel):
    """Ajuste de SP no atribuible a un issue (p.ej. bono MVP). amount_sp ya viene firmado."""

    label: str
    amount_sp: float


class TopPlayer(BaseModel):
    player_id: int
    display_name: str
    area: str
    sp: float
    # Drill-down (WP-23): por_issue + ajustes_no_issue reconcilian con `sp`.
    por_issue: list[IssueBreakdown] = []
    ajustes_no_issue: list[AdjustmentLine] = []


class BlockingError(BaseModel):
    """Error bloqueante estructurado (WP-23). issue_keys vacío si la regla no es por issue."""

    type: str
    message: str
    issue_keys: list[str] = []


class CycleCloseSummary(BaseModel):
    cycle_id: int
    cycle_name: str
    cycle_status: str
    kpis: CycleKPIs
    top_players: list[TopPlayer]
    can_close: bool
    blocking_errors: list[BlockingError]
    warnings: list[str]
    # Base URL de Jira para construir links /browse/{key}; None si no está configurada.
    jira_base_url: str | None = None


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


class CycleRecalcResponse(BaseModel):
    """Resultado del recalc contextual del cierre (WP-23)."""

    cycle_id: int
    recalculated: int  # subtasks que el motor escribió (Done sin sp_final)
    message: str
    summary: CycleCloseSummary  # estado de validación re-ejecutado tras el recalc
