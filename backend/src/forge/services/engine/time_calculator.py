"""
Motor de cálculo de tiempos hábiles para el engine.

Recalcula los mismos campos de tiempo que el ETL, pero operando sobre el
raw_changelog guardado en DB (no sobre el payload directo de Jira).
Reutiliza business_hours() de time_utils para el conteo de horas hábiles.

Campos calculados
─────────────────
lt_biz_hours       Lead Time: desde created_at hasta done_at
ct_biz_hours       Cycle Time: desde primera transición "In Progress" → done_at
adj_ct_biz_hours   Cycle Time ajustado: CT − blocked_biz_hours − waiting_biz_hours
dev_resp_biz_hours Zona de responsabilidad del dev: CT − qa_biz_hours − review_biz_hours
qa_biz_hours       Suma de periodos en estados QA/Testing
blocked_biz_hours  Suma de periodos en estados Blocked/Bloqueado
waiting_biz_hours  Suma de periodos en estados Waiting/Esperando
review_biz_hours   Suma de periodos en estados In Review/Code Review

Transiciones contabilizadas por estado
────────────────────────────────────────
In Progress  → primera entrada marca el inicio de CT
Done/Cerrado → marca done_at (si Jira no devuelve resolutiondate)
Blocked      → acumula blocked_biz_hours
Waiting      → acumula waiting_biz_hours
Testing/QA   → acumula qa_biz_hours
In Review    → acumula review_biz_hours
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from forge.core.time_utils import business_hours
from forge.db.models.subtask import Subtask

# ── Agrupación de estados ──────────────────────────────────────────────────
_DONE_STATUSES: frozenset[str] = frozenset(
    {"Done", "Cerrado", "Closed", "Resuelto", "Resolved"}
)
_IN_PROGRESS_STATUSES: frozenset[str] = frozenset(
    {"In Progress", "En Progreso", "En progreso"}
)
_BLOCKED_STATUSES: frozenset[str] = frozenset({"Blocked", "Bloqueado"})
_WAITING_STATUSES: frozenset[str] = frozenset({"Waiting", "Esperando"})
_QA_STATUSES: frozenset[str] = frozenset({"Testing", "QA", "To Test", "En QA"})
_REVIEW_STATUSES: frozenset[str] = frozenset({"In Review", "Code Review", "En Review"})

TimeMetricsDict = dict[str, float | datetime | None]


def recompute_time_metrics(subtask: Subtask) -> TimeMetricsDict:
    """
    Recalcular todos los campos de tiempo para una Subtask desde su raw_changelog.

    Args:
        subtask: Instancia del modelo con raw_changelog cargado.

    Returns:
        Dict con done_at y todos los campos *_biz_hours.
        Si no hay changelog o el issue no está completado, retorna ceros/None.
    """
    if not subtask.raw_changelog:
        return _empty()

    try:
        changelog_payload = json.loads(subtask.raw_changelog)
    except (json.JSONDecodeError, TypeError):
        return _empty()

    histories: list[dict[str, Any]] = changelog_payload.get("histories", [])

    # Usar created_at del modelo como referencia base
    created_at: datetime | None = _to_naive(subtask.created_at)  # type: ignore[attr-defined]
    if created_at is None:
        return _empty()

    # done_at: preferir el valor ya persistido (derivado del changelog por ETL)
    done_at: datetime | None = _to_naive(subtask.done_at)
    if done_at is None:
        done_at = _find_last_transition_to(histories, _DONE_STATUSES)
    if done_at is None:
        # Tarea no terminada → no hay tiempos de ciclo
        return _empty()

    # Lead Time: created_at → done_at
    lt_biz = business_hours(created_at, done_at)

    # Cycle Time: primera entrada a "In Progress" → done_at
    in_progress_at = _find_first_transition_to(histories, _IN_PROGRESS_STATUSES)
    ct_biz: float | None = None
    if in_progress_at:
        ct_biz = business_hours(in_progress_at, done_at)

    # Periodos por estado
    blocked_biz = _sum_status_hours(histories, _BLOCKED_STATUSES, done_at)
    waiting_biz = _sum_status_hours(histories, _WAITING_STATUSES, done_at)
    qa_biz = _sum_status_hours(histories, _QA_STATUSES, done_at)
    review_biz = _sum_status_hours(histories, _REVIEW_STATUSES, done_at)

    # CT Ajustado: CT − tiempo bloqueado − tiempo en espera
    adj_ct: float | None = None
    if ct_biz is not None:
        adj_ct = max(0.0, ct_biz - (blocked_biz or 0.0) - (waiting_biz or 0.0))

    # Dev responsibility: CT − QA − Review
    dev_resp: float | None = None
    if ct_biz is not None:
        dev_resp = max(0.0, ct_biz - (qa_biz or 0.0) - (review_biz or 0.0))

    return {
        "done_at": done_at,
        "lt_biz_hours": lt_biz,
        "ct_biz_hours": ct_biz,
        "adj_ct_biz_hours": adj_ct,
        "dev_resp_biz_hours": dev_resp,
        "qa_biz_hours": qa_biz if qa_biz and qa_biz > 0 else None,
        "blocked_biz_hours": blocked_biz if blocked_biz and blocked_biz > 0 else None,
        "waiting_biz_hours": waiting_biz if waiting_biz and waiting_biz > 0 else None,
        "review_biz_hours": review_biz if review_biz and review_biz > 0 else None,
    }


# ── Helpers privados ───────────────────────────────────────────────────────


def _parse_ts(ts_str: str | None) -> datetime | None:
    """
    Parsear timestamp de Jira a datetime NAIVE (sin tz).

    SQLite no preserva timezone en las columnas DateTime, así que los
    valores en DB (created_at, done_at) son naive. Devolvemos naive aquí
    también para que las comparaciones funcionen sin TypeError.
    """
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        # Convertir a naive: si tiene tz, descartarla preservando el wall-time
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except (ValueError, AttributeError):
        return None


def _to_naive(dt: datetime | None) -> datetime | None:
    """Asegurar que un datetime sea naive (drop tz si lo tiene)."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _sorted_histories(histories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ordenar historiales de changelog por timestamp ascendente."""
    return sorted(histories, key=lambda h: h.get("created", ""))


def _find_first_transition_to(
    histories: list[dict[str, Any]],
    target_statuses: frozenset[str],
) -> datetime | None:
    """Primera transición HACIA alguno de los estados dados."""
    for history in _sorted_histories(histories):
        for item in history.get("items", []):
            if item.get("field") == "status" and item.get("toString") in target_statuses:
                return _parse_ts(history.get("created"))
    return None


def _find_last_transition_to(
    histories: list[dict[str, Any]],
    target_statuses: frozenset[str],
) -> datetime | None:
    """Última transición HACIA alguno de los estados dados."""
    result: datetime | None = None
    for history in histories:
        for item in history.get("items", []):
            if item.get("field") == "status" and item.get("toString") in target_statuses:
                ts = _parse_ts(history.get("created"))
                if ts and (result is None or ts > result):
                    result = ts
    return result


def _sum_status_hours(
    histories: list[dict[str, Any]],
    target_statuses: frozenset[str],
    cutoff: datetime,
) -> float:
    """
    Sumar horas hábiles en los periodos donde el estado era uno de los dados.

    Un periodo comienza cuando se entra al estado y termina cuando se sale,
    o al llegar al cutoff (done_at).
    """
    periods = _collect_periods(histories, target_statuses, cutoff)
    return sum(
        business_hours(start, end)
        for start, end in periods
        if start and end and end > start
    )


def _collect_periods(
    histories: list[dict[str, Any]],
    target_statuses: frozenset[str],
    cutoff: datetime,
) -> list[tuple[datetime, datetime]]:
    """Extraer pares (entrada, salida) para un conjunto de estados."""
    periods: list[tuple[datetime, datetime]] = []
    entered_at: datetime | None = None

    for history in _sorted_histories(histories):
        ts = _parse_ts(history.get("created"))
        if ts is None:
            continue

        for item in history.get("items", []):
            if item.get("field") != "status":
                continue
            from_status: str = item.get("fromString") or ""
            to_status: str = item.get("toString") or ""

            if to_status in target_statuses and entered_at is None:
                entered_at = ts
            elif from_status in target_statuses and entered_at is not None:
                end_ts = min(ts, cutoff)
                if end_ts > entered_at:
                    periods.append((entered_at, end_ts))
                entered_at = None

    # Estado todavía activo al momento de done_at
    if entered_at is not None and cutoff > entered_at:
        periods.append((entered_at, cutoff))

    return periods


def _empty() -> TimeMetricsDict:
    """Retornar dict de métricas vacías (tarea no terminada o sin changelog)."""
    return {
        "done_at": None,
        "lt_biz_hours": None,
        "ct_biz_hours": None,
        "adj_ct_biz_hours": None,
        "dev_resp_biz_hours": None,
        "qa_biz_hours": None,
        "blocked_biz_hours": None,
        "waiting_biz_hours": None,
        "review_biz_hours": None,
    }
