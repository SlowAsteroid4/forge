"""Tests para debuff_detector.py — D01, D03, D04, D10, D11, D13."""

import pytest
from datetime import datetime, date

from forge.db.models.sprint import Sprint
from forge.db.models.subtask import Subtask
from forge.services.engine.debuff_detector import (
    DetectedDebuff,
    detect_all,
    detect_d01,
    detect_d03,
    detect_d04,
    detect_d10,
    detect_d11,
    detect_d13,
    _D01_PENALTY,
    _D03_PENALTY_PER_EXTRA,
    _D04_PENALTY_PER_EXTRA,
    _D10_PENALTY,
    _D11_PENALTY,
    _D13_PENALTY,
    _D10_BLOCKED_THRESHOLD_HOURS,
    _D11_INACTIVE_BIZ_HOURS,
)


# ── Factories ──────────────────────────────────────────────────────────────


def _subtask(
    *,
    jira_key: str = "YAP-1",
    status: str = "Done",
    qa_first_pass: bool | None = True,
    qa_attempts: int = 1,
    review_rejections: int = 0,
    blocked_biz_hours: float | None = 0.0,
    waiting_biz_hours: float | None = None,
    lt_biz_hours: float | None = None,
    done_at: datetime | None = datetime(2026, 5, 20),
) -> Subtask:
    return Subtask(
        jira_key=jira_key,
        issue_type="Sub-task",
        area="BE",
        summary="Test",
        status=status,
        qa_first_pass=qa_first_pass,
        qa_attempts=qa_attempts,
        review_rejections=review_rejections,
        blocked_biz_hours=blocked_biz_hours,
        waiting_biz_hours=waiting_biz_hours,
        lt_biz_hours=lt_biz_hours,
        done_at=done_at,
    )


def _sprint(*, is_closed: bool = True, name: str = "Sprint 2026-W20") -> Sprint:
    return Sprint(
        name=name,
        start_date=date(2026, 5, 11),
        end_date=date(2026, 5, 17),
        is_closed=is_closed,
    )


# ── D01 ────────────────────────────────────────────────────────────────────


class TestDetectD01:
    def test_returns_none_when_first_pass_true(self) -> None:
        st = _subtask(qa_first_pass=True, qa_attempts=1)
        assert detect_d01(st) is None

    def test_returns_none_when_multiple_attempts(self) -> None:
        """Con ≥2 intentos D03 aplica, no D01."""
        st = _subtask(qa_first_pass=False, qa_attempts=2)
        assert detect_d01(st) is None

    def test_triggers_on_single_failed_attempt(self) -> None:
        st = _subtask(qa_first_pass=False, qa_attempts=1)
        result = detect_d01(st)
        assert result is not None
        assert result.catalog_code == "D01"
        assert result.amount_sp == pytest.approx(_D01_PENALTY)

    def test_returns_none_when_first_pass_none_zero_attempts(self) -> None:
        st = _subtask(qa_first_pass=None, qa_attempts=0)
        assert detect_d01(st) is None

    def test_debuff_is_frozen_dataclass(self) -> None:
        st = _subtask(qa_first_pass=False, qa_attempts=1)
        d = detect_d01(st)
        assert isinstance(d, DetectedDebuff)
        with pytest.raises((AttributeError, TypeError)):
            d.amount_sp = 99.0  # type: ignore[misc]


# ── D03 ────────────────────────────────────────────────────────────────────


class TestDetectD03:
    def test_no_debuff_on_two_attempts(self) -> None:
        st = _subtask(qa_attempts=2)
        assert detect_d03(st) is None

    def test_triggers_on_three_attempts(self) -> None:
        st = _subtask(qa_attempts=3)
        result = detect_d03(st)
        assert result is not None
        assert result.catalog_code == "D03"
        # 1 intento extra (3-2=1) × penalty
        assert result.amount_sp == pytest.approx(1 * _D03_PENALTY_PER_EXTRA)

    def test_stacks_per_extra_attempt(self) -> None:
        """5 intentos → 3 extras → 3 × penalty."""
        st = _subtask(qa_attempts=5)
        result = detect_d03(st)
        assert result is not None
        assert result.amount_sp == pytest.approx(3 * _D03_PENALTY_PER_EXTRA)

    def test_reason_mentions_attempt_count(self) -> None:
        st = _subtask(qa_attempts=4)
        result = detect_d03(st)
        assert result is not None
        assert "4" in result.reason

    def test_zero_attempts_no_debuff(self) -> None:
        st = _subtask(qa_attempts=0)
        assert detect_d03(st) is None


# ── D04 ────────────────────────────────────────────────────────────────────


class TestDetectD04:
    def test_no_debuff_on_one_rejection(self) -> None:
        st = _subtask(review_rejections=1)
        assert detect_d04(st) is None

    def test_triggers_on_two_rejections(self) -> None:
        st = _subtask(review_rejections=2)
        result = detect_d04(st)
        assert result is not None
        assert result.catalog_code == "D04"
        # 1 rechazo extra (2-1=1) × penalty
        assert result.amount_sp == pytest.approx(1 * _D04_PENALTY_PER_EXTRA)

    def test_stacks_per_extra_rejection(self) -> None:
        """4 rechazos → 3 extras → 3 × penalty."""
        st = _subtask(review_rejections=4)
        result = detect_d04(st)
        assert result is not None
        assert result.amount_sp == pytest.approx(3 * _D04_PENALTY_PER_EXTRA)

    def test_no_debuff_zero_rejections(self) -> None:
        st = _subtask(review_rejections=0)
        assert detect_d04(st) is None


# ── D10 ────────────────────────────────────────────────────────────────────


class TestDetectD10:
    def test_no_debuff_below_threshold(self) -> None:
        st = _subtask(blocked_biz_hours=_D10_BLOCKED_THRESHOLD_HOURS - 0.1)
        assert detect_d10(st) is None

    def test_triggers_above_threshold(self) -> None:
        st = _subtask(blocked_biz_hours=_D10_BLOCKED_THRESHOLD_HOURS + 1.0)
        result = detect_d10(st)
        assert result is not None
        assert result.catalog_code == "D10"
        assert result.amount_sp == pytest.approx(_D10_PENALTY)

    def test_exactly_at_threshold_no_debuff(self) -> None:
        """El umbral es estricto (>), exactamente en el límite no activa."""
        st = _subtask(blocked_biz_hours=_D10_BLOCKED_THRESHOLD_HOURS)
        assert detect_d10(st) is None

    def test_none_blocked_hours_no_debuff(self) -> None:
        st = _subtask(blocked_biz_hours=None)
        assert detect_d10(st) is None

    def test_reason_mentions_hours(self) -> None:
        st = _subtask(blocked_biz_hours=12.0)
        result = detect_d10(st)
        assert result is not None
        assert "12.0" in result.reason


# ── D11 ────────────────────────────────────────────────────────────────────


class TestDetectD11:
    def test_no_debuff_when_done(self) -> None:
        """Tarea terminada: D11 no aplica sin importar el tiempo."""
        st = _subtask(
            status="Done",
            done_at=datetime(2026, 5, 20),
            lt_biz_hours=100.0,
        )
        assert detect_d11(st) is None

    def test_no_debuff_when_cancelled(self) -> None:
        st = _subtask(
            status="Cancelled",
            done_at=None,
            lt_biz_hours=100.0,
        )
        assert detect_d11(st) is None

    def test_triggers_when_in_progress_too_long(self) -> None:
        st = _subtask(
            status="In Progress",
            done_at=None,
            lt_biz_hours=_D11_INACTIVE_BIZ_HOURS + 1.0,
        )
        result = detect_d11(st)
        assert result is not None
        assert result.catalog_code == "D11"
        assert result.amount_sp == pytest.approx(_D11_PENALTY)

    def test_no_debuff_when_in_progress_short_time(self) -> None:
        st = _subtask(
            status="In Progress",
            done_at=None,
            lt_biz_hours=_D11_INACTIVE_BIZ_HOURS - 1.0,
        )
        assert detect_d11(st) is None

    def test_no_debuff_when_none_lt(self) -> None:
        st = _subtask(status="In Progress", done_at=None, lt_biz_hours=None)
        assert detect_d11(st) is None

    def test_reason_mentions_hours(self) -> None:
        st = _subtask(status="In Progress", done_at=None, lt_biz_hours=50.0)
        result = detect_d11(st)
        assert result is not None
        assert "50.0" in result.reason


# ── D13 ────────────────────────────────────────────────────────────────────


class TestDetectD13:
    def test_no_debuff_when_sprint_is_none(self) -> None:
        st = _subtask(status="In Progress", done_at=None)
        assert detect_d13(st, sprint=None) is None

    def test_no_debuff_when_sprint_is_open(self) -> None:
        st = _subtask(status="In Progress", done_at=None)
        sprint = _sprint(is_closed=False)
        assert detect_d13(st, sprint=sprint) is None

    def test_triggers_when_sprint_closed_and_task_not_done(self) -> None:
        st = _subtask(status="In Progress", done_at=None)
        sprint = _sprint(is_closed=True)
        result = detect_d13(st, sprint=sprint)
        assert result is not None
        assert result.catalog_code == "D13"
        assert result.amount_sp == pytest.approx(_D13_PENALTY)

    def test_no_debuff_when_sprint_closed_but_task_done(self) -> None:
        st = _subtask(status="Done", done_at=datetime(2026, 5, 17))
        sprint = _sprint(is_closed=True)
        assert detect_d13(st, sprint=sprint) is None

    def test_no_debuff_when_sprint_closed_but_task_cancelled(self) -> None:
        st = _subtask(status="Cancelled", done_at=None)
        sprint = _sprint(is_closed=True)
        assert detect_d13(st, sprint=sprint) is None

    def test_reason_mentions_sprint_name(self) -> None:
        st = _subtask(status="Blocked", done_at=None)
        sprint = _sprint(is_closed=True, name="Sprint 2026-W15")
        result = detect_d13(st, sprint=sprint)
        assert result is not None
        assert "Sprint 2026-W15" in result.reason


# ── detect_all ────────────────────────────────────────────────────────────


class TestDetectAll:
    def test_clean_subtask_returns_empty_list(self) -> None:
        st = _subtask(
            status="Done",
            qa_first_pass=True,
            qa_attempts=1,
            review_rejections=0,
            blocked_biz_hours=0.0,
            lt_biz_hours=8.0,
            done_at=datetime(2026, 5, 20),
        )
        sprint = _sprint(is_closed=True)
        result = detect_all(st, sprint=sprint)
        assert result == []

    def test_multiple_debuffs_detected(self) -> None:
        """Una subtask puede disparar varios debuffs a la vez."""
        st = _subtask(
            status="In Progress",
            qa_first_pass=False,
            qa_attempts=4,          # D03
            review_rejections=3,    # D04
            blocked_biz_hours=20.0, # D10
            lt_biz_hours=60.0,      # D11
            done_at=None,
        )
        sprint = _sprint(is_closed=True)  # D13
        result = detect_all(st, sprint=sprint)
        codes = {d.catalog_code for d in result}
        # D01 NO aplica porque qa_attempts > 1
        assert "D03" in codes
        assert "D04" in codes
        assert "D10" in codes
        assert "D11" in codes
        assert "D13" in codes
        assert "D01" not in codes

    def test_detect_all_without_sprint_skips_d13(self) -> None:
        st = _subtask(
            status="In Progress",
            done_at=None,
            lt_biz_hours=60.0,     # D11
            blocked_biz_hours=20.0, # D10
        )
        result = detect_all(st, sprint=None)
        codes = {d.catalog_code for d in result}
        assert "D13" not in codes
        assert "D10" in codes
        assert "D11" in codes

    def test_detect_all_returns_list_of_detected_debuffs(self) -> None:
        st = _subtask(qa_attempts=3)
        result = detect_all(st)
        assert all(isinstance(d, DetectedDebuff) for d in result)

    def test_detect_all_never_raises(self) -> None:
        """detect_all debe ser robusto y nunca propagar excepciones."""
        # Subtask con datos absurdos
        st = _subtask(
            status="Unknown_Status",
            qa_first_pass=None,
            qa_attempts=-1,
            review_rejections=-5,
            blocked_biz_hours=-10.0,
            lt_biz_hours=-50.0,
        )
        # No debe lanzar
        result = detect_all(st)
        assert isinstance(result, list)

    def test_amount_sp_always_positive(self) -> None:
        st = _subtask(qa_attempts=10, review_rejections=5, blocked_biz_hours=50.0)
        for d in detect_all(st):
            assert d.amount_sp > 0, f"{d.catalog_code} tiene amount_sp <= 0"
