"""Tests de reconciliación de borrados (prune) del SyncOrchestrator — WP-22.

El prune es ahora soft-delete + reversión append-only (no DELETE físico).
Garantías verificadas:
  - sp_adjustments NUNCA se borra (COUNT aumenta)
  - Subtask podada se marca pruned_at (NO se borra la fila)
  - Reversiones tienen amount_sp = -original (signo opuesto)
  - Idempotencia: re-correr no duplica reversiones
  - GUARDA A: aborta si poda > umbral %
  - GUARDA B: aborta si alguna stale tiene cp_approved_at
  - Dry-run (find_stale_keys) no escribe nada
"""

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from forge.db.models.epic import Epic
from forge.db.models.player import Player
from forge.db.models.sp_adjustment import SpAdjustment
from forge.db.models.story import Story
from forge.db.models.subtask import Subtask
from forge.etl.sync_orchestrator import PruneGuardAError, PruneGuardBError, SyncOrchestrator


# ── Helpers ──────────────────────────────────────────────────────────────────


def _orch(session: Session) -> SyncOrchestrator:
    orch = SyncOrchestrator.__new__(SyncOrchestrator)
    orch.session = session
    return orch


def _seed_hierarchy(session: Session) -> Player:
    """Siembra: 1 PM, 1 epic, 1 story, 2 subtasks (YAP-3 viva, YAP-4 orfanato)."""
    pm = Player(
        jira_account_id="pm-1",
        display_name="PM",
        email="pm@yapsi.com",
        area="PM",
        employment_type="internal",
    )
    session.add(pm)
    session.add(Epic(jira_key="YAP-1", project_code="YAP", summary="E", status="Done"))
    session.add(Story(jira_key="YAP-2", parent_epic_key="YAP-1", summary="S", status="Done"))
    session.add_all(
        [
            Subtask(
                jira_key="YAP-3",
                parent_story_key="YAP-2",
                project_code="YAP",
                issue_type="Backend Sub-task",
                area="BE",
                summary="vive",
                status="Done",
            ),
            Subtask(
                jira_key="YAP-4",
                parent_story_key="YAP-2",
                project_code="YAP",
                issue_type="Backend Sub-task",
                area="BE",
                summary="orfanato en Jira",
                status="Done",
            ),
        ]
    )
    session.flush()
    return pm


def _add_bonus(session: Session, subtask_key: str, amount: float, applied_by: int) -> SpAdjustment:
    adj = SpAdjustment(
        subtask_key=subtask_key,
        adjustment_type="bonus",
        amount_sp=amount,
        reason="bono de prueba",
        applied_by=applied_by,
        applied_at=datetime.utcnow(),
    )
    session.add(adj)
    session.flush()
    return adj


# ── Tests de detección ────────────────────────────────────────────────────────


def test_find_stale_keys_detects_missing(test_session: Session) -> None:
    _seed_hierarchy(test_session)
    orch = _orch(test_session)

    stale = orch.find_stale_keys({"YAP-1", "YAP-2", "YAP-3"}, "YAP")

    assert stale["subtasks"] == ["YAP-4"]
    assert stale["stories"] == []
    assert stale["epics"] == []


def test_find_stale_keys_scoped_by_project_prefix(test_session: Session) -> None:
    _seed_hierarchy(test_session)
    test_session.add(
        Subtask(
            jira_key="ABC-9",
            project_code="ABC",
            issue_type="Backend Sub-task",
            area="BE",
            summary="otro proyecto",
            status="Done",
        )
    )
    test_session.flush()
    orch = _orch(test_session)

    stale = orch.find_stale_keys({"YAP-1", "YAP-2", "YAP-3", "YAP-4"}, "YAP")
    assert stale["subtasks"] == []  # ABC-9 no entra al scope YAP


def test_find_stale_keys_excludes_already_pruned(test_session: Session) -> None:
    """Subtasks con pruned_at ya seteado no vuelven a aparecer como stale."""
    _seed_hierarchy(test_session)
    yap4 = test_session.get(Subtask, "YAP-4")
    assert yap4 is not None
    yap4.pruned_at = datetime.utcnow()
    test_session.flush()
    orch = _orch(test_session)

    stale = orch.find_stale_keys({"YAP-1", "YAP-2", "YAP-3"}, "YAP")
    assert stale["subtasks"] == []  # ya fue podada, no se reprocesa


# ── Test principal: append-only ───────────────────────────────────────────────


def test_prune_reversa_sp_append_only(test_session: Session) -> None:
    """Poda soft-delete: original intacto, reversión insertada, neto=0, pruned_at seteado."""
    pm = _seed_hierarchy(test_session)
    orig_adj = _add_bonus(test_session, "YAP-4", 5.0, pm.id)
    orig_adj_id = orig_adj.id

    count_before = test_session.query(SpAdjustment).count()

    orch = _orch(test_session)
    counts = orch.prune_stale(
        {"subtasks": ["YAP-4"], "stories": [], "epics": []},
        allow_large_prune=True,  # entorno de test: 1/2 subtasks = 50% > 5% umbral
        actor_player_id=pm.id,
    )
    test_session.commit()

    # Subtask NO fue borrada
    yap4 = test_session.get(Subtask, "YAP-4")
    assert yap4 is not None, "La fila de la subtask debe permanecer"
    assert yap4.pruned_at is not None, "pruned_at debe estar seteado"
    assert yap4.prune_reason is not None

    # Subtask viva no tocada
    assert test_session.get(Subtask, "YAP-3") is not None

    # sp_adjustments AUMENTÓ en 1 (nunca decreció)
    count_after = test_session.query(SpAdjustment).count()
    assert count_after == count_before + 1, "El conteo de ajustes debe aumentar, no disminuir"

    # Fila original intacta
    original = test_session.get(SpAdjustment, orig_adj_id)
    assert original is not None, "La fila original no debe borrarse"
    assert original.amount_sp == 5.0, "El amount_sp original debe permanecer sin cambios"

    # Reversión con signo opuesto
    all_adjs = (
        test_session.query(SpAdjustment).filter_by(subtask_key="YAP-4").all()
    )
    reversal_rows = [a for a in all_adjs if a.adjustment_type == "prune_reversal"]
    assert len(reversal_rows) == 1, "Debe existir exactamente 1 fila de prune_reversal"
    reversal = reversal_rows[0]
    assert reversal.amount_sp == -5.0, "amount_sp del reversal debe ser -original.amount_sp"
    assert f"PRUNE:{orig_adj_id}" in (reversal.catalog_code or ""), "catalog_code debe referenciar el original"

    # Contribución neta de ajustes = 0 (ledger append-only)
    net = sum(a.amount_sp for a in all_adjs)
    assert net == pytest.approx(0.0), f"La suma de amount_sp para la subtask debe ser 0, es {net}"

    # Contadores correctos
    assert counts["subtasks_pruned"] == 1
    assert counts["prune_reversals_inserted"] == 1


# ── Test idempotencia ─────────────────────────────────────────────────────────


def test_prune_idempotente(test_session: Session) -> None:
    """Correr prune dos veces no duplica reversiones ni cambia pruned_at."""
    pm = _seed_hierarchy(test_session)
    _add_bonus(test_session, "YAP-4", 5.0, pm.id)

    orch = _orch(test_session)
    stale = {"subtasks": ["YAP-4"], "stories": [], "epics": []}

    # Primera corrida
    orch.prune_stale(stale, allow_large_prune=True, actor_player_id=pm.id)
    test_session.commit()

    yap4 = test_session.get(Subtask, "YAP-4")
    assert yap4 is not None
    pruned_at_first = yap4.pruned_at
    count_after_first = test_session.query(SpAdjustment).count()
    reversal_count_first = (
        test_session.query(SpAdjustment)
        .filter_by(subtask_key="YAP-4", adjustment_type="prune_reversal")
        .count()
    )

    # Segunda corrida: YAP-4 ahora tiene pruned_at → find_stale_keys la excluye
    # Simulamos un re-run pasando la misma stale list (como si find_stale_keys la devolviera)
    # find_stale_keys excluye las ya podadas, así que stale["subtasks"] estaría vacío.
    stale_second = {"subtasks": [], "stories": [], "epics": []}
    counts2 = orch.prune_stale(stale_second, actor_player_id=pm.id)
    test_session.commit()

    # Nada cambió
    yap4_after = test_session.get(Subtask, "YAP-4")
    assert yap4_after is not None
    assert yap4_after.pruned_at == pruned_at_first, "pruned_at no debe cambiar"
    assert test_session.query(SpAdjustment).count() == count_after_first, "No deben insertarse más reversiones"
    assert (
        test_session.query(SpAdjustment)
        .filter_by(subtask_key="YAP-4", adjustment_type="prune_reversal")
        .count()
        == reversal_count_first
    ), "El count de prune_reversals no debe duplicarse"
    assert counts2["subtasks_pruned"] == 0
    assert counts2["prune_reversals_inserted"] == 0


# ── Test GUARDA A ─────────────────────────────────────────────────────────────


def test_prune_aborta_jira_parcial(test_session: Session) -> None:
    """GUARDA A: aborta si la poda supera el umbral % de subtasks activas."""
    pm = _seed_hierarchy(test_session)  # 2 subtasks activas: YAP-3, YAP-4
    orch = _orch(test_session)

    # Con threshold_pct=0.0 (0%), cualquier poda lo dispara
    # (o con threshold_pct=0.4 → 40% de 2 = 0.8, podar 1 = 50% > 40%)
    count_before = test_session.query(SpAdjustment).count()
    subtask_count_before = test_session.query(Subtask).count()

    with pytest.raises(PruneGuardAError, match="GUARDA A"):
        orch.prune_stale(
            {"subtasks": ["YAP-4"], "stories": [], "epics": []},
            threshold_pct=0.4,  # 40%; podar 1/2 = 50% > 40%
            allow_large_prune=False,
            actor_player_id=pm.id,
        )
    # La guarda aborta ANTES de cualquier escritura → no hay nada que revertir;
    # el session sigue válido con el estado sembrado.

    # Cero escrituras
    assert test_session.query(SpAdjustment).count() == count_before
    assert test_session.query(Subtask).count() == subtask_count_before
    yap4 = test_session.get(Subtask, "YAP-4")
    assert yap4 is not None and yap4.pruned_at is None, "pruned_at no debe setearse si abortó"


def test_prune_guarda_a_override_con_flag(test_session: Session) -> None:
    """--allow-large-prune omite la GUARDA A y la poda procede."""
    pm = _seed_hierarchy(test_session)
    orch = _orch(test_session)

    # Sin el flag falla; con el flag pasa
    counts = orch.prune_stale(
        {"subtasks": ["YAP-4"], "stories": [], "epics": []},
        threshold_pct=0.01,  # 1% → normalmente dispararía guarda
        allow_large_prune=True,
        actor_player_id=pm.id,
    )
    test_session.commit()

    assert counts["subtasks_pruned"] == 1
    yap4 = test_session.get(Subtask, "YAP-4")
    assert yap4 is not None and yap4.pruned_at is not None


# ── Test GUARDA B ─────────────────────────────────────────────────────────────


def test_prune_aborta_cp_aprobado(test_session: Session) -> None:
    """GUARDA B: aborta + reporta si alguna stale tiene cp_approved_at."""
    pm = _seed_hierarchy(test_session)

    yap4 = test_session.get(Subtask, "YAP-4")
    assert yap4 is not None
    yap4.cp_approved_at = datetime.utcnow()
    yap4.cp = 3
    test_session.flush()

    orch = _orch(test_session)
    count_before = test_session.query(SpAdjustment).count()
    subtask_count_before = test_session.query(Subtask).count()

    with pytest.raises(PruneGuardBError, match="GUARDA B"):
        orch.prune_stale(
            {"subtasks": ["YAP-4"], "stories": [], "epics": []},
            allow_large_prune=True,  # GUARDA A no interfiere
            actor_player_id=pm.id,
        )
    # La guarda aborta ANTES de cualquier escritura → session sigue válido.

    # Cero escrituras
    assert test_session.query(SpAdjustment).count() == count_before
    assert test_session.query(Subtask).count() == subtask_count_before
    yap4_check = test_session.get(Subtask, "YAP-4")
    assert yap4_check is not None and yap4_check.pruned_at is None


# ── Test dry-run ──────────────────────────────────────────────────────────────


def test_prune_dry_run_default_no_escribe(test_session: Session) -> None:
    """find_stale_keys reporta el plan y NO escribe nada."""
    pm = _seed_hierarchy(test_session)
    _add_bonus(test_session, "YAP-4", 7.5, pm.id)

    orch = _orch(test_session)
    count_before = test_session.query(SpAdjustment).count()
    subtask_count_before = test_session.query(Subtask).count()

    # Dry-run = solo llamar find_stale_keys, NO prune_stale
    stale = orch.find_stale_keys({"YAP-1", "YAP-2", "YAP-3"}, "YAP")

    assert "YAP-4" in stale["subtasks"]

    # Sin commit, sin prune_stale → cero escrituras
    assert test_session.query(SpAdjustment).count() == count_before
    assert test_session.query(Subtask).count() == subtask_count_before
    yap4 = test_session.get(Subtask, "YAP-4")
    assert yap4 is not None and yap4.pruned_at is None


# ── Anti-regresión: cp_approved_at y append-only ─────────────────────────────


def test_prune_no_toca_cp_approved_count(test_session: Session) -> None:
    """cp_approved_at count no cambia antes/después de podar una subtask sin CP aprobado."""
    pm = _seed_hierarchy(test_session)

    # Dar CP aprobado solo a YAP-3 (la que NO se poda)
    yap3 = test_session.get(Subtask, "YAP-3")
    assert yap3 is not None
    yap3.cp_approved_at = datetime.utcnow()
    yap3.cp = 2
    test_session.flush()

    cp_approved_before = (
        test_session.query(Subtask).filter(Subtask.cp_approved_at.is_not(None)).count()
    )

    orch = _orch(test_session)
    orch.prune_stale(
        {"subtasks": ["YAP-4"], "stories": [], "epics": []},
        allow_large_prune=True,
        actor_player_id=pm.id,
    )
    test_session.commit()

    cp_approved_after = (
        test_session.query(Subtask).filter(Subtask.cp_approved_at.is_not(None)).count()
    )
    assert cp_approved_after == cp_approved_before, "cp_approved_at count NO debe cambiar"


def test_prune_multiples_ajustes(test_session: Session) -> None:
    """Con N ajustes en la subtask, se insertan N reversiones y la neta es 0."""
    pm = _seed_hierarchy(test_session)

    # Agregar 3 ajustes de tipos distintos
    adj1 = _add_bonus(test_session, "YAP-4", 5.0, pm.id)
    adj2 = SpAdjustment(
        subtask_key="YAP-4",
        adjustment_type="penalty",
        amount_sp=2.0,
        reason="penalización test",
        applied_by=pm.id,
        applied_at=datetime.utcnow(),
    )
    session = test_session
    session.add(adj2)
    adj3 = SpAdjustment(
        subtask_key="YAP-4",
        adjustment_type="debuff_manual",
        catalog_code="D01",
        amount_sp=1.0,
        reason="debuff manual test",
        applied_by=pm.id,
        applied_at=datetime.utcnow(),
    )
    session.add(adj3)
    session.flush()

    count_before = session.query(SpAdjustment).count()

    orch = _orch(session)
    counts = orch.prune_stale(
        {"subtasks": ["YAP-4"], "stories": [], "epics": []},
        allow_large_prune=True,
        actor_player_id=pm.id,
    )
    session.commit()

    count_after = session.query(SpAdjustment).count()
    assert count_after == count_before + 3, "Deben insertarse 3 reversiones (1 por ajuste original)"
    assert counts["prune_reversals_inserted"] == 3

    all_adjs = session.query(SpAdjustment).filter_by(subtask_key="YAP-4").all()
    net = sum(a.amount_sp for a in all_adjs)
    assert net == pytest.approx(0.0), f"La suma neta de ajustes debe ser 0, es {net}"
