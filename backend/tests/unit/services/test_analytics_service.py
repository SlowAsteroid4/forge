"""Tests para AnalyticsService (WP-07a)."""

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from forge.db.models.cycle import Cycle
from forge.db.models.player import Player
from forge.db.models.subtask import Subtask
from forge.services.analytics_service import AnalyticsService, _parse_time_per_status

# ──────────────────────────────────────────────
# Factories
# ──────────────────────────────────────────────

def _cycle(
    session: Session,
    name: str,
    status: str = "closed",
    start_offset_weeks: int = 0,
) -> Cycle:
    today = date.today()
    start = today - timedelta(weeks=start_offset_weeks)
    end = start + timedelta(days=4)
    iso = start.isocalendar()
    c = Cycle(
        iso_year=iso[0],
        iso_week=iso[1],
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
) -> Player:
    p = Player(
        jira_account_id=jira_id,
        display_name=name,
        email=f"{jira_id}@yapsi.com",
        area=area,
        employment_type="internal",
        is_lead=False,
        is_active=True,
    )
    session.add(p)
    session.flush()
    return p


def _subtask(
    session: Session,
    jira_key: str,
    status: str = "Done",
    area: str = "BE",
    cp: int | None = None,
    cycle_id: int | None = None,
    assignee_id: int | None = None,
    qa_first_pass: bool | None = None,
    dev_resp_h: float | None = None,
    qa_h: float | None = None,
    review_h: float | None = None,
    blocked_h: float | None = None,
    waiting_h: float | None = None,
    done_at: datetime | None = None,
) -> Subtask:
    s = Subtask(
        jira_key=jira_key,
        issue_type="Sub-task",
        summary=f"Test {jira_key}",
        status=status,
        area=area,
        cp=cp,
        cycle_id=cycle_id,
        assignee_player_id=assignee_id,
        qa_first_pass=qa_first_pass,
        dev_resp_biz_hours=dev_resp_h,
        qa_biz_hours=qa_h,
        review_biz_hours=review_h,
        blocked_biz_hours=blocked_h,
        waiting_biz_hours=waiting_h,
        done_at=done_at or datetime.utcnow(),
        last_synced_at=datetime.utcnow(),
    )
    session.add(s)
    session.flush()
    return s


# ──────────────────────────────────────────────
# throughput_by_cycle
# ──────────────────────────────────────────────

class TestThroughputByCycle:
    def test_sums_cp_and_count_per_cycle(self, test_session: Session) -> None:
        c1 = _cycle(test_session, "C-01", status="closed", start_offset_weeks=2)
        c2 = _cycle(test_session, "C-02", status="closed", start_offset_weeks=1)

        _subtask(test_session, "S-01", cp=5, cycle_id=c1.id)
        _subtask(test_session, "S-02", cp=3, cycle_id=c1.id)
        _subtask(test_session, "S-03", cp=8, cycle_id=c2.id)
        _subtask(test_session, "S-04", status="Backlog", cp=99, cycle_id=c1.id)
        test_session.commit()

        svc = AnalyticsService(test_session)
        result = svc.throughput_by_cycle(last_n=10)

        assert len(result) == 2
        # El más reciente va primero
        newer = next(r for r in result if r["cycle_id"] == c2.id)
        older = next(r for r in result if r["cycle_id"] == c1.id)
        assert newer["total_cp"] == 8
        assert newer["done_count"] == 1
        assert older["total_cp"] == 8  # 5+3 (S-04 no es Done)
        assert older["done_count"] == 2

    def test_respects_last_n_limit(self, test_session: Session) -> None:
        for i in range(5):
            c = _cycle(test_session, f"C-{i:02}", status="closed", start_offset_weeks=i + 1)
            _subtask(test_session, f"S-{i}", cp=2, cycle_id=c.id)
        test_session.commit()

        svc = AnalyticsService(test_session)
        result = svc.throughput_by_cycle(last_n=3)
        assert len(result) == 3

    def test_returns_empty_when_no_cycles(self, test_session: Session) -> None:
        svc = AnalyticsService(test_session)
        result = svc.throughput_by_cycle()
        assert result == []

    def test_null_cp_counted_as_zero(self, test_session: Session) -> None:
        c = _cycle(test_session, "C-null", status="closed", start_offset_weeks=1)
        _subtask(test_session, "S-null-cp", cp=None, cycle_id=c.id)
        test_session.commit()

        svc = AnalyticsService(test_session)
        result = svc.throughput_by_cycle(last_n=5)
        row = next(r for r in result if r["cycle_id"] == c.id)
        assert row["total_cp"] == 0
        assert row["done_count"] == 1


# ──────────────────────────────────────────────
# cp_by_area
# ──────────────────────────────────────────────

class TestCpByArea:
    def test_groups_done_subtasks_by_area(self, test_session: Session) -> None:
        c = _cycle(test_session, "C-area", status="closed", start_offset_weeks=1)
        _subtask(test_session, "S-BE-1", area="BE", cp=5, cycle_id=c.id)
        _subtask(test_session, "S-BE-2", area="BE", cp=3, cycle_id=c.id)
        _subtask(test_session, "S-FE-1", area="FE", cp=7, cycle_id=c.id)
        _subtask(test_session, "S-FE-pend", area="FE", status="Active", cp=10, cycle_id=c.id)
        test_session.commit()

        svc = AnalyticsService(test_session)
        result = svc.cp_by_area(scope="window")

        by_area = {r["area"]: r for r in result}
        assert by_area["BE"]["total_cp"] == 8
        assert by_area["FE"]["total_cp"] == 7
        assert "FE" in by_area  # S-FE-pend excluido (no Done)

    def test_empty_when_no_closed_cycles(self, test_session: Session) -> None:
        c = _cycle(test_session, "C-active", status="active", start_offset_weeks=0)
        _subtask(test_session, "S-1", cp=5, cycle_id=c.id)
        test_session.commit()

        svc = AnalyticsService(test_session)
        result = svc.cp_by_area(scope="window")
        assert result == []


# ──────────────────────────────────────────────
# qa_first_pass_by_dev
# ──────────────────────────────────────────────

class TestQaFirstPassByDev:
    def test_calculates_pct_correctly(self, test_session: Session) -> None:
        p = _player(test_session, "dev1", "Ana Gómez", area="FE")
        # 3 passed, 1 failed, 1 NULL (excluida del denominador)
        _subtask(test_session, "T-1", assignee_id=p.id, qa_first_pass=True)
        _subtask(test_session, "T-2", assignee_id=p.id, qa_first_pass=True)
        _subtask(test_session, "T-3", assignee_id=p.id, qa_first_pass=True)
        _subtask(test_session, "T-4", assignee_id=p.id, qa_first_pass=False)
        _subtask(test_session, "T-5", assignee_id=p.id, qa_first_pass=None)  # excluida
        test_session.commit()

        svc = AnalyticsService(test_session)
        result = svc.qa_first_pass_by_dev(scope="historical")

        assert len(result) == 1
        dev = result[0]
        assert dev["player_id"] == p.id
        assert dev["total"] == 4   # NULL excluido
        assert dev["passed"] == 3
        assert dev["first_pass_pct"] == 75.0

    def test_excludes_pm_po_areas(self, test_session: Session) -> None:
        po = _player(test_session, "po1", "PO User", area="PO")
        dev = _player(test_session, "dev2", "Dev User", area="BE")
        _subtask(test_session, "U-1", assignee_id=po.id, qa_first_pass=True)
        _subtask(test_session, "U-2", assignee_id=dev.id, qa_first_pass=True)
        test_session.commit()

        svc = AnalyticsService(test_session)
        result = svc.qa_first_pass_by_dev(scope="historical")

        ids = [r["player_id"] for r in result]
        assert po.id not in ids
        assert dev.id in ids

    def test_returns_empty_when_no_data(self, test_session: Session) -> None:
        svc = AnalyticsService(test_session)
        result = svc.qa_first_pass_by_dev(scope="historical")
        assert result == []


# ──────────────────────────────────────────────
# time_in_status
# ──────────────────────────────────────────────

class TestTimeInStatus:
    def test_sorts_by_total_time_descending(self, test_session: Session) -> None:
        c1 = _cycle(test_session, "C-t1", status="closed", start_offset_weeks=1)
        # BE tiene más tiempo total que FE
        _subtask(test_session, "TI-1", area="BE", cp=3, cycle_id=c1.id,
                 dev_resp_h=20.0, qa_h=5.0, review_h=2.0)
        _subtask(test_session, "TI-2", area="FE", cp=2, cycle_id=c1.id,
                 dev_resp_h=4.0, qa_h=1.0)
        test_session.commit()

        svc = AnalyticsService(test_session)
        result = svc.time_in_status(group_by="area", scope="window")

        assert len(result) == 2
        assert result[0]["display_name"] == "BE"  # mayor total
        assert result[1]["display_name"] == "FE"

    def test_sums_all_buckets_per_area(self, test_session: Session) -> None:
        c1 = _cycle(test_session, "C-sum", status="closed", start_offset_weeks=1)
        _subtask(test_session, "TI-sum", area="DB", cp=1, cycle_id=c1.id,
                 dev_resp_h=10.0, qa_h=3.0, review_h=2.0, blocked_h=1.0, waiting_h=0.5)
        test_session.commit()

        svc = AnalyticsService(test_session)
        result = svc.time_in_status(group_by="area", scope="window")

        db_row = next(r for r in result if r["display_name"] == "DB")
        assert db_row["dev_resp_h"] == 10.0
        assert db_row["qa_h"] == 3.0
        assert db_row["review_h"] == 2.0
        assert db_row["blocked_h"] == 1.0
        assert db_row["waiting_h"] == 0.5
        assert db_row["total_h"] == pytest.approx(16.5)


# ──────────────────────────────────────────────
# _parse_time_per_status (utilidad de changelog)
# ──────────────────────────────────────────────

class TestParseTimePerStatus:
    def test_returns_empty_for_none(self) -> None:
        assert _parse_time_per_status(None) == {}

    def test_returns_empty_for_invalid_json(self) -> None:
        assert _parse_time_per_status("not json") == {}

    def test_returns_empty_for_no_status_changes(self) -> None:
        changelog = '{"histories": [{"created": "2026-01-01T10:00:00+00:00", "items": [{"field": "assignee", "toString": "X"}]}]}'
        assert _parse_time_per_status(changelog) == {}

    def test_parses_simple_transition_chain(self) -> None:
        # Timestamps en CDMX (UTC-6) para que caigan en business hours (09:00–18:00 CDMX)
        # Active 09:00 → In Review 13:00 → Done 09:00 siguiente día
        changelog = """{
            "histories": [
                {
                    "created": "2026-01-05T09:00:00-06:00",
                    "items": [{"field": "status", "toString": "Active"}]
                },
                {
                    "created": "2026-01-05T13:00:00-06:00",
                    "items": [{"field": "status", "toString": "In Review"}]
                },
                {
                    "created": "2026-01-06T09:00:00-06:00",
                    "items": [{"field": "status", "toString": "Done"}]
                }
            ]
        }"""
        result = _parse_time_per_status(changelog)
        # "Active": 09:00–13:00 CDMX Lun = 4 h hábiles
        assert "Active" in result
        assert result["Active"] == pytest.approx(4.0, abs=0.01)
        # "In Review": 13:00–18:00 CDMX Lun (sin lunch 14-15) = 4 h
        assert "In Review" in result
        assert result["In Review"] > 0
        # "Done" no tiene duración medida (es el último estado)
        assert "Done" not in result


# ──────────────────────────────────────────────
# WP-17a: Quality, vs ciclo anterior, canónico
# ──────────────────────────────────────────────

class TestQualitySummary:
    def test_metrics_and_delta_vs_previous(self, test_session: Session) -> None:
        prev = _cycle(test_session, "C-prev", status="closed", start_offset_weeks=2)
        ref = _cycle(test_session, "C-ref", status="closed", start_offset_weeks=1)
        # ref: 2 probadas (qa_first_pass set), 1 por probar (In QA), avg qa = (10+20)/2=15
        _subtask(test_session, "R-1", cycle_id=ref.id, qa_first_pass=True, qa_h=10.0)
        _subtask(test_session, "R-2", cycle_id=ref.id, qa_first_pass=False, qa_h=20.0)
        _subtask(test_session, "R-3", status="In QA", cycle_id=ref.id)
        # prev: 1 probada, avg qa = 5
        _subtask(test_session, "P-1", cycle_id=prev.id, qa_first_pass=True, qa_h=5.0)
        test_session.commit()

        svc = AnalyticsService(test_session)
        res = svc.quality_summary(cycle_id=ref.id)

        assert res["reference_cycle"]["cycle_id"] == ref.id
        assert res["previous_cycle"]["cycle_id"] == prev.id
        assert res["tested"]["current"] == 2
        assert res["tested"]["previous"] == 1
        assert res["tested"]["delta_abs"] == 1
        assert res["pending"]["current"] == 1
        assert res["avg_qa_hours"]["current"] == pytest.approx(15.0)
        assert res["avg_qa_hours"]["previous"] == pytest.approx(5.0)

    def test_no_previous_cycle_means_sin_comparativa(self, test_session: Session) -> None:
        ref = _cycle(test_session, "C-only", status="closed", start_offset_weeks=1)
        _subtask(test_session, "O-1", cycle_id=ref.id, qa_first_pass=True, qa_h=8.0)
        test_session.commit()

        svc = AnalyticsService(test_session)
        res = svc.quality_summary(cycle_id=ref.id)
        assert res["previous_cycle"] is None
        assert res["tested"]["previous"] is None
        assert res["tested"]["delta_abs"] is None
        assert res["tested"]["delta_pct"] is None

    def test_zero_previous_yields_null_pct_not_infinity(self, test_session: Session) -> None:
        prev = _cycle(test_session, "C-zprev", status="closed", start_offset_weeks=2)
        ref = _cycle(test_session, "C-zref", status="closed", start_offset_weeks=1)
        _subtask(test_session, "Z-ref", cycle_id=ref.id, qa_first_pass=True)
        # prev sin probadas → previous=0
        _subtask(test_session, "Z-prev", status="Backlog", cycle_id=prev.id)
        test_session.commit()

        svc = AnalyticsService(test_session)
        res = svc.quality_summary(cycle_id=ref.id)
        assert res["tested"]["previous"] == 0
        assert res["tested"]["delta_pct"] is None  # no +inf inventado


class TestQaFirstPassVsPrevious:
    def test_dev_current_previous_delta(self, test_session: Session) -> None:
        prev = _cycle(test_session, "Q-prev", status="closed", start_offset_weeks=2)
        ref = _cycle(test_session, "Q-ref", status="closed", start_offset_weeks=1)
        dev = _player(test_session, "dev-1", "Dev Uno", area="BE")
        # ref: 1/2 pass = 50%
        _subtask(test_session, "QR-1", cycle_id=ref.id, assignee_id=dev.id, qa_first_pass=True)
        _subtask(test_session, "QR-2", cycle_id=ref.id, assignee_id=dev.id, qa_first_pass=False)
        # prev: 1/1 pass = 100%
        _subtask(test_session, "QP-1", cycle_id=prev.id, assignee_id=dev.id, qa_first_pass=True)
        test_session.commit()

        svc = AnalyticsService(test_session)
        res = svc.qa_first_pass_vs_previous(cycle_id=ref.id)
        row = next(d for d in res["devs"] if d["player_id"] == dev.id)
        assert row["first_pass_pct"] == pytest.approx(50.0)
        assert row["previous_pct"] == pytest.approx(100.0)
        assert row["delta_pts"] == pytest.approx(-50.0)


class TestTimeCanonical:
    def test_bucket_sum_matches_total(self, test_session: Session) -> None:
        ref = _cycle(test_session, "T-ref", status="closed", start_offset_weeks=1)
        _subtask(
            test_session, "TC-1", area="BE", cycle_id=ref.id,
            dev_resp_h=10.0, qa_h=4.0, review_h=2.0, blocked_h=1.0, waiting_h=3.0,
        )
        test_session.commit()

        svc = AnalyticsService(test_session)
        rows = svc.time_canonical(group_by="area", scope="window")
        be = next(r for r in rows if r["group_key"] == "BE")
        # Re-etiquetado WP-07h → canónico
        assert be["by_canonical"]["In Progress"] == pytest.approx(10.0)
        assert be["by_canonical"]["In QA"] == pytest.approx(4.0)
        assert be["by_canonical"]["In Review"] == pytest.approx(2.0)
        assert be["by_canonical"]["Blocked"] == pytest.approx(1.0)
        assert be["by_canonical"]["Waiting"] == pytest.approx(3.0)
        # La suma de canónicos == total_h
        assert sum(be["by_canonical"].values()) == pytest.approx(be["total_h"])
        assert be["total_h"] == pytest.approx(20.0)

    def test_area_filter_for_design(self, test_session: Session) -> None:
        ref = _cycle(test_session, "T-design", status="closed", start_offset_weeks=1)
        designer = _player(test_session, "des-1", "Jesús", area="DESIGN")
        _subtask(test_session, "DD-1", area="DESIGN", cycle_id=ref.id,
                 assignee_id=designer.id, dev_resp_h=5.0)
        _subtask(test_session, "BB-1", area="BE", cycle_id=ref.id, dev_resp_h=99.0)
        test_session.commit()

        svc = AnalyticsService(test_session)
        rows = svc.time_canonical(group_by="player", scope="window", area_filter="DESIGN")
        assert all(r["area"] == "DESIGN" for r in rows)
        assert any(r["display_name"] == "Jesús" for r in rows)
