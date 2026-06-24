"""Schemas Pydantic para UC-16 Pulso Operativo (rediseño WP-16, WIP fix WP-20)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ── CAMBIO 1: Franja de contadores por estado (orden de flujo) ─────────────────


class FlowCounter(BaseModel):
    """Un contador de la franja de flujo (Backlog → Done)."""

    key: str = Field(description="Clave estable del paso de flujo, ej. 'in_progress'")
    label: str = Field(description="Etiqueta visible, ej. 'In Progress'")
    count: int = Field(description="Subtasks en este paso AHORA")
    raw_statuses: list[str] = Field(
        description="Statuses reales de Jira plegados en este contador (auditable)"
    )
    zone: str = Field(description="Zona de color JPDS: neutral/dev/review/qa/done")


# ── CAMBIO 2: Cards por área (reemplaza WIP/semáforo) ──────────────────────────


class AreaTask(BaseModel):
    """Fila de tarea dentro de un grupo-por-estado de una card de área."""

    jira_key: str
    summary: str
    status: str
    zone: str = Field(description="Zona de color JPDS del estado")
    assignee_name: str | None
    assignee_player_id: int | None
    is_aggregate_team: bool = Field(
        default=False,
        description="True si el dueño es una cuenta-grupo agregada (ej. 'Equipo de Producto')",
    )


class AreaStatusGroup(BaseModel):
    """Agrupación de tareas de un área por estado."""

    status: str
    zone: str
    count: int
    tasks: list[AreaTask]


class AreaCard(BaseModel):
    """Card de un área: tareas activas asignadas → expand por estado → código+dueño.

    WP-20: agrega wip_count, wip_limit, semaphore y n_devs_over_limit.
    """

    area: str
    total_active: int = Field(description="Total de tareas activas en el área (excl. Backlog/Done)")
    wip_count: int = Field(default=0, description="Tareas WIP (In Progress + In Code) en el área")
    wip_limit: int = Field(default=0, description="Límite de WIP configurado para el área")
    semaphore: str = Field(
        default="green",
        description="Color semáforo del área: green/yellow/red. Rojo si algún dev supera su límite.",
    )
    n_devs_over_limit: int = Field(
        default=0, description="Devs cuyo WIP individual excede el límite del área"
    )
    by_status: list[AreaStatusGroup] = Field(description="Grupos por estado en orden de flujo")


# ── CAMBIO 3: Drill-down de dev ────────────────────────────────────────────────


class DevTask(BaseModel):
    jira_key: str
    summary: str
    status: str
    zone: str
    area: str
    dias_en_estado: float = Field(description="Días hábiles en el estado actual")


class DevWipSummary(BaseModel):
    """Resumen WIP por dev (WP-20). Solo wip dispara color de semáforo."""

    wip: int = Field(description="Trabajo activo: In Progress + In Code")
    review: int = Field(description="En revisión: In Review")
    qa: int = Field(description="En QA: Ready for QA + In QA")
    waiting: int = Field(description="En espera: Waiting")
    ready: int = Field(description="Listos para dev: Ready")
    wip_limit: int = Field(description="Límite de WIP del área del dev")
    semaphore: str = Field(
        description="verde/amarillo/rojo. Verde: WIP < límite. Amarillo: WIP == límite. Rojo: WIP > límite."
    )


class DevDrilldown(BaseModel):
    player_id: int
    display_name: str
    is_aggregate_team: bool = Field(
        default=False, description="True si es cuenta-grupo agregada"
    )
    area: str | None
    total: int = Field(description="Total de tareas operativas del dev (excl. Backlog/Done)")
    wip_summary: DevWipSummary = Field(description="WP-20: WIP canónico + semáforo")
    tasks: list[DevTask] = Field(description="Tareas en progreso del dev, con estatus")


# ── Secciones conservadas (sin cambios funcionales) ────────────────────────────


class BlockItem(BaseModel):
    jira_key: str
    summary: str
    area: str
    assignee_name: str | None
    assignee_player_id: int | None
    horas_bloqueado: float
    es_critico: bool = Field(description="True si horas_bloqueado >= 8h habiles")
    block_reason: str | None = Field(
        default=None,
        description="Razon del bloqueo. HUECO: Jira no expone este campo en changelog.",
    )


class DayMovementItem(BaseModel):
    jira_key: str
    summary: str
    area: str
    assignee_name: str | None
    from_status: str
    to_status: str
    moved_at: datetime


class AgingItem(BaseModel):
    jira_key: str
    summary: str
    area: str
    status: str
    assignee_name: str | None
    assignee_player_id: int | None
    dias_en_estado: float = Field(description="Dias habiles en el estado actual")
    edad_total_dias: float = Field(description="Dias habiles desde created_at")


class ReadyQueueItem(BaseModel):
    jira_key: str
    summary: str
    area: str
    cp: int | None
    assignee_name: str | None
    tiempo_en_ready_horas: float
    priority: str | None = Field(default=None, description="Prioridad Jira (Highest/High/Medium/Low/Lowest)")


class FlagForReviewRequest(BaseModel):
    note: str | None = Field(default=None, description="Nota opcional del PM/TL")


class FlagForReviewResponse(BaseModel):
    jira_key: str
    audit_log_id: int
    message: str


class PulseSnapshot(BaseModel):
    generated_at: datetime
    filters_applied: dict[str, Any]
    flow_counters: list[FlowCounter] = Field(description="CAMBIO 1: franja por estado")
    area_cards: list[AreaCard] = Field(description="CAMBIO 2: cards por área")
    blocks: list[BlockItem]
    day_movements: list[DayMovementItem]
    aging_critical: list[AgingItem]
    ready_queue: list[ReadyQueueItem]
