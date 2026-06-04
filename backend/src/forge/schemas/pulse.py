"""Schemas Pydantic para UC-16 Pulso Operativo."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PulseGlobals(BaseModel):
    activas: int = Field(description="Subtasks en estados activos (WIP + blocked)")
    bloqueadas: int = Field(description="Subtasks en status Blocked")
    en_espera: int = Field(description="Subtasks en status Waiting (actualmente 0 — hueco de datos)")
    cola_ready: int = Field(description="Subtasks en status Ready")
    aging_max_dias_habiles: float = Field(description="Maximo dias habiles en estado actual (activas)")


class WipAreaCard(BaseModel):
    area: str
    wip_actual: int = Field(description="Total subtasks activas asignadas en el area (excluye sin asignee)")
    wip_limit: int = Field(description="Limite WIP por dev (no por area)")
    max_wip_individual: int = Field(description="WIP mas alto de cualquier dev en el area")
    devs_over_limit: int = Field(description="Devs en el area que exceden su limite individual")
    pct_utilization: float = Field(description="max_wip_individual / wip_limit * 100 (base del semaforo)")
    semaforo: str = Field(description="verde: ningun dev excede; amarillo: alguien en el limite; rojo: alguien excede")
    activas: list[dict[str, Any]] = Field(description="Detalle de subtasks activas asignadas en el area")
    assignee_count: int = Field(description="Numero de devs distintos con WIP en el area")


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
    priority: str | None = Field(
        default=None,
        description="Prioridad Jira. HUECO: campo no existe en el modelo actual.",
    )


class PulseSnapshot(BaseModel):
    generated_at: datetime
    filters_applied: dict[str, Any]
    globals: PulseGlobals
    wip_by_area: list[WipAreaCard]
    blocks: list[BlockItem]
    day_movements: list[DayMovementItem]
    aging_critical: list[AgingItem]
    ready_queue: list[ReadyQueueItem]
