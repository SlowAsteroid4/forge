"""Schemas (DTOs) para las analíticas de Flujo / Cuellos de botella (WP-07a)."""

from pydantic import BaseModel, Field


class ThroughputPoint(BaseModel):
    """Un punto de la serie temporal de throughput por ciclo."""

    cycle_id: int
    cycle_name: str
    iso_year: int
    iso_week: int
    start_date: str
    end_date: str
    status: str
    done_count: int = Field(description="Subtasks Done en el ciclo")
    total_cp: int = Field(description="CP acumulado en el ciclo")


class ThroughputResponse(BaseModel):
    """Serie temporal de throughput (CP + subtasks Done por ciclo)."""

    cycles: list[ThroughputPoint]
    total_cycles: int


class AreaBreakdown(BaseModel):
    """CP Done desglosado por área técnica."""

    area: str
    done_count: int
    total_cp: int


class CpByAreaResponse(BaseModel):
    """CP Done agrupado por área para un scope."""

    scope: str
    cycle_id: int | None = None
    areas: list[AreaBreakdown]


class DevCpPerDay(BaseModel):
    """CP por día hábil de un dev en el scope."""

    player_id: int
    display_name: str
    area: str
    done_count: int
    total_cp: int
    biz_days: int
    cp_per_day: float


class CpPerDayResponse(BaseModel):
    """CP normalizado por días hábiles para cada dev en el scope."""

    scope: str
    biz_days: int
    devs: list[DevCpPerDay]


class DevQaFirstPass(BaseModel):
    """QA first-pass de un dev en el scope."""

    player_id: int
    display_name: str
    area: str
    total: int = Field(description="Subtasks Done con dato de QA")
    passed: int = Field(description="Subtasks que pasaron QA en primer intento")
    first_pass_pct: float = Field(description="% first-pass (0–100)")


class QaFirstPassResponse(BaseModel):
    """QA first-pass por dev en el scope dado."""

    scope: str
    devs: list[DevQaFirstPass]


class TimeInStatusRow(BaseModel):
    """Horas por bucket de estado para un grupo (área o dev)."""

    group_key: str
    display_name: str
    area: str | None = None
    done_count: int
    dev_resp_h: float
    qa_h: float
    review_h: float
    blocked_h: float
    waiting_h: float
    total_h: float


class TimeInStatusResponse(BaseModel):
    """Tiempo en cada bucket de estado por área o dev.

    Orden: de mayor tiempo total a menor (primero = mayor cuello de botella).
    """

    scope: str
    group_by: str
    rows: list[TimeInStatusRow]
    bucket_definitions: dict[str, str] = Field(
        default={
            "dev_resp_h": "Cycle Time - QA - Review (zona del dev)",
            "qa_h": "Testing / In QA / Ready for QA",
            "review_h": "In Review / Code Review",
            "blocked_h": "Blocked / Bloqueado",
            "waiting_h": "Waiting / Esperando",
        }
    )


class StatusDetailRow(BaseModel):
    """Horas por estado Jira específico para un grupo (desde raw_changelog)."""

    group_key: str
    display_name: str
    area: str | None = None
    done_count: int
    total_h: float
    by_status: dict[str, float] = Field(description="Horas por nombre de estado Jira")


class TimeInStatusDetailResponse(BaseModel):
    """Tiempo por estado Jira específico (parseo de raw_changelog).

    Granularidad fina (ej. 'Ready for QA', 'Active', 'In Design').
    """

    scope: str
    group_by: str
    rows: list[StatusDetailRow]


# ──────────────────────────────────────────────────────────────
# WP-17a — Quality, comparativas vs ciclo anterior, agrupación canónica
# ──────────────────────────────────────────────────────────────


class CycleBrief(BaseModel):
    """Identificación mínima de un ciclo para comparativas."""

    cycle_id: int
    name: str
    iso_year: int
    iso_week: int
    status: str


class DeltaMetric(BaseModel):
    """Una métrica con su comparativa vs ciclo anterior.

    previous/delta_* = None ⇒ "sin comparativa" (no hay ciclo previo o base 0).
    """

    current: float
    previous: float | None = None
    delta_abs: float | None = None
    delta_pct: float | None = None


class QualitySummaryResponse(BaseModel):
    """Sección Quality propia: probadas / por probar / tiempo prom. en QA + vs anterior."""

    reference_cycle: CycleBrief | None = None
    previous_cycle: CycleBrief | None = None
    tested: DeltaMetric = Field(description="PROBADAS: Done con paso por QA en el ciclo")
    pending: DeltaMetric = Field(description="POR PROBAR: en cola de QA ahora (In QA / Ready for QA)")
    avg_qa_hours: DeltaMetric = Field(description="Horas hábiles promedio en QA (qa_biz_hours)")


class DevQaVsPrevious(BaseModel):
    """QA first-pass de un dev: ciclo actual vs anterior."""

    player_id: int
    display_name: str
    area: str
    total: int
    passed: int
    first_pass_pct: float
    previous_pct: float | None = None
    delta_pts: float | None = Field(default=None, description="Diferencia en puntos vs anterior")


class QaFirstPassVsPreviousResponse(BaseModel):
    """QA first-pass por dev comparado contra el ciclo anterior."""

    reference_cycle: CycleBrief | None = None
    previous_cycle: CycleBrief | None = None
    devs: list[DevQaVsPrevious]


class CanonicalTimeRow(BaseModel):
    """Horas por estado canónico para un grupo (área o dev)."""

    group_key: str
    display_name: str
    area: str | None = None
    done_count: int
    by_canonical: dict[str, float] = Field(
        description="Horas por estado canónico (In Progress/In Review/In QA/Blocked/Waiting)"
    )
    total_h: float


class CanonicalTimeResponse(BaseModel):
    """Tiempo agrupado por estado canónico del Manifiesto JPDS (capa de display).

    Las horas provienen de los buckets WP-07h sin alterar la atribución.
    """

    scope: str
    group_by: str
    area_filter: str | None = None
    rows: list[CanonicalTimeRow]


# ──────────────────────────────────────────────────────────────
# WP-17b — apartado, cycle/lead time, métricas por dev
# ──────────────────────────────────────────────────────────────


class ApartadoOption(BaseModel):
    """Un apartado (sub-división de YAP) con su conteo de subtasks."""

    apartado: str
    subtask_count: int


class ApartadosResponse(BaseModel):
    """Apartados disponibles para el filtro (incluye 'Sin apartado')."""

    apartados: list[ApartadoOption]


class CycleLeadStats(BaseModel):
    """Cycle/Lead time agregados de un conjunto de subtasks Done."""

    done_count: int
    cycle_avg_h: float | None = None
    cycle_median_h: float | None = None
    lead_avg_h: float | None = None
    lead_median_h: float | None = None


class CycleLeadPeriod(CycleLeadStats):
    """Un periodo (ciclo / mes) en la serie de cycle/lead time."""

    key: str
    label: str
    cycle_id: int | None = None


class CycleLeadTimeResponse(BaseModel):
    """Cycle time (In Progress→Done) y Lead time (Backlog→Done) en horas hábiles.

    Detección canónica desde raw_changelog (no reusa ct/lt de WP-07h). `overall` es
    el agregado histórico de todo el conjunto filtrado.
    """

    grouping: str
    apartado: str | None = None
    area: str | None = None
    periods: list[CycleLeadPeriod]
    overall: CycleLeadStats


class DevListItem(BaseModel):
    """Un dev con subtasks Done (para el selector)."""

    player_id: int
    display_name: str
    area: str
    done_count: int


class DevListResponse(BaseModel):
    """Devs disponibles para métricas por dev."""

    devs: list[DevListItem]


class DevStateRow(BaseModel):
    """Tiempo promedio de un dev en un estado (crudo o canónico)."""

    status: str
    canonical: str | None = None
    avg_h: float
    total_h: float
    n: int = Field(description="Subtasks que pasaron por este estado")


class DevMetricsResponse(BaseModel):
    """Métricas promedio de un dev: tiempo por estado crudo (37) y canónico (9)."""

    player_id: int
    display_name: str
    area: str
    is_aggregate: bool = Field(description="True para cuentas-grupo (Equipo de Producto)")
    scope: str
    apartado: str | None = None
    done_count: int
    cycle_avg_h: float | None = None
    lead_avg_h: float | None = None
    qa_first_pass_pct: float | None = None
    raw_states: list[DevStateRow]
    canonical_states: list[DevStateRow]
