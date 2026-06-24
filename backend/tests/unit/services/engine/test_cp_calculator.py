"""Tests para cp_calculator.py — tabla de tallas, inmutabilidad, aprobación."""

from datetime import UTC, datetime

import pytest

from forge.core.exceptions import CPImmutableError
from forge.db.models.subtask import Subtask
from forge.services.engine.cp_calculator import (
    APPROVAL_REQUIRED,
    CP_TABLE,
    assign_cp,
    calculate_cp,
    is_rejected_size,
    needs_approval,
    validate_immutability,
)

# ── Fixtures ───────────────────────────────────────────────────────────────


def _make_subtask(
    *,
    jira_key: str = "YAP-1",
    complexity_size: str | None = None,
    cp: int | None = None,
    cp_approved_at: datetime | None = None,
) -> Subtask:
    """Subtask mínima (sin DB) para tests unitarios."""
    return Subtask(
        jira_key=jira_key,
        issue_type="Sub-task",
        area="BE",
        summary="Test subtask",
        status="In Progress",
        complexity_size=complexity_size,
        cp=cp,
        cp_approved_at=cp_approved_at,
        cp_approval_required=False,
        qa_attempts=0,
        review_rejections=0,
    )


# ── Tabla de tallas ────────────────────────────────────────────────────────


class TestCpTable:
    """Verifica la tabla CP_TABLE y calculate_cp()."""

    @pytest.mark.parametrize(
        "size, expected_cp",
        [
            ("XS", 1),
            ("S", 2),
            ("M", 3),
            ("L", 5),
            ("XL", 8),
            ("XXL", 13),
        ],
    )
    def test_calculate_cp_all_valid_sizes(self, size: str, expected_cp: int) -> None:
        assert calculate_cp(size) == expected_cp

    def test_calculate_cp_lowercase_normalized(self) -> None:
        """Tallas en minúsculas deben funcionar (se normalizan a uppercase)."""
        assert calculate_cp("xs") == 1
        assert calculate_cp("m") == 3
        assert calculate_cp("xxl") == 13

    def test_calculate_cp_with_whitespace(self) -> None:
        assert calculate_cp("  M  ") == 3

    def test_calculate_cp_none_returns_zero(self) -> None:
        assert calculate_cp(None) == 0

    def test_calculate_cp_invalid_size_raises(self) -> None:
        with pytest.raises(ValueError, match="no reconocida"):
            calculate_cp("ULTRA")

    def test_calculate_cp_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="no reconocida"):
            calculate_cp("")

    def test_cp_table_fibonacci_values(self) -> None:
        """Los valores CP deben seguir la escala Fibonacci (1,2,3,5,8,13)."""
        values = list(CP_TABLE.values())
        assert values == [1, 2, 3, 5, 8, 13]

    def test_cp_table_has_all_sizes(self) -> None:
        assert set(CP_TABLE.keys()) == {"XS", "S", "M", "L", "XL", "XXL"}


# ── needs_approval ─────────────────────────────────────────────────────────


class TestNeedsApproval:
    @pytest.mark.parametrize("size", ["L", "XL", "XXL"])
    def test_approval_required_for_large_sizes(self, size: str) -> None:
        assert needs_approval(size) is True

    @pytest.mark.parametrize("size", ["XS", "S", "M"])
    def test_approval_not_required_for_small_sizes(self, size: str) -> None:
        assert needs_approval(size) is False

    def test_approval_none_returns_false(self) -> None:
        assert needs_approval(None) is False

    def test_approval_case_insensitive(self) -> None:
        assert needs_approval("l") is True
        assert needs_approval("xl") is True
        assert needs_approval("m") is False

    def test_approval_required_set_matches_parametrize(self) -> None:
        assert APPROVAL_REQUIRED == frozenset({"L", "XL", "XXL"})


# ── is_rejected_size ───────────────────────────────────────────────────────


class TestIsRejectedSize:
    def test_xxl_is_rejected(self) -> None:
        assert is_rejected_size("XXL") is True

    def test_xxl_lowercase_is_rejected(self) -> None:
        assert is_rejected_size("xxl") is True

    @pytest.mark.parametrize("size", ["XS", "S", "M", "L", "XL"])
    def test_non_xxl_not_rejected(self, size: str) -> None:
        assert is_rejected_size(size) is False

    def test_none_is_not_rejected(self) -> None:
        assert is_rejected_size(None) is False


# ── validate_immutability ──────────────────────────────────────────────────


class TestValidateImmutability:
    def test_no_error_when_not_approved(self) -> None:
        st = _make_subtask(cp_approved_at=None)
        validate_immutability(st)  # No debe lanzar

    def test_raises_when_approved(self) -> None:
        approved_at = datetime(2026, 5, 1, tzinfo=UTC)
        st = _make_subtask(jira_key="YAP-99", cp_approved_at=approved_at)
        with pytest.raises(CPImmutableError) as exc_info:
            validate_immutability(st)
        assert "YAP-99" in str(exc_info.value)

    def test_error_message_contains_key(self) -> None:
        st = _make_subtask(jira_key="YAP-42", cp_approved_at=datetime.utcnow())
        with pytest.raises(CPImmutableError, match="YAP-42"):
            validate_immutability(st)


# ── assign_cp ─────────────────────────────────────────────────────────────


class TestAssignCp:
    def test_assign_sets_cp_and_size(self) -> None:
        st = _make_subtask()
        assign_cp(st, "M")
        assert st.complexity_size == "M"
        assert st.cp == 3

    def test_assign_sets_approval_required_for_l(self) -> None:
        st = _make_subtask()
        assign_cp(st, "L")
        assert st.cp_approval_required is True

    def test_assign_does_not_require_approval_for_m(self) -> None:
        st = _make_subtask()
        assign_cp(st, "M")
        assert st.cp_approval_required is False

    def test_assign_normalizes_to_uppercase(self) -> None:
        st = _make_subtask()
        assign_cp(st, "xs")
        assert st.complexity_size == "XS"
        assert st.cp == 1

    def test_assign_raises_if_already_approved(self) -> None:
        st = _make_subtask(
            jira_key="YAP-100",
            cp_approved_at=datetime.utcnow(),
            complexity_size="S",
            cp=2,
        )
        with pytest.raises(CPImmutableError):
            assign_cp(st, "M")  # Intento de cambiar CP aprobado

    def test_assign_raises_on_invalid_size(self) -> None:
        st = _make_subtask()
        with pytest.raises(ValueError):
            assign_cp(st, "GIGANTE")

    def test_assign_xxl_marks_approval_required(self) -> None:
        """XXL es rechazada pero igualmente requiere aprobación (como L y XL)."""
        st = _make_subtask()
        assign_cp(st, "XXL")
        assert st.cp == 13
        assert st.cp_approval_required is True
