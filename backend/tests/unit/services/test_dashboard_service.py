"""Tests para DashboardService (UC-02) — operando sobre Cycles."""

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError
from forge.db.models.cycle import Cycle
from forge.db.models.player import Player
from forge.db.models.project import Project
from forge.db.models.subtask import Subtask
from forge.services.dashboard_service import DashboardService, _delta_pct

# ──────────────────────────────────────────────
# Factories de fixtures
# ──────────────────────────────────────────────


def _cycle(
    session: Session,
    name: str = "Ciclo-Test",
    start_offset: int = -4,
    end_offset: int = 0,
    status: str = "active",
    start_date: date | None = None,
    end_date: date | None = None,
) -> Cycle:
    today = date.today()
    start = start_date or (today + timedelta(days=start_offset))
    end = end_date or (today + timedelta(days=end_offset))
    iso_cal = start.isocalendar()
    c = Cycle(
        iso_year=iso_cal[0],
        iso_week=iso_cal[1],
        name=name,
        start_date=start,
        end_date=end,
        status=status,
    )
    session.add(c)
    session.flush()
    return c


def _player(
    session: Session,
    jira_id: str,
    name: str,
    area: str = "BE",
    email: str | None = None,
) -> Player:
    p = Player(
        jira_account_id=jira_id,
        display_name=name,
        email=email or f"{jira_id}@yapsi.com",
        area=area,
        employment_type="internal",
        is_active=True,
    )
    session.add(p)
    session.flush()
    return p


def _subtask(
    session: Session,
    key: str,
    cycle_id: int | None = None,
    player_id: int | None = None,
    status: str = "In Progress",
    area: str = "BE",
    cp: int | None = None,
    sp_final: float | None = None,
    issue_type: str = "Backend Sub-task",
    project_code: str | None = None,
    complexity_size: str | None = None,
    cp_approval_required: bool = False,
    cp_approved_at: datetime | None = None,
    created_at_offset: int = 0,
    qa_first_pass: bool | None = None,
) -> Subtask:
    st = Subtask(
        jira_key=key,
        issue_type=issue_type,
        area=area,
        summary=f"Summary {key}",
        status=status,
        cycle_id=cycle_id,
        assignee_player_id=player_id,
        cp=cp,
        sp_final=sp_final,
        project_code=project_code,
        complexity_size=complexity_size,
        cp_approval_required=cp_approval_required,
        cp_approved_at=cp_approved_at,
        qa_first_pass=qa_first_pass,
    )
    if created_at_offset:
        st.created_at = datetime.utcnow() - timedelta(days=abs(created_at_offset))
    session.add(st)
    session.flush()
    return st


def _project(session: Session, code: str = "YAP") -> Project:
    p = Project(
        code=code,
        jira_prefix=f"[{code}]",
        internal_name=f"Project {code}",
        arena_name=f"Dungeon {code}",
        is_active=True,
    )
    session.add(p)
    session.flush()
    return p


# ──────────────────────────────────────────────
# Tests: sin ciclo activo
# ──────────────────────────────────────────────


def test_no_active_cycle_returns_empty_dashboard(test_session: Session) -> None:
    svc = DashboardService(test_session)

    result = svc.get_dashboard()

    assert result.cycle is None
    assert result.no_cycle_message is not None
    assert result.kpis is None
    assert result.area_progress == []


def test_cycle_id_not_found_raises(test_session: Session) -> None:
    svc = DashboardService(test_session)

    with pytest.raises(NotFoundError):
        svc.get_dashboard(cycle_id=9999)


# ──────────────────────────────────────────────
# Tests: cycle header
# ──────────────────────────────────────────────


def test_cycle_header_calculates_days_elapsed(test_session: Session) -> None:
    cycle = _cycle(test_session, start_offset=-4, end_offset=0)
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id)

    assert result.cycle is not None
    assert result.cycle.days_elapsed == 5   # 4 días antes + hoy
    assert result.cycle.days_total == 5     # 5 días en total (-4 a 0 inclusive)


def test_cycle_header_progress_pct_between_0_and_100(test_session: Session) -> None:
    cycle = _cycle(test_session)
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id)

    assert result.cycle is not None
    assert 0 <= result.cycle.progress_pct <= 100


# ──────────────────────────────────────────────
# Tests: KPI cards
# ──────────────────────────────────────────────


def test_kpis_cp_done_sums_done_subtasks(test_session: Session) -> None:
    cycle = _cycle(test_session)
    _subtask(test_session, "T-1", cycle_id=cycle.id, status="Done", cp=3)
    _subtask(test_session, "T-2", cycle_id=cycle.id, status="Done", cp=5)
    _subtask(test_session, "T-3", cycle_id=cycle.id, status="In Progress", cp=8)
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id)

    assert result.kpis is not None
    assert result.kpis.cp_done.value == 8.0  # solo Done: 3+5


def test_kpis_qa_first_pass_rate_calculates_correctly(test_session: Session) -> None:
    cycle = _cycle(test_session)
    _subtask(test_session, "T-10", cycle_id=cycle.id, status="Done", qa_first_pass=True)
    _subtask(test_session, "T-11", cycle_id=cycle.id, status="Done", qa_first_pass=True)
    _subtask(test_session, "T-12", cycle_id=cycle.id, status="Done", qa_first_pass=False)
    _subtask(test_session, "T-13", cycle_id=cycle.id, status="Done", qa_first_pass=None)  # no cuenta
    _subtask(test_session, "T-14", cycle_id=cycle.id, status="In Progress", qa_first_pass=True)  # no Done
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id)

    assert result.kpis is not None
    qfp = result.kpis.qa_first_pass
    assert qfp.total == 3   # solo Done con dato
    assert qfp.passed == 2
    assert abs(qfp.rate - 2 / 3) < 0.001


def test_kpis_qa_first_pass_empty_when_no_done(test_session: Session) -> None:
    cycle = _cycle(test_session)
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id)

    assert result.kpis is not None
    assert result.kpis.qa_first_pass.total == 0
    assert result.kpis.qa_first_pass.rate == 0.0


def test_kpis_no_cp_pending_or_sp_total_fields(test_session: Session) -> None:
    """cp_pending y sp_total no deben existir en KPICards (son de Arena)."""
    cycle = _cycle(test_session)
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id)

    assert result.kpis is not None
    assert not hasattr(result.kpis, "cp_pending")
    assert not hasattr(result.kpis, "sp_total")
    assert not hasattr(result.kpis, "bugs_derived")


def test_kpis_project_filter_applies(test_session: Session) -> None:
    cycle = _cycle(test_session)
    _project(test_session, "YAP")
    _project(test_session, "CRM")
    _subtask(test_session, "T-40", cycle_id=cycle.id, status="Done", cp=5, project_code="YAP")
    _subtask(test_session, "T-41", cycle_id=cycle.id, status="Done", cp=3, project_code="CRM")
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id, project_code="YAP")

    assert result.kpis is not None
    assert result.kpis.cp_done.value == 5.0


def test_kpis_comparison_with_previous_cycle(test_session: Session) -> None:
    today = date.today()
    prev = _cycle(test_session, "Ciclo-Prev", start_offset=-18, end_offset=-14, status="closed")
    curr = _cycle(test_session, "Ciclo-Curr", start_offset=-4, end_offset=0, status="active")
    _subtask(test_session, "T-50", cycle_id=prev.id, status="Done", cp=10)
    _subtask(test_session, "T-51", cycle_id=curr.id, status="Done", cp=12)
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=curr.id)

    assert result.kpis is not None
    assert result.kpis.cp_done.previous_value == 10.0
    assert result.kpis.cp_done.delta_pct == 20.0  # (12-10)/10*100


def test_kpis_delta_none_when_no_previous_cycle(test_session: Session) -> None:
    cycle = _cycle(test_session)
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id)

    assert result.kpis is not None
    assert result.kpis.cp_done.previous_value is None
    assert result.kpis.cp_done.delta_pct is None


# ──────────────────────────────────────────────
# Tests: progreso por área
# ──────────────────────────────────────────────


def test_area_progress_returns_all_6_areas(test_session: Session) -> None:
    """BUG se agregó como área de seguimiento (WP-20 ajuste)."""
    cycle = _cycle(test_session)
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id)

    areas = {ap.area for ap in result.area_progress}
    assert areas == {"BE", "FE", "DESIGN", "DB", "BUG", "QA"}


def test_area_progress_cp_done_correct(test_session: Session) -> None:
    cycle = _cycle(test_session)
    _subtask(test_session, "T-60", cycle_id=cycle.id, area="BE", status="Done", cp=5)
    _subtask(test_session, "T-61", cycle_id=cycle.id, area="BE", status="Done", cp=3)
    _subtask(test_session, "T-62", cycle_id=cycle.id, area="FE", status="Done", cp=8)
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id)

    be = next(a for a in result.area_progress if a.area == "BE")
    fe = next(a for a in result.area_progress if a.area == "FE")
    assert be.cp_done == 8.0
    assert fe.cp_done == 8.0


def test_area_progress_wip_bottleneck_detected(test_session: Session) -> None:
    cycle = _cycle(test_session)
    p = _player(test_session, "j-be", "Dev BE", area="BE")
    # BE threshold = 3, creamos 4 subtasks activas para el mismo dev
    for i in range(4):
        _subtask(
            test_session, f"T-7{i}", cycle_id=cycle.id,
            player_id=p.id, area="BE", status="In Progress"
        )
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id)

    be = next(a for a in result.area_progress if a.area == "BE")
    assert be.has_wip_bottleneck is True


def test_area_progress_no_bottleneck_within_threshold(test_session: Session) -> None:
    cycle = _cycle(test_session)
    p = _player(test_session, "j-fe", "Dev FE", area="FE")
    # FE threshold = 3, creamos 3 (exacto, no excede)
    for i in range(3):
        _subtask(
            test_session, f"T-8{i}", cycle_id=cycle.id,
            player_id=p.id, area="FE", status="In Progress"
        )
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id)

    fe = next(a for a in result.area_progress if a.area == "FE")
    assert fe.has_wip_bottleneck is False


# ──────────────────────────────────────────────
# Tests: estado de devs
# ──────────────────────────────────────────────


def test_player_status_productive(test_session: Session) -> None:
    cycle = _cycle(test_session)
    p = _player(test_session, "j-prod", "Dev Prod", area="BE")
    _subtask(test_session, "T-90", cycle_id=cycle.id, player_id=p.id, status="In Progress")
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id)

    dev = next((d for d in result.player_status if d.player_id == p.id), None)
    assert dev is not None
    assert dev.status == "productive"


def test_player_status_blocked_when_all_active_are_blocked(test_session: Session) -> None:
    cycle = _cycle(test_session)
    p = _player(test_session, "j-blk", "Dev Blocked", area="BE")
    _subtask(test_session, "T-100", cycle_id=cycle.id, player_id=p.id, status="Blocked")
    _subtask(test_session, "T-101", cycle_id=cycle.id, player_id=p.id, status="Waiting")
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id)

    dev = next(d for d in result.player_status if d.player_id == p.id)
    assert dev.status == "blocked"


def test_player_status_wip_high_when_exceeds_threshold(test_session: Session) -> None:
    cycle = _cycle(test_session)
    p = _player(test_session, "j-wip", "Dev WIP", area="BE")  # threshold=3
    for i in range(4):
        _subtask(test_session, f"T-11{i}", cycle_id=cycle.id, player_id=p.id, status="In Progress")
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id)

    dev = next(d for d in result.player_status if d.player_id == p.id)
    assert dev.status == "wip_high"


def test_player_status_inactive_when_all_done(test_session: Session) -> None:
    cycle = _cycle(test_session)
    p = _player(test_session, "j-done", "Dev Done", area="FE")
    _subtask(test_session, "T-120", cycle_id=cycle.id, player_id=p.id, status="Done")
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id)

    dev = next(d for d in result.player_status if d.player_id == p.id)
    assert dev.status == "inactive"


def test_player_status_wip_live_counts_all_non_terminal(test_session: Session) -> None:
    """wip_live cuenta subtasks activas sin filtro de ciclo; done_subtasks solo del ciclo."""
    cycle = _cycle(test_session)
    other_cycle = _cycle(
        test_session, "Ciclo 2025-W01", status="closed",
        start_date=date(2025, 1, 6), end_date=date(2025, 1, 10),
    )
    p = _player(test_session, "j-wlive", "Dev WipLive", area="DB")
    _subtask(test_session, "T-130", cycle_id=cycle.id, player_id=p.id, status="In Progress")
    _subtask(test_session, "T-131", cycle_id=other_cycle.id, player_id=p.id, status="In Progress")
    _subtask(test_session, "T-132", cycle_id=cycle.id, player_id=p.id, status="Done")
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id)

    dev = next(d for d in result.player_status if d.player_id == p.id)
    assert dev.wip_live == 2      # ambas In Progress sin importar ciclo
    assert dev.done_subtasks == 1  # solo Done en el ciclo actual


# ──────────────────────────────────────────────
# Tests: alertas
# ──────────────────────────────────────────────


def test_alerts_abandoned_subtask_older_than_14_days(test_session: Session) -> None:
    cycle = _cycle(test_session)
    _subtask(
        test_session, "T-OLD", cycle_id=cycle.id,
        status="In Progress", created_at_offset=20  # 20 días atrás
    )
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id)

    abandoned = [a for a in result.alerts if a.alert_type == "abandoned_subtask"]
    assert any(a.subtask_key == "T-OLD" for a in abandoned)


def test_alerts_no_abandoned_for_recent_subtask(test_session: Session) -> None:
    cycle = _cycle(test_session)
    _subtask(test_session, "T-NEW", cycle_id=cycle.id, status="In Progress")
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id)

    abandoned = [a for a in result.alerts if a.alert_type == "abandoned_subtask"]
    assert not any(a.subtask_key == "T-NEW" for a in abandoned)


def test_alerts_xxl_detected(test_session: Session) -> None:
    """WP-24: solo XXL genera alerta; L/XL ya no (el CP se auto-lockea en el sync)."""
    cycle = _cycle(test_session)
    _subtask(test_session, "T-XXL", cycle_id=cycle.id, complexity_size="XXL", cp=13)
    _subtask(
        test_session, "T-L", cycle_id=cycle.id, complexity_size="L", cp=5,
        cp_approval_required=True, cp_approved_at=None
    )
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id)

    xxl_alerts = [a for a in result.alerts if a.alert_type == "xxl_detected"]
    assert any(a.subtask_key == "T-XXL" for a in xxl_alerts)
    assert not any(a.subtask_key == "T-L" for a in xxl_alerts)


def test_alerts_wip_exceeded_alert_generated(test_session: Session) -> None:
    cycle = _cycle(test_session)
    p = _player(test_session, "j-wip2", "Dev WIP Alert", area="FE")  # threshold=3
    for i in range(4):
        _subtask(test_session, f"T-WIP{i}", cycle_id=cycle.id, player_id=p.id,
                 area="FE", status="In Progress")
    svc = DashboardService(test_session)

    result = svc.get_dashboard(cycle_id=cycle.id)

    wip_alerts = [a for a in result.alerts if a.alert_type == "wip_exceeded"]
    assert any(a.player_id == p.id for a in wip_alerts)


# ──────────────────────────────────────────────
# Tests: proyectos disponibles
# ──────────────────────────────────────────────


def test_available_projects_in_response(test_session: Session) -> None:
    _cycle(test_session)
    _project(test_session, "YAP")
    _project(test_session, "CRM")
    svc = DashboardService(test_session)

    result = svc.get_dashboard()

    codes = {p.code for p in result.available_projects}
    assert {"YAP", "CRM"}.issubset(codes)


# ──────────────────────────────────────────────
# Tests: helper puro _delta_pct
# ──────────────────────────────────────────────


def test_delta_pct_increase() -> None:
    assert _delta_pct(12.0, 10.0) == 20.0


def test_delta_pct_decrease() -> None:
    assert _delta_pct(8.0, 10.0) == -20.0


def test_delta_pct_no_previous() -> None:
    assert _delta_pct(10.0, None) is None


def test_delta_pct_previous_zero() -> None:
    assert _delta_pct(10.0, 0.0) is None
