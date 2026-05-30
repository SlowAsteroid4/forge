"""Extracción de métricas de calidad desde changelog."""

from typing import Any


def extract_quality_metrics(issue: dict[str, Any]) -> dict[str, Any]:
    """
    Extraer métricas de calidad desde changelog.

    Args:
        issue: Payload completo de Jira

    Returns:
        Dict con qa_first_pass, qa_attempts, review_rejections
    """
    changelog = issue.get("changelog", {}).get("histories", [])

    # Contar transiciones QA → Dev (fallos QA)
    qa_attempts = _count_transitions(
        changelog, from_statuses=["Testing", "QA"], to_statuses=["In Progress", "To Do"]
    )

    # Contar review rejections
    review_rejections = _count_transitions(
        changelog, from_statuses=["In Review", "Code Review"], to_statuses=["In Progress"]
    )

    # QA first pass: True si qa_attempts == 0
    qa_first_pass = qa_attempts == 0 if qa_attempts is not None else None

    return {
        "qa_first_pass": qa_first_pass,
        "qa_attempts": qa_attempts or 0,
        "review_rejections": review_rejections or 0,
    }


def _count_transitions(changelog: list, from_statuses: list[str], to_statuses: list[str]) -> int:
    """Contar transiciones de un conjunto de estados a otro."""
    count = 0
    for history in changelog:
        for item in history.get("items", []):
            if item.get("field") == "status":
                if item.get("fromString") in from_statuses and item.get("toString") in to_statuses:
                    count += 1
    return count
