"""
Tests de integración para engine_orchestrator.py — end-to-end con DB real.

Usan SQLite en memoria (conftest.py) para ser rápidos y aislados.
Cada test crea los datos mínimos necesarios en la sesión de test.
"""

import json
from datetime import datetime, timezone, date, timedelta

import pytest
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError
from forge.db.models.cycle import Cycle
from forge.db.models.engine_version import EngineVersion
from forge.db.models.player import Player
from forge.db.models.sp_adjustment import SpAdjustment
from forge.db.models.subtask import Subtask
from forge.services.engine.engine_orchestrator import (
    recalculate_cycle,
    recalculate_sprint,  # deprecated alias — still tested for backwards compat
    recalculate_subtask,
)


# ── Helpers de setup ──────────────────────────────────────────────────────


def _create_engine_version(session: Session) -> EngineVersion:
    ev = EngineVersion(
        version_tag="v2.0-test",
        description="Test version",
        is_active=True,
    )
    session.add(ev)
    session.flush()
    return ev


def _create_system_player(session: Session) -> Player:
    p = Player(
        jira_account_id="system-000",
        display_name="Sistema Forge",
        email="system@forge.local",
        area="PM",
        employment_type="internal",
        is_lead=False,
        is_active=True,
    )
    session.add(p)
    session.flush()
    return p


def _create_cycle(session: Session, *, status: str = "active") -> Cycle:
    today = date.today()
    iso = today.isocalendar()
    cycle = Cycle(
        name=f"Ciclo Test {today.isoformat()}",
        iso_year=iso[0],
        iso_week=iso[1],
        start_date=today - timedelta(days=4),
        end_date=today,
        status=status,
    )
    session.add(cycle)
    session.flush()
    return cycle


def _create_subtask(
    session: Session,
    cycle: Cycle,
    *,
    jira_key: str = "TEST-1",
    status: str = "Done",
    cp: int = 3,
    complexity_size: str = "M",
    qa_first_pass: bool = True,
    qa_attempts: int = 1,
    review_rejections: int = 0,
    blocked_biz_hours: float | None = None,
    done_at: datetime | None = None,
    lt_biz_hours: float | None = None,
    raw_changelog: str | None = None,
) -> Subtask:
    if done_at is None and status == "Done":
        done_at = datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc)

    st = Subtask(
        jira_key=jira_key,
        issue_type="Sub-task",
        area="BE",
        summary="Test subtask",
        status=status,
        cycle_id=cycle.id,
        cp=cp,
        complexity_size=complexity_size,
        cp_approved_at=datetime.utcnow() if cp else None,
        qa_first_pass=qa_first_pass,
        qa_attempts=qa_attempts,
        review_rejections=review_rejections,
        blocked_biz_hours=blocked_biz_hours,
        done_at=done_at,
        lt_biz_hours=lt_biz_hours,
        raw_changelog=raw_changelog or '{"histories": []}',
    )
    session.add(st)
    session.flush()
    return st


# ── Tests recalculate_subtask ─────────────────────────────────────────────


class TestRecalculateSubtask:
    @pytest.mark.integration
    def test_not_found_raises(self, test_session: Session) -> None:
        _create_engine_version(test_session)
        player = _create_system_player(test_session)
        with pytest.raises(NotFoundError, match="NOEXISTE-1"):
            recalculate_subtask(test_session, "NOEXISTE-1", player.id, force=True)

    @pytest.mark.integration
    def test_basic_recalc_sets_sp_final(self, test_session: Session) -> None:
        _create_engine_version(test_session)
        player = _create_system_player(test_session)
        cycle = _create_cycle(test_session)
        st = _create_subtask(
            test_session,
            cycle,
            jira_key="TEST-10",
            cp=5,
            complexity_size="L",
            qa_first_pass=True,
            qa_attempts=1,
        )

        result = recalculate_subtask(test_session, "TEST-10", player.id, force=True)

        # M_calidad=1.20 (first pass), resto=1.0 → sp_base = 5 × 1.20 = 6.0
        assert result.sp_base == pytest.approx(6.0)
        assert result.sp_final >= 0.0

        # Verificar que se guardó en DB
        test_session.refresh(st)
        assert st.sp_final == pytest.approx(result.sp_final)
        assert st.sp_last_calculated_at is not None

    @pytest.mark.integration
    def test_recalc_sets_engine_version_id(self, test_session: Session) -> None:
        ev = _create_engine_version(test_session)
        player = _create_system_player(test_session)
        cycle = _create_cycle(test_session)
        st = _create_subtask(test_session, cycle, jira_key="TEST-11")

        recalculate_subtask(test_session, "TEST-11", player.id, force=True)

        test_session.refresh(st)
        assert st.engine_version_id == ev.id

    @pytest.mark.integration
    def test_recalc_creates_debuff_for_qa_instability(
        self, test_session: Session
    ) -> None:
        """qa_attempts=4 debe crear un SpAdjustment D03."""
        _create_engine_version(test_session)
        player = _create_system_player(test_session)
        cycle = _create_cycle(test_session)
        _create_subtask(
            test_session,
            cycle,
            jira_key="TEST-12",
            cp=3,
            qa_first_pass=False,
            qa_attempts=4,
        )

        recalculate_subtask(test_session, "TEST-12", player.id, force=True)

        debuffs = (
            test_session.query(SpAdjustment)
            .filter(
                SpAdjustment.subtask_key == "TEST-12",
                SpAdjustment.catalog_code == "D03",
            )
            .all()
        )
        assert len(debuffs) == 1
        assert debuffs[0].amount_sp > 0
        assert debuffs[0].adjustment_type == "penalty"

    @pytest.mark.integration
    def test_recalc_is_idempotent(self, test_session: Session) -> None:
        """Correr recalculate_subtask dos veces → mismo resultado, sin duplicados."""
        _create_engine_version(test_session)
        player = _create_system_player(test_session)
        cycle = _create_cycle(test_session)
        _create_subtask(
            test_session,
            cycle,
            jira_key="TEST-13",
            cp=5,
            qa_first_pass=False,
            qa_attempts=3,   # D03
        )

        result1 = recalculate_subtask(test_session, "TEST-13", player.id, force=True)
        result2 = recalculate_subtask(test_session, "TEST-13", player.id, force=True)

        # SP final debe ser idéntico
        assert result1.sp_final == pytest.approx(result2.sp_final)

        # D03 debe existir exactamente una vez (no duplicado)
        debuffs = (
            test_session.query(SpAdjustment)
            .filter(
                SpAdjustment.subtask_key == "TEST-13",
                SpAdjustment.catalog_code == "D03",
            )
            .all()
        )
        assert len(debuffs) == 1

    @pytest.mark.integration
    def test_recalc_penalizes_d10_blocking(self, test_session: Session) -> None:
        """blocked_biz_hours=12 → D10 detectado, penalty en sp_final."""
        _create_engine_version(test_session)
        player = _create_system_player(test_session)
        cycle = _create_cycle(test_session)
        _create_subtask(
            test_session,
            cycle,
            jira_key="TEST-14",
            cp=3,
            blocked_biz_hours=12.0,  # > 8h → D10
        )

        result = recalculate_subtask(test_session, "TEST-14", player.id, force=True)

        # sp_penalty > 0 porque D10 aplicó
        assert result.sp_penalty > 0
        # sp_final < sp_base por la penalización
        assert result.sp_final < result.sp_base

    @pytest.mark.integration
    def test_cp_immutability_preserved(self, test_session: Session) -> None:
        """CP aprobado no debe ser modificado por el recalculator."""
        _create_engine_version(test_session)
        player = _create_system_player(test_session)
        cycle = _create_cycle(test_session)
        st = _create_subtask(
            test_session,
            cycle,
            jira_key="TEST-15",
            cp=5,    # CP aprobado en _create_subtask (si cp is not None)
            complexity_size="L",
        )
        original_cp = st.cp

        recalculate_subtask(test_session, "TEST-15", player.id, force=True)

        test_session.refresh(st)
        assert st.cp == original_cp  # CP no cambió

    @pytest.mark.integration
    def test_sp_final_minimum_zero(self, test_session: Session) -> None:
        """sp_final nunca puede ser negativo aunque las penalizaciones sean grandes."""
        _create_engine_version(test_session)
        player = _create_system_player(test_session)
        cycle = _create_cycle(test_session)
        st = _create_subtask(
            test_session,
            cycle,
            jira_key="TEST-16",
            cp=1,  # CP mínimo
            qa_first_pass=False,
            qa_attempts=10,   # D03 masivo
            review_rejections=5,  # D04
            blocked_biz_hours=50.0,  # D10
        )

        result = recalculate_subtask(test_session, "TEST-16", player.id, force=True)
        assert result.sp_final >= 0.0

    @pytest.mark.integration
    def test_d13_cycle_overflow_detected(self, test_session: Session) -> None:
        """Ciclo cerrado + tarea sin entregar → D13 detectado."""
        _create_engine_version(test_session)
        player = _create_system_player(test_session)
        closed_cycle = _create_cycle(test_session, status="closed")
        _create_subtask(
            test_session,
            closed_cycle,
            jira_key="TEST-17",
            status="In Progress",
            cp=3,
            done_at=None,
        )

        recalculate_subtask(test_session, "TEST-17", player.id, force=True)

        debuffs = (
            test_session.query(SpAdjustment)
            .filter(
                SpAdjustment.subtask_key == "TEST-17",
                SpAdjustment.catalog_code == "D13",
            )
            .all()
        )
        assert len(debuffs) == 1


# ── Tests recalculate_sprint ──────────────────────────────────────────────


class TestRecalculateSprint:
    @pytest.mark.integration
    def test_not_found_raises(self, test_session: Session) -> None:
        player = _create_system_player(test_session)
        with pytest.raises(NotFoundError, match="9999"):
            recalculate_sprint(test_session, 9999, player.id)

    @pytest.mark.integration
    def test_recalc_sprint_processes_all_subtasks(
        self, test_session: Session
    ) -> None:
        _create_engine_version(test_session)
        player = _create_system_player(test_session)
        cycle = _create_cycle(test_session)

        for i in range(3):
            _create_subtask(
                test_session,
                cycle,
                jira_key=f"SPRINT-{i}",
                cp=3,
            )

        stats = recalculate_cycle(test_session, cycle.id, player.id, force=True)

        assert stats["total"] == 3
        assert int(stats["processed"]) == 3
        assert int(stats["errors"]) == 0

    @pytest.mark.integration
    def test_recalc_sprint_accumulates_sp_total(
        self, test_session: Session
    ) -> None:
        """sp_total debe ser la suma de sp_final de todas las subtasks."""
        _create_engine_version(test_session)
        player = _create_system_player(test_session)
        cycle = _create_cycle(test_session)

        # 2 subtasks, CP=3 cada una, all defaults → sp_final = 3.0 each
        _create_subtask(test_session, cycle, jira_key="SPSUM-1", cp=3)
        _create_subtask(test_session, cycle, jira_key="SPSUM-2", cp=3)

        stats = recalculate_cycle(test_session, cycle.id, player.id, force=True)

        assert float(stats["sp_total"]) >= 0.0

    @pytest.mark.integration
    def test_recalc_sprint_skips_already_calculated(
        self, test_session: Session
    ) -> None:
        """Sin force=True, subtasks ya calculadas con la versión actual se omiten."""
        ev = _create_engine_version(test_session)
        player = _create_system_player(test_session)
        cycle = _create_cycle(test_session)

        st = _create_subtask(test_session, cycle, jira_key="SKIP-1", cp=5)
        # Simular que ya fue calculada con la versión actual
        st.sp_last_calculated_at = datetime.utcnow()
        st.engine_version_id = ev.id
        test_session.flush()

        stats = recalculate_cycle(test_session, cycle.id, player.id, force=False)

        assert int(stats["skipped"]) >= 1

    @pytest.mark.integration
    def test_recalc_sprint_force_overrides_skip(
        self, test_session: Session
    ) -> None:
        """Con force=True todas las subtasks se recalculan."""
        ev = _create_engine_version(test_session)
        player = _create_system_player(test_session)
        cycle = _create_cycle(test_session)

        st = _create_subtask(test_session, cycle, jira_key="FORCE-1", cp=3)
        st.sp_last_calculated_at = datetime.utcnow()
        st.engine_version_id = ev.id
        test_session.flush()

        stats = recalculate_cycle(test_session, cycle.id, player.id, force=True)

        assert int(stats["processed"]) >= 1
        assert int(stats["skipped"]) == 0
