"""Extracción de métricas de tiempo desde changelog de Jira."""

from datetime import datetime
from typing import Any

from forge.core.time_utils import business_hours


_DONE_STATUSES = frozenset({"Done", "Cerrado", "Closed", "Resuelto", "Resolved"})


def extract_time_metrics(issue: dict[str, Any]) -> dict[str, float | datetime | None]:
    """
    Extraer métricas de tiempo desde changelog.

    Args:
        issue: Payload completo de Jira con changelog expandido

    Returns:
        Dict con done_at, lt_biz_hours, ct_biz_hours, adj_ct_biz_hours, etc.
        `done_at` se deriva de resolutiondate o, si está vacío, de la última
        transición al estado "Done" en el changelog.
    """
    changelog = issue.get("changelog", {}).get("histories", [])
    fields = issue.get("fields", {})

    # Timestamps clave
    created = _parse_jira_datetime(fields.get("created"))

    # done_at: preferir resolutiondate; caer en última transición a Done
    done_at: datetime | None = _parse_jira_datetime(fields.get("resolutiondate"))
    if done_at is None:
        done_at = _find_last_transition_to(changelog, _DONE_STATUSES)

    if not created:
        return _empty_metrics()

    # Detectar transiciones relevantes
    in_progress_at = _find_transition_to(changelog, "In Progress", created)
    blocked_periods = _find_blocked_periods(changelog)
    waiting_periods = _find_waiting_periods(changelog)
    qa_periods = _find_status_periods(changelog, ["Testing", "QA", "To Test"])
    review_periods = _find_status_periods(changelog, ["In Review", "Code Review"])

    if not done_at:
        # Issue no terminado
        return _empty_metrics()

    # Calcular tiempos
    lt_biz = business_hours(created, done_at) if created and done_at else None
    ct_biz = business_hours(in_progress_at, done_at) if in_progress_at and done_at else None

    # Tiempo bloqueado y waiting
    blocked_biz = _sum_period_hours(blocked_periods)
    waiting_biz = _sum_period_hours(waiting_periods)
    qa_biz = _sum_period_hours(qa_periods)
    review_biz = _sum_period_hours(review_periods)

    # Cycle ajustado (sin blocked/waiting)
    adj_ct_biz = None
    if ct_biz is not None:
        adj_ct_biz = max(0, ct_biz - (blocked_biz or 0) - (waiting_biz or 0))

    # Dev responsability: cycle - qa - review
    dev_resp_biz = None
    if ct_biz is not None:
        dev_resp_biz = max(0, ct_biz - (qa_biz or 0) - (review_biz or 0))

    return {
        "done_at": done_at,
        "lt_biz_hours": lt_biz,
        "ct_biz_hours": ct_biz,
        "adj_ct_biz_hours": adj_ct_biz,
        "dev_resp_biz_hours": dev_resp_biz,
        "qa_biz_hours": qa_biz,
        "blocked_biz_hours": blocked_biz,
        "waiting_biz_hours": waiting_biz,
        "review_biz_hours": review_biz,
    }


def _parse_jira_datetime(date_str: str | None) -> datetime | None:
    """Parsear fecha de Jira a datetime."""
    if not date_str:
        return None
    try:
        # Formato típico: 2024-01-15T14:30:00.000-0600
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except:
        return None


def _find_last_transition_to(
    changelog: list, statuses: frozenset[str]
) -> datetime | None:
    """Encontrar la ÚLTIMA transición a cualquiera de los estados dados."""
    result: datetime | None = None
    for history in changelog:
        for item in history.get("items", []):
            if item.get("field") == "status" and item.get("toString") in statuses:
                ts = _parse_jira_datetime(history.get("created"))
                if ts and (result is None or ts > result):
                    result = ts
    return result


def _find_transition_to(changelog: list, to_status: str, default: datetime) -> datetime:
    """Encontrar primera transición a un estado."""
    for history in changelog:
        for item in history.get("items", []):
            if item.get("field") == "status" and item.get("toString") == to_status:
                return _parse_jira_datetime(history.get("created")) or default
    return default


def _find_blocked_periods(changelog: list) -> list[tuple[datetime, datetime]]:
    """Encontrar periodos en estado 'Blocked'."""
    return _find_status_periods(changelog, ["Blocked", "Bloqueado"])


def _find_waiting_periods(changelog: list) -> list[tuple[datetime, datetime]]:
    """Encontrar periodos en estado 'Waiting'."""
    return _find_status_periods(changelog, ["Waiting", "Esperando"])


def _find_status_periods(changelog: list, statuses: list[str]) -> list[tuple[datetime, datetime]]:
    """Encontrar periodos en ciertos estados."""
    periods = []
    current_start = None

    for history in sorted(changelog, key=lambda h: h.get("created", "")):
        for item in history.get("items", []):
            if item.get("field") != "status":
                continue

            from_status = item.get("fromString")
            to_status = item.get("toString")
            timestamp = _parse_jira_datetime(history.get("created"))

            if to_status in statuses and current_start is None:
                current_start = timestamp
            elif from_status in statuses and current_start is not None:
                if timestamp:
                    periods.append((current_start, timestamp))
                current_start = None

    return periods


def _sum_period_hours(periods: list[tuple[datetime, datetime]]) -> float | None:
    """Sumar horas hábiles de periodos."""
    if not periods:
        return None
    total = sum(business_hours(start, end) for start, end in periods if start and end)
    return total if total > 0 else None


def _empty_metrics() -> dict[str, None]:
    """Retornar métricas vacías."""
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
