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
