"""Tests para sp_calculator.py — fórmula completa SP."""

from datetime import datetime

import pytest

from forge.db.models.subtask import Subtask
from forge.services.engine.sp_calculator import SpComponents, calculate_sp, needs_recalculation

# ── Factories ──────────────────────────────────────────────────────────────


def _subtask(
    *,
    cp: int | None = None,
    complexity_size: str | None = None,
    qa_first_pass: bool | None = None,
    qa_attempts: int = 0,
    review_rejections: int = 0,
    adj_ct_biz_hours: float | None = None,
    difficulty_modifier_raw: str | None = None,
    blocked_biz_hours: float | None = None,
    raw_changelog: str | None = None,
    sp_last_calculated_at: datetime | None = None,
    engine_version_id: int | None = None,
) -> Subtask:
    return Subtask(
        jira_key="YAP-TEST",
        issue_type="Sub-task",
        area="BE",
        summary="Test",
        status="Done",
        done_at=datetime(2026, 5, 20),
        cp=cp,
        complexity_size=complexity_size,
        qa_first_pass=qa_first_pass,
        qa_attempts=qa_attempts,
        review_rejections=review_rejections,
        adj_ct_biz_hours=adj_ct_biz_hours,
        difficulty_modifier_raw=difficulty_modifier_raw,
        blocked_biz_hours=blocked_biz_hours,
        raw_changelog=raw_changelog,
        sp_last_calculated_at=sp_last_calculated_at,
        engine_version_id=engine_version_id,
    )


# ── calculate_sp — fórmula básica ─────────────────────────────────────────


class TestCalculateSp:
    def test_zero_cp_returns_zero_sp(self) -> None:
        st = _subtask(cp=None)
        result = calculate_sp(st)
        assert result.sp_base == 0.0
        assert result.sp_final == 0.0

    def test_cp_zero_explicit_returns_zero(self) -> None:
        st = _subtask(cp=0)
        result = calculate_sp(st)
        assert result.sp_final == 0.0

    def test_basic_formula_all_ones(self) -> None:
        """CP=3 × todos los multiplicadores=1.0 → SP=3.0."""
        st = _subtask(cp=3, qa_attempts=0)
        result = calculate_sp(st)
        assert result.sp_base == pytest.approx(3.0)
        assert result.sp_final == pytest.approx(3.0)

    def test_first_pass_bonus_applied(self) -> None:
        """CP=5 × M_calidad=1.20 × resto=1.0 → SP=6.0."""
        st = _subtask(cp=5, qa_first_pass=True, qa_attempts=1)
        result = calculate_sp(st)
        assert result.m_calidad == pytest.approx(1.20)
        assert result.sp_base == pytest.approx(6.0)

    def test_quality_penalty_applied(self) -> None:
        """CP=8 × M_calidad=0.85 → SP base=6.80."""
        st = _subtask(cp=8, qa_first_pass=False, qa_attempts=3)
        result = calculate_sp(st)
        assert result.m_calidad == pytest.approx(0.85)
        assert result.sp_base == pytest.approx(8 * 0.85)

    def test_difficulty_modifier_applied(self) -> None:
        """CP=3 × M_dificultad=1.10 → SP base=3.30."""
        st = _subtask(cp=3, difficulty_modifier_raw="B08")
        result = calculate_sp(st)
        assert result.m_dificultad == pytest.approx(1.10)
        assert result.sp_base == pytest.approx(3.30)

    def test_bonus_added_to_sp_final(self) -> None:
        """CP=3 base, +2 bonus → SP final=5."""
        st = _subtask(cp=3)
        result = calculate_sp(st, sp_flat_bonus=2.0)
        assert result.sp_flat_bonus == 2.0
        assert result.sp_final == pytest.approx(5.0)

    def test_penalty_subtracted_from_sp_final(self) -> None:
        """CP=5 base, -1.5 penalty → SP final=3.5."""
        st = _subtask(cp=5)
        result = calculate_sp(st, sp_penalty=1.5)
        assert result.sp_penalty == 1.5
        assert result.sp_final == pytest.approx(3.5)

    def test_sp_final_never_negative(self) -> None:
        """Penalización mayor que SP base → sp_final = 0.0."""
        st = _subtask(cp=1)  # sp_base = 1.0
        result = calculate_sp(st, sp_penalty=10.0)
        assert result.sp_final == 0.0

    def test_bonus_and_penalty_combined(self) -> None:
        """CP=5, +3 bonus, -1 penalty → 5 + 3 - 1 = 7."""
        st = _subtask(cp=5)
        result = calculate_sp(st, sp_flat_bonus=3.0, sp_penalty=1.0)
        assert result.sp_final == pytest.approx(7.0)

    def test_full_formula_all_multipliers(self) -> None:
        """
        CP=8, M_calidad=1.20, M_eficiencia=1.10, M_dificultad=1.10,
        M_lider=1.0, M_cooperacion=1.0 → base=8×1.20×1.10×1.10×1×1=11.616
        """
        # XS esperado = 4h, tardó 2.8h → ratio=0.70 → 1.10
        st = _subtask(
            cp=8,
            qa_first_pass=True,
            qa_attempts=1,
            complexity_size="XS",
            adj_ct_biz_hours=2.8,   # ratio ≈ 0.70 → M_eficiencia=1.10
            difficulty_modifier_raw="B08",  # M_dificultad=1.10
        )
        result = calculate_sp(st)
        expected_base = round(8 * 1.20 * 1.10 * 1.10 * 1.0 * 1.0, 2)
        assert result.sp_base == pytest.approx(expected_base, abs=0.01)

    def test_returns_sp_components_dataclass(self) -> None:
        st = _subtask(cp=3)
        result = calculate_sp(st)
        assert isinstance(result, SpComponents)

    def test_components_as_dict_has_all_keys(self) -> None:
        st = _subtask(cp=5)
        d = calculate_sp(st).as_dict()
        expected_keys = {
            "m_calidad", "m_eficiencia", "m_dificultad",
            "m_lider", "m_cooperacion",
            "sp_base", "sp_flat_bonus", "sp_penalty", "sp_final",
        }
        assert set(d.keys()) == expected_keys

    def test_idempotent_with_same_inputs(self) -> None:
        """Calcular dos veces produce el mismo resultado."""
        st = _subtask(
            cp=5,
            qa_first_pass=True,
            qa_attempts=1,
            difficulty_modifier_raw="B09",
        )
        r1 = calculate_sp(st, sp_flat_bonus=1.0, sp_penalty=0.5)
        r2 = calculate_sp(st, sp_flat_bonus=1.0, sp_penalty=0.5)
        assert r1 == r2

    def test_sp_rounded_to_two_decimals(self) -> None:
        """sp_base y sp_final tienen máximo 2 decimales."""
        # CP=3 × 1.05 (B07) = 3.15 → exacto a 2 decimales
        st = _subtask(cp=3, difficulty_modifier_raw="B07")
        result = calculate_sp(st)
        # Verificar que no hay más de 2 decimales (float puede ser impreciso)
        assert result.sp_base == round(result.sp_base, 2)
        assert result.sp_final == round(result.sp_final, 2)


# ── needs_recalculation ───────────────────────────────────────────────────


class TestNeedsRecalculation:
    def test_never_calculated_needs_recalc(self) -> None:
        st = _subtask(sp_last_calculated_at=None, engine_version_id=None)
        assert needs_recalculation(st, current_version_id=1) is True

    def test_different_version_needs_recalc(self) -> None:
        st = _subtask(
            sp_last_calculated_at=datetime(2026, 5, 1),
            engine_version_id=1,
        )
        assert needs_recalculation(st, current_version_id=2) is True

    def test_same_version_no_recalc_needed(self) -> None:
        st = _subtask(
            sp_last_calculated_at=datetime(2026, 5, 1),
            engine_version_id=3,
        )
        assert needs_recalculation(st, current_version_id=3) is False

    def test_calculated_with_none_version_id_needs_recalc(self) -> None:
        st = _subtask(
            sp_last_calculated_at=datetime(2026, 5, 1),
            engine_version_id=None,
        )
        assert needs_recalculation(st, current_version_id=1) is True
