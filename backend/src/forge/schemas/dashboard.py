"""Schemas de respuesta para UC-02: Dashboard del sprint."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Bloques base
# ──────────────────────────────────────────────


class SprintSummary(BaseModel):
    """Sprint reducido para el selector de sprints."""

    id: int
    name: str
    start_date: date
    end_date: date
    is_closed: bool


class SprintHeader(BaseModel):
    """Header del sprint con progreso temporal."""

    id: int
    name: str
    start_date: date
    end_date: date
    days_elapsed: int
    days_total: int
    progress_pct: float = Field(ge=0, le=100, description="% de días transcurridos")


class KPIValue(BaseModel):
    """Valor de un KPI con comparativa vs sprint anterior."""

    value: float
    previous_value: float | None = None
    delta_pct: float | None = Field(
        default=None,
        description="Variación porcentual vs sprint anterior (+positivo = mejora)",
    )


class KPICards(BaseModel):
    """4 KPI cards principales del dashboard."""

    cp_done: KPIValue
    cp_pending: float = Field(description="CP de subtasks aún no terminadas")
    sp_total: float = Field(description="SP acumulado en subtasks Done del sprint")
    bugs_derived: int = Field(description="Cantidad de Bug Sub-tasks en el sprint")


class AreaProgress(BaseModel):
    """Progreso de un área técnica en el sprint."""

    area: str
    cp_done: float
    cp_total: float
    progress_pct: float = Field(ge=0, le=100)
    active_devs: int = Field(description="Devs con al menos 1 subtask activa")
    has_wip_bottleneck: bool = Field(description="Algún dev del área excede el WIP máximo")


PlayerStatusEnum = Literal["productive", "wip_high", "blocked", "inactive"]


class PlayerStatus(BaseModel):
    """Estado de un developer en el sprint actual."""

    player_id: int
    display_name: str
    area: str
    avatar_code: str | None = None
    active_subtasks: int = Field(description="Subtasks no terminadas (no Done/Cancelled)")
    done_subtasks: int = Field(description="Subtasks Done en el sprint")
    sp_sprint: float = Field(description="SP acumulado en el sprint")
    status: PlayerStatusEnum


AlertTypeEnum = Literal[
    "abandoned_subtask",
    "waiting_long",
    "wip_exceeded",
    "cp_pending_approval",
    "bug_unattributed",
]


class AlertItem(BaseModel):
    """Alerta accionable del dashboard."""

    alert_type: AlertTypeEnum
    severity: Literal["warning", "critical"]
    message: str
    subtask_key: str | None = None
    player_id: int | None = None


class ProjectSummary(BaseModel):
    """Proyecto resumido para el filtro global."""

    code: str
    internal_name: str
    jira_prefix: str


# ──────────────────────────────────────────────
# Respuesta principal
# ──────────────────────────────────────────────


class DashboardResponse(BaseModel):
    """Respuesta completa del UC-02 dashboard.

    Cuando no hay sprint activo, `sprint` es None y `no_sprint_message`
    indica el motivo. El frontend renderiza el empty state.
    """

    sprint: SprintHeader | None = None
    no_sprint_message: str | None = None

    kpis: KPICards | None = None
    area_progress: list[AreaProgress] = []
    player_status: list[PlayerStatus] = []
    alerts: list[AlertItem] = []

    available_projects: list[ProjectSummary] = []
    available_sprints: list[SprintSummary] = []
    last_synced_at: datetime | None = Field(
        default=None,
        description="Timestamp del último sync contra Jira",
    )
