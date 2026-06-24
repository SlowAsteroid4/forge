"""Tests para multiplier_calculator.py — cada multiplicador de SP."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from forge.db.models.subtask import Subtask
from forge.services.engine.multiplier_calculator import (
    _EXPECTED_HOURS_BY_SIZE,
    _M_CALIDAD_DEFAULT,
    _M_CALIDAD_FIRST_PASS,
    _M_CALIDAD_MULTIPLE,
    _M_COOPERACION_BONUS,
    calc_all_multipliers,
    calc_m_calidad,
    calc_m_cooperacion,
    calc_m_dificultad,
    calc_m_eficiencia,
    calc_m_lider,
)

# ── Fixture base ───────────────────────────────────────────────────────────


def _subtask(
    *,
    qa_first_pass: bool | None = None,
    qa_attempts: int = 0,
    complexity_size: str | None = None,
    adj_ct_biz_hours: float | None = None,
    difficulty_modifier_raw: str | None = None,
    raw_changelog: str | None = None,
) -> Subtask:
    return Subtask(
        jira_key="YAP-TEST",
        issue_type="Sub-task",
        area="BE",
        summary="Test",
        status="In Progress",
        qa_first_pass=qa_first_pass,
        qa_attempts=qa_attempts,
        complexity_size=complexity_size,
        adj_ct_biz_hours=adj_ct_biz_hours,
        difficulty_modifier_raw=difficulty_modifier_raw,
        raw_changelog=raw_changelog,
    )


def _changelog_with_blocking(
    block_start: datetime,
    block_end: datetime,
) -> str:
    """Genera un raw_changelog con un periodo de bloqueo."""
    histories = [
        {
            "created": block_start.isoformat(),
            "items": [
                {
                    "field": "status",
                    "fromString": "In Progress",
                    "toString": "Blocked",
                }
            ],
        },
        {
            "created": block_end.isoformat(),
            "items": [
                {
                    "field": "status",
                    "fromString": "Blocked",
                    "toString": "In Progress",
                }
            ],
        },
    ]
    return json.dumps({"histories": histories})


# ── M_calidad ─────────────────────────────────────────────────────────────


class TestMCalidad:
    def test_first_pass_gives_bonus(self) -> None:
        st = _subtask(qa_first_pass=True, qa_attempts=1)
        assert calc_m_calidad(st) == _M_CALIDAD_FIRST_PASS  # 1.20

    def test_two_attempts_gives_default(self) -> None:
        st = _subtask(qa_first_pass=False, qa_attempts=2)
        assert calc_m_calidad(st) == _M_CALIDAD_DEFAULT  # 1.00

    def test_three_attempts_gives_penalty(self) -> None:
        st = _subtask(qa_first_pass=False, qa_attempts=3)
        assert calc_m_calidad(st) == _M_CALIDAD_MULTIPLE  # 0.85

    def test_five_attempts_still_gives_multiple_penalty(self) -> None:
        st = _subtask(qa_first_pass=False, qa_attempts=5)
        assert calc_m_calidad(st) == _M_CALIDAD_MULTIPLE  # 0.85

    def test_none_first_pass_with_zero_attempts_gives_default(self) -> None:
        st = _subtask(qa_first_pass=None, qa_attempts=0)
        assert calc_m_calidad(st) == _M_CALIDAD_DEFAULT

    def test_first_pass_true_overrides_low_attempts(self) -> None:
        """qa_first_pass=True debe ganar incluso si qa_attempts=1."""
        st = _subtask(qa_first_pass=True, qa_attempts=1)
        assert calc_m_calidad(st) == pytest.approx(1.20)

    def test_returns_float(self) -> None:
        assert isinstance(calc_m_calidad(_subtask()), float)


# ── M_eficiencia ──────────────────────────────────────────────────────────


class TestMEficiencia:
    def test_no_size_returns_neutral(self) -> None:
        st = _subtask(complexity_size=None, adj_ct_biz_hours=10.0)
        assert calc_m_eficiencia(st) == 1.0

    def test_no_ct_returns_neutral(self) -> None:
        st = _subtask(complexity_size="M", adj_ct_biz_hours=None)
        assert calc_m_eficiencia(st) == 1.0

    def test_on_target_gives_neutral(self) -> None:
        """M esperado = 16h; ratio 1.0 → bracket [0.85, 1.20) → 1.0."""
        expected = _EXPECTED_HOURS_BY_SIZE["M"]  # 16
        st = _subtask(complexity_size="M", adj_ct_biz_hours=expected)
        assert calc_m_eficiencia(st) == 1.0

    def test_very_fast_gives_bonus(self) -> None:
        """XS esperado = 4h; terminó en 1h → ratio 0.25 → 1.20."""
        expected = _EXPECTED_HOURS_BY_SIZE["XS"]  # 4
        st = _subtask(complexity_size="XS", adj_ct_biz_hours=expected * 0.25)
        assert calc_m_eficiencia(st) == pytest.approx(1.20)

    def test_slightly_fast_gives_small_bonus(self) -> None:
        """S esperado = 8h; terminó en 5.6h → ratio 0.70 → 1.10."""
        expected = _EXPECTED_HOURS_BY_SIZE["S"]  # 8
        st = _subtask(complexity_size="S", adj_ct_biz_hours=expected * 0.70)
        assert calc_m_eficiencia(st) == pytest.approx(1.10)

    def test_slow_gives_penalty(self) -> None:
        """L esperado = 32h; tardó 48h → ratio 1.5 → 0.90."""
        expected = _EXPECTED_HOURS_BY_SIZE["L"]  # 32
        st = _subtask(complexity_size="L", adj_ct_biz_hours=expected * 1.5)
        assert calc_m_eficiencia(st) == pytest.approx(0.90)

    def test_very_slow_gives_max_penalty(self) -> None:
        """XL esperado = 56h; tardó 200h → ratio > 2.0 → 0.75."""
        expected = _EXPECTED_HOURS_BY_SIZE["XL"]  # 56
        st = _subtask(complexity_size="XL", adj_ct_biz_hours=expected * 4)
        assert calc_m_eficiencia(st) == pytest.approx(0.75)

    def test_boundary_exactly_at_085_is_in_first_pass_bracket(self) -> None:
        """ratio=0.85 pertenece al bracket [0.85, 1.20) → 1.0."""
        expected = _EXPECTED_HOURS_BY_SIZE["S"]
        st = _subtask(complexity_size="S", adj_ct_biz_hours=expected * 0.85)
        assert calc_m_eficiencia(st) == 1.0


# ── M_dificultad ──────────────────────────────────────────────────────────


class TestMDificultad:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("B06", 1.00),
            ("B07", 1.05),
            ("B08", 1.10),
            ("B09", 1.20),
            ("B10", 1.30),
            # Alias en español
            ("Normal", 1.00),
            ("Leve", 1.05),
            ("Media", 1.10),
            ("Alta", 1.20),
            ("Muy alta", 1.30),
        ],
    )
    def test_all_catalog_codes(self, raw: str, expected: float) -> None:
        st = _subtask(difficulty_modifier_raw=raw)
        assert calc_m_dificultad(st) == pytest.approx(expected)

    def test_none_raw_returns_default(self) -> None:
        st = _subtask(difficulty_modifier_raw=None)
        assert calc_m_dificultad(st) == 1.0

    def test_unknown_raw_returns_default(self) -> None:
        st = _subtask(difficulty_modifier_raw="DESCONOCIDO")
        assert calc_m_dificultad(st) == 1.0

    def test_strips_whitespace(self) -> None:
        st = _subtask(difficulty_modifier_raw="  B09  ")
        assert calc_m_dificultad(st) == pytest.approx(1.20)


# ── M_lider ───────────────────────────────────────────────────────────────


class TestMLider:
    def test_always_one_in_mvp(self) -> None:
        """MVP: m_lider siempre es 1.0 hasta integración GitHub."""
        for size in ["XS", "S", "M", "L", "XL"]:
            st = _subtask(complexity_size=size)
            assert calc_m_lider(st) == 1.0

    def test_returns_float(self) -> None:
        assert isinstance(calc_m_lider(_subtask()), float)


# ── M_cooperacion ─────────────────────────────────────────────────────────


class TestMCooperacion:
    def test_no_changelog_returns_default(self) -> None:
        st = _subtask(raw_changelog=None)
        assert calc_m_cooperacion(st) == 1.0

    def test_empty_changelog_returns_default(self) -> None:
        st = _subtask(raw_changelog='{"histories": []}')
        assert calc_m_cooperacion(st) == 1.0

    def test_fast_unblock_within_24h_gives_bonus(self) -> None:
        """Desbloqueó a compañero en 2h hábiles → bonus cooperación."""
        # Lunes 2026-05-18: CDMX está en CDT (UTC-5).
        # 15:00 UTC = 10:00 CDMX (horario hábil).
        # 17:00 UTC = 12:00 CDMX → 2 horas hábiles de bloqueo.
        base = datetime(2026, 5, 18, 15, 0, tzinfo=UTC)  # 10:00 CDMX
        changelog = _changelog_with_blocking(base, base + timedelta(hours=2))
        st = _subtask(raw_changelog=changelog)
        assert calc_m_cooperacion(st) == pytest.approx(_M_COOPERACION_BONUS)

    def test_slow_unblock_over_24h_gives_no_bonus(self) -> None:
        """Bloqueado varios días → excede 24h hábiles → sin bonus."""
        # Lunes 15:00 UTC (10:00 CDMX) → Viernes 20:00 UTC (15:00 CDMX)
        # = 4 días hábiles completos >> 24h hábiles
        base = datetime(2026, 5, 18, 15, 0, tzinfo=UTC)
        changelog = _changelog_with_blocking(base, base + timedelta(days=5))
        st = _subtask(raw_changelog=changelog)
        assert calc_m_cooperacion(st) == pytest.approx(1.0)

    def test_invalid_json_returns_default(self) -> None:
        st = _subtask(raw_changelog="not-valid-json{")
        assert calc_m_cooperacion(st) == 1.0


# ── calc_all_multipliers ───────────────────────────────────────────────────


class TestCalcAllMultipliers:
    def test_returns_all_five_keys(self) -> None:
        st = _subtask()
        result = calc_all_multipliers(st)
        assert set(result.keys()) == {
            "m_calidad",
            "m_eficiencia",
            "m_dificultad",
            "m_lider",
            "m_cooperacion",
        }

    def test_all_default_subtask_gives_all_ones(self) -> None:
        """Subtask sin datos especiales → todos los multiplicadores = 1.0."""
        st = _subtask()
        result = calc_all_multipliers(st)
        for key, val in result.items():
            assert val == pytest.approx(1.0), f"{key} debería ser 1.0"

    def test_first_pass_reflected_in_calidad(self) -> None:
        st = _subtask(qa_first_pass=True, qa_attempts=1)
        result = calc_all_multipliers(st)
        assert result["m_calidad"] == pytest.approx(1.20)
        # Resto sigue siendo 1.0
        assert result["m_eficiencia"] == 1.0
        assert result["m_dificultad"] == 1.0
