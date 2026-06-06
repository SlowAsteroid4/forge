"""WP-15 — tests de corrección de identidades y áreas.

Verifica la lógica de scripts/wp15_fix_identities.apply_wp15:
- los diseñadores reales quedan en DESIGN,
- Jesús queda role='PO' (gobierno) PERO area='DESIGN' (cuenta en producción),
- "Equipo de Producto" (cuenta-grupo) se atribuye a DESIGN, sin área fantasma PO,
- idempotencia y anti-regresión (costos y cp_approved_at intactos).
"""

from datetime import datetime

import pytest

from forge.db.models.audit_log import AuditLog
from forge.db.models.player import Player
from forge.db.models.subtask import Subtask
from forge.repositories.player import LEADERBOARD_AREAS
from scripts.wp15_fix_identities import EDP_ID, JESUS_ID, apply_wp15


def _seed(session) -> None:
    """Pre-estado realista anterior a WP-15."""
    session.add(
        Player(
            id=JESUS_ID,
            jira_account_id="jesus-acc",
            display_name="Jesús Mancilla",
            area="DESIGN",
            employment_type="internal",
            is_lead=False,
            is_active=True,
            role=None,
        )
    )
    session.add(
        Player(
            id=EDP_ID,
            jira_account_id="edp-group-acc",
            display_name="Equipo de Producto",
            area="PO",  # área fantasma
            employment_type="internal",
            is_lead=False,
            is_active=True,
        )
    )
    # Un dev con costo capturado, para anti-regresión.
    session.add(
        Player(
            id=2,
            jira_account_id="alan-acc",
            display_name="Alan",
            area="BE",
            employment_type="external",
            is_lead=False,
            is_active=True,
            monthly_salary=45000,
            hourly_rate=250,
        )
    )
    # 3 design subtasks del grupo, etiquetadas PO, una con CP aprobado.
    for i, approved in enumerate([None, None, datetime(2026, 5, 1)]):
        session.add(
            Subtask(
                jira_key=f"YAP-{900 + i}",
                issue_type="Design Sub-task",
                area="PO",
                summary=f"UI/UX {i}",
                status="Done",
                assignee_player_id=EDP_ID,
                cp=3,
                cp_approved_at=approved,
            )
        )
    session.commit()


def test_designers_in_design_and_no_phantom_area(test_session):
    _seed(test_session)
    apply_wp15(test_session)
    test_session.commit()

    jesus = test_session.get(Player, JESUS_ID)
    edp = test_session.get(Player, EDP_ID)
    assert jesus.area == "DESIGN"
    assert edp.area == "DESIGN"
    # Ningún player ni subtask queda como área fantasma PO.
    assert test_session.query(Subtask).filter(Subtask.area == "PO").count() == 0


def test_jesus_is_po_but_counts_in_production(test_session):
    _seed(test_session)
    apply_wp15(test_session)
    test_session.commit()

    jesus = test_session.get(Player, JESUS_ID)
    assert jesus.role == "PO"  # rol de gobierno
    assert jesus.area == "DESIGN"  # NO sale de producción
    assert jesus.area in LEADERBOARD_AREAS  # participa en leaderboard


def test_group_subtasks_attributed_to_design(test_session):
    _seed(test_session)
    summary = apply_wp15(test_session)
    test_session.commit()

    assert summary["subtasks_remapped"] == 3
    rows = test_session.query(Subtask).filter(Subtask.assignee_player_id == EDP_ID).all()
    assert rows and all(r.area == "DESIGN" for r in rows)


def test_audit_trail_written(test_session):
    _seed(test_session)
    apply_wp15(test_session)
    test_session.commit()

    events = {e.event_type for e in test_session.query(AuditLog).all()}
    assert "player_role_set" in events
    assert "player_area_corrected" in events
    assert "subtask_area_remapped_from_group" in events


def test_idempotent(test_session):
    _seed(test_session)
    apply_wp15(test_session)
    test_session.commit()
    second = apply_wp15(test_session)
    test_session.commit()
    assert second == {"area_corrected": 0, "role_set": 0, "subtasks_remapped": 0}


def test_costs_and_cp_immutability_intact(test_session):
    _seed(test_session)
    cp_before = (
        test_session.query(Subtask).filter(Subtask.cp_approved_at.isnot(None)).count()
    )
    apply_wp15(test_session)
    test_session.commit()

    # Costos no tocados.
    alan = test_session.get(Player, 2)
    assert float(alan.monthly_salary) == 45000
    assert float(alan.hourly_rate) == 250
    # Inmutabilidad CP: el conteo de cp_approved_at no cambia.
    cp_after = (
        test_session.query(Subtask).filter(Subtask.cp_approved_at.isnot(None)).count()
    )
    assert cp_after == cp_before == 1


@pytest.mark.parametrize("missing_id", [JESUS_ID, EDP_ID])
def test_no_silent_pass_when_key_player_missing(test_session, missing_id):
    """Si falta Jesús o EdP, debe fallar fuerte (no inventar)."""
    # Sólo sembramos uno de los dos.
    keep = EDP_ID if missing_id == JESUS_ID else JESUS_ID
    area = "PO" if keep == EDP_ID else "DESIGN"
    test_session.add(
        Player(
            id=keep,
            jira_account_id=f"acc-{keep}",
            display_name=f"P{keep}",
            area=area,
            employment_type="internal",
            is_lead=False,
            is_active=True,
        )
    )
    test_session.commit()
    with pytest.raises(SystemExit):
        apply_wp15(test_session)
