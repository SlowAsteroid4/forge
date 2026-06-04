"""Extracción de métricas de calidad desde changelog."""

from typing import Any

# Estados que representan entrada a QA
_QA_STATES: frozenset[str] = frozenset({"In QA", "Ready for QA", "Testing"})

# Estados que representan vuelta a desarrollo (rebote desde QA)
_DEV_STATES: frozenset[str] = frozenset(
    {
        "In Progress",
        "Active",
        "Implementation",
        "UI Implementation",
        "In Design",
        "Prototyping",
    }
)


def extract_quality_metrics(issue: dict[str, Any]) -> dict[str, Any]:
    """
    Extraer métricas de calidad desde changelog.

    Args:
        issue: Payload completo de Jira (con changelog.histories)

    Returns:
        Dict con qa_first_pass, qa_attempts, review_rejections
    """
    changelog = issue.get("changelog", {}).get("histories", [])

    qa_first_pass, qa_attempts = _compute_qa_first_pass(changelog)
    review_rejections = _count_transitions(
        changelog,
        from_statuses={"In Review", "Code Review"},
        to_statuses={"In Progress", "Active"},
    )

    return {
        "qa_first_pass": qa_first_pass,
        "qa_attempts": qa_attempts,
        "review_rejections": review_rejections or 0,
    }


def _compute_qa_first_pass(changelog: list[dict[str, Any]]) -> tuple[bool | None, int]:
    """
    Determinar si una subtask pasó QA en el primer intento.

    Reglas:
    - Si nunca entró a un estado QA → (None, 0)  — no aplica, excluir del denominador
    - Si entró a QA y regresó a desarrollo antes de Done → (False, n)  — rebotó n veces
    - Si entró a QA y fue directo a Done sin regresar → (True, 1)

    Args:
        changelog: Lista de historias de changelog (dicts con 'created' e 'items')

    Returns:
        Tuple (qa_first_pass, qa_attempts) donde qa_attempts = número de entradas a QA
    """
    histories_sorted = sorted(changelog, key=lambda h: h.get("created", ""))

    transitions: list[tuple[str, str]] = []
    for history in histories_sorted:
        for item in history.get("items", []):
            if item.get("field") == "status":
                frm = item.get("fromString") or ""
                to = item.get("toString") or ""
                transitions.append((frm, to))

    entered_qa = False
    bounced = False
    qa_entry_count = 0

    for frm, to in transitions:
        if to in _QA_STATES:
            entered_qa = True
            qa_entry_count += 1
        elif entered_qa and frm in _QA_STATES and to in _DEV_STATES:
            # Regresó a desarrollo desde QA — primer rebote confirma no-first-pass
            bounced = True

    if not entered_qa:
        return (None, 0)
    if bounced:
        return (False, qa_entry_count)
    return (True, qa_entry_count)


def _count_transitions(
    changelog: list[dict[str, Any]],
    from_statuses: set[str],
    to_statuses: set[str],
) -> int:
    """Contar transiciones de un conjunto de estados a otro."""
    count = 0
    for history in changelog:
        for item in history.get("items", []):
            if item.get("field") == "status":
                if item.get("fromString") in from_statuses and item.get("toString") in to_statuses:
                    count += 1
    return count


def compute_qa_first_pass_from_raw(raw_changelog: dict[str, Any]) -> tuple[bool | None, int]:
    """
    Recomputar qa_first_pass desde raw_changelog ya guardado en DB.

    Args:
        raw_changelog: Dict con clave 'histories' (formato Jira changelog paginado)

    Returns:
        Tuple (qa_first_pass, qa_attempts)
    """
    histories = raw_changelog.get("histories", [])
    return _compute_qa_first_pass(histories)
