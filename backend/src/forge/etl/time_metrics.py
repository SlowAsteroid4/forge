"""Extracción de métricas de tiempo desde changelog de Jira."""

from datetime import datetime
from typing import Any

from forge.core.time_utils import business_hours

_DONE_STATUSES = frozenset({"Done", "Cerrado", "Closed", "Resuelto", "Resolved"})

# ──────────────────────────────────────────────────────────────────────────────
# JPDS — Atribución del tiempo de QA (Decisión WP-07h)
#
# "Ready for QA" = cola de handoff dev→QA.
#   Responsabilidad del DEV: es su cuello real (tarjeta esperando a ser tomada).
#   Se acumula en ready_for_qa_biz_hours y permanece DENTRO de dev_resp_biz_hours.
#
# "In QA" / "Testing" = revisión activa de QA (Edgar).
#   Responsabilidad de QA/Edgar, NO del dev.
#   Se acumula en qa_biz_hours y se EXCLUYE de dev_resp_biz_hours.
#   Evidencia: WP-07d confirmó que el changelog registra el cambio de assignee
#   a Edgar justo al entrar a "In QA". Atribuimos por convención de estado.
# ──────────────────────────────────────────────────────────────────────────────

# Cola del dev antes de que QA tome la tarjeta — cuenta para el dev
HANDOFF_QA_STATES: list[str] = ["Ready for QA"]

# Revisión activa de QA/Edgar — cuenta para QA, NO para el dev
# "Testing" se usa en flujos de PO/Design con el mismo significado de revisión activa
ACTIVE_QA_STATES: list[str] = ["In QA", "Testing"]


def extract_time_metrics(issue: dict[str, Any]) -> dict[str, float | datetime | None]:
    """Extraer métricas de tiempo desde changelog de Jira.

    Args:
        issue: Payload completo de Jira con changelog expandido.

    Returns:
        Dict con los buckets de tiempo (horas hábiles):

        Buckets de tiempo:
          done_at             — datetime de resolución
          lt_biz_hours        — Lead Time (created → done)
          ct_biz_hours        — Cycle Time (in_progress → done)
          adj_ct_biz_hours    — CT ajustado (sin blocked/waiting)
          dev_resp_biz_hours  — Zona de responsabilidad del dev:
                                CT - qa_biz (In QA) - review_biz
                                Incluye ready_for_qa_biz (es el cuello del dev)
          ready_for_qa_biz_hours — Tiempo en cola "Ready for QA" (dev → QA handoff)
          qa_biz_hours        — Revisión activa en "In QA"/"Testing" (tiempo de Edgar/QA)
          blocked_biz_hours   — Tiempo bloqueado
          waiting_biz_hours   — Tiempo en espera
          review_biz_hours    — Tiempo en Code Review / In Review

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
    # QA activo (In QA / Testing) — tiempo de Edgar, excluido de dev_resp
    qa_active_periods = _find_status_periods(changelog, ACTIVE_QA_STATES)
    # Handoff dev→QA (Ready for QA) — cuello del dev, incluido en dev_resp
    qa_handoff_periods = _find_status_periods(changelog, HANDOFF_QA_STATES)
    review_periods = _find_status_periods(changelog, ["In Review", "Code Review"])

    if not done_at:
        # Issue no terminado
        return _empty_metrics()

    # Calcular tiempos
    lt_biz = business_hours(created, done_at) if created and done_at else None
    ct_biz = business_hours(in_progress_at, done_at) if in_progress_at and done_at else None

    # Tiempo por bucket
    blocked_biz = _sum_period_hours(blocked_periods)
    waiting_biz = _sum_period_hours(waiting_periods)
    qa_biz = _sum_period_hours(qa_active_periods)        # In QA / Testing → Edgar
    ready_for_qa_biz = _sum_period_hours(qa_handoff_periods)  # Ready for QA → dev
    review_biz = _sum_period_hours(review_periods)

    # Cycle ajustado (sin blocked/waiting)
    adj_ct_biz = None
    if ct_biz is not None:
        adj_ct_biz = max(0, ct_biz - (blocked_biz or 0) - (waiting_biz or 0))

    # Dev responsability: cycle - qa_activo(Edgar) - review
    # ready_for_qa NO se resta → es responsabilidad del dev
    dev_resp_biz = None
    if ct_biz is not None:
        dev_resp_biz = max(0, ct_biz - (qa_biz or 0) - (review_biz or 0))

    return {
        "done_at": done_at,
        "lt_biz_hours": lt_biz,
        "ct_biz_hours": ct_biz,
        "adj_ct_biz_hours": adj_ct_biz,
        "dev_resp_biz_hours": dev_resp_biz,
        "ready_for_qa_biz_hours": ready_for_qa_biz,
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
    except (ValueError, AttributeError):
        return None


def _find_last_transition_to(
    changelog: list[dict[str, Any]], statuses: frozenset[str]
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


def _find_transition_to(changelog: list[dict[str, Any]], to_status: str, default: datetime) -> datetime:
    """Encontrar primera transición a un estado."""
    for history in changelog:
        for item in history.get("items", []):
            if item.get("field") == "status" and item.get("toString") == to_status:
                return _parse_jira_datetime(history.get("created")) or default
    return default


def _find_blocked_periods(changelog: list[dict[str, Any]]) -> list[tuple[datetime, datetime]]:
    """Encontrar periodos en estado 'Blocked'."""
    return _find_status_periods(changelog, ["Blocked", "Bloqueado"])


def _find_waiting_periods(changelog: list[dict[str, Any]]) -> list[tuple[datetime, datetime]]:
    """Encontrar periodos en estado 'Waiting'."""
    return _find_status_periods(changelog, ["Waiting", "Esperando"])


def _find_status_periods(changelog: list[dict[str, Any]], statuses: list[str]) -> list[tuple[datetime, datetime]]:
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
    values = [business_hours(start, end) for start, end in periods if start and end]
    total: float = sum(values)
    return total if total > 0 else None


def _empty_metrics() -> dict[str, float | datetime | None]:
    """Retornar métricas vacías."""
    return {
        "done_at": None,
        "lt_biz_hours": None,
        "ct_biz_hours": None,
        "adj_ct_biz_hours": None,
        "dev_resp_biz_hours": None,
        "ready_for_qa_biz_hours": None,
        "qa_biz_hours": None,
        "blocked_biz_hours": None,
        "waiting_biz_hours": None,
        "review_biz_hours": None,
    }
