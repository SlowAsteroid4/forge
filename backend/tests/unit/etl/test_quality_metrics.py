"""Tests unitarios para quality_metrics — qa_first_pass con estados reales de Jira."""

import pytest

from forge.etl.quality_metrics import _compute_qa_first_pass, extract_quality_metrics


def _make_history(created: str, frm: str, to: str) -> dict:
    return {
        "created": created,
        "items": [{"field": "status", "fromString": frm, "toString": to}],
    }


# ─── _compute_qa_first_pass ───────────────────────────────────────────────────


def test_qa_first_pass_true_entered_qa_then_done() -> None:
    """Entró a QA y fue directo a Done → first-pass = True."""
    changelog = [
        _make_history("2026-05-01T10:00:00Z", "In Progress", "Ready for QA"),
        _make_history("2026-05-02T10:00:00Z", "Ready for QA", "In QA"),
        _make_history("2026-05-03T10:00:00Z", "In QA", "Done"),
    ]
    qa_first_pass, qa_attempts = _compute_qa_first_pass(changelog)
    assert qa_first_pass is True
    assert qa_attempts == 2  # entró a Ready for QA y a In QA


def test_qa_first_pass_false_bounced_back_to_dev() -> None:
    """Entró a QA, regresó a In Progress, luego Done → first-pass = False."""
    changelog = [
        _make_history("2026-05-01T10:00:00Z", "In Progress", "In QA"),
        _make_history("2026-05-02T10:00:00Z", "In QA", "In Progress"),  # rebote
        _make_history("2026-05-03T10:00:00Z", "In Progress", "In QA"),
        _make_history("2026-05-04T10:00:00Z", "In QA", "Done"),
    ]
    qa_first_pass, qa_attempts = _compute_qa_first_pass(changelog)
    assert qa_first_pass is False
    assert qa_attempts == 2  # dos entradas a In QA


def test_qa_first_pass_none_never_entered_qa() -> None:
    """Nunca entró a un estado QA → None (no aplica, no cuenta en denominador)."""
    changelog = [
        _make_history("2026-05-01T10:00:00Z", "Backlog", "In Progress"),
        _make_history("2026-05-02T10:00:00Z", "In Progress", "Done"),
    ]
    qa_first_pass, qa_attempts = _compute_qa_first_pass(changelog)
    assert qa_first_pass is None
    assert qa_attempts == 0


def test_qa_first_pass_testing_state_counts() -> None:
    """El estado 'Testing' también cuenta como QA."""
    changelog = [
        _make_history("2026-05-01T10:00:00Z", "In Progress", "Testing"),
        _make_history("2026-05-02T10:00:00Z", "Testing", "Done"),
    ]
    qa_first_pass, qa_attempts = _compute_qa_first_pass(changelog)
    assert qa_first_pass is True
    assert qa_attempts == 1


def test_qa_first_pass_bounce_via_implementation() -> None:
    """Rebote desde 'In QA' a 'Implementation' también cuenta."""
    changelog = [
        _make_history("2026-05-01T10:00:00Z", "Implementation", "In QA"),
        _make_history("2026-05-02T10:00:00Z", "In QA", "Implementation"),  # rebote
        _make_history("2026-05-03T10:00:00Z", "Implementation", "In QA"),
        _make_history("2026-05-04T10:00:00Z", "In QA", "Done"),
    ]
    qa_first_pass, qa_attempts = _compute_qa_first_pass(changelog)
    assert qa_first_pass is False


# ─── extract_quality_metrics (integración mínima) ────────────────────────────


def test_extract_quality_metrics_no_qa() -> None:
    issue: dict = {
        "changelog": {
            "histories": [
                _make_history("2026-05-01T10:00:00Z", "Backlog", "In Progress"),
                _make_history("2026-05-02T10:00:00Z", "In Progress", "Done"),
            ]
        }
    }
    result = extract_quality_metrics(issue)
    assert result["qa_first_pass"] is None
    assert result["qa_attempts"] == 0


def test_extract_quality_metrics_first_pass() -> None:
    issue: dict = {
        "changelog": {
            "histories": [
                _make_history("2026-05-01T10:00:00Z", "In Progress", "In QA"),
                _make_history("2026-05-02T10:00:00Z", "In QA", "Done"),
            ]
        }
    }
    result = extract_quality_metrics(issue)
    assert result["qa_first_pass"] is True
    assert result["qa_attempts"] == 1


def test_extract_quality_metrics_bounced() -> None:
    issue: dict = {
        "changelog": {
            "histories": [
                _make_history("2026-05-01T10:00:00Z", "In Progress", "In QA"),
                _make_history("2026-05-02T10:00:00Z", "In QA", "In Progress"),
                _make_history("2026-05-03T10:00:00Z", "In Progress", "In QA"),
                _make_history("2026-05-04T10:00:00Z", "In QA", "Done"),
            ]
        }
    }
    result = extract_quality_metrics(issue)
    assert result["qa_first_pass"] is False
    assert result["qa_attempts"] == 2
