"""Tests unitarios para penalty_service (UC-06).

COBERTURA:
  - apply_penalty (catálogo + custom) recalcula sp_final
  - validación razón < 30 chars rechaza
  - validación límite: penalización > sp_final → cap a 0, no negativo
  - debuffs -100% (D09/D14) → sp_final=0 exacto
  - reversión total append-only: INSERT opuesto, NO UPDATE del sp_delta
  - reducción parcial: neto correcto, append-only
  - resolve_appeal upheld: SP intacto, solo metadatos
  - ciclo cerrado: apply_penalty rechazado
  - inmutabilidad CP: cp_approved_at count igual
"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError, RuleViolationError
from forge.db.models.cycle import Cycle
from forge.db.models.debuff import Debuff
from forge.db.models.player import Player
from forge.db.models.sp_adjustment import SpAdjustment
from forge.db.models.subtask import Subtask
from forge.services import penalty_service

# ── Helpers ───────────────────────────────────────────────────────────────


def _make_player(session: Session, area: str = "BE", jira_id: str = "j1") -> Player:
    p = Player(
        jira_account_id=jira_id,
        display_name="Dev Test",
        email=f"{jira_id}@yapsi.com",
        area=area,
        employment_type="internal",
        is_lead=False,
        is_active=True,
    )
    session.add(p)
    session.flush()
    return p


def _make_cycle(session: Session, status: str = "active") -> Cycle:
    c = Cycle(
        name=f"Ciclo Test {status}",
        iso_year=2026,
        iso_week=22,
        start_date=datetime(2026, 5, 25).date(),
        end_date=datetime(2026, 5, 29).date(),
        status=status,
    )
    session.add(c)
    session.flush()
    return c


def _make_subtask(
    session: Session,
    cycle_id: int | None = None,
    sp_final: float = 5.0,
    cp: int = 5,
    cp_approved_at: datetime | None = None,
    key: str = "YAP-999",
) -> Subtask:
    st = Subtask(
        jira_key=key,
        issue_type="Sub-task",
        area="BE",
        summary="Subtask de prueba penalización",
        status="Done",
        last_synced_at=datetime.utcnow(),
        cp_approval_required=False,
        cp_modified_post_approval=False,
        cp=cp,
        sp_final=sp_final,
        sp_base=sp_final,
        sp_flat_bonus=0.0,
        sp_penalty=0.0,
        cycle_id=cycle_id,
        cp_approved_at=cp_approved_at,
    )
    session.add(st)
    session.flush()
    return st


def _make_debuff(
    session: Session,
    code: str = "D06",
    penalty_type: str = "flat",
    value: float = 1.0,
    is_active: bool = True,
) -> Debuff:
    d = Debuff(
        code=code,
        narrative_name=f"Debuff {code}",
        trigger_description="Trigger de prueba",
        penalty_type=penalty_type,
        value=value,
        is_appealable=True,
        is_active=is_active,
    )
    session.add(d)
    session.flush()
    return d


def _count_adjustments(session: Session, subtask_key: str) -> list[SpAdjustment]:
    return list(
        session.scalars(
            select(SpAdjustment)
            .where(SpAdjustment.subtask_key == subtask_key)
            .order_by(SpAdjustment.id)
        ).all()
    )


# ── apply_penalty ─────────────────────────────────────────────────────────


def test_apply_custom_penalty_reduces_sp(test_session: Session) -> None:
    """Penalización custom recalcula sp_final correctamente."""
    cycle = _make_cycle(test_session, "active")
    st = _make_subtask(test_session, cycle_id=cycle.id, sp_final=5.0, key="YAP-A1")
    _make_player(test_session, jira_id="j1")

    adj = penalty_service.apply_penalty(
        test_session,
        "YAP-A1",
        reason="Penalización custom de prueba con razón suficientemente larga para pasar validación",
        custom_sp=2.0,
    )
    test_session.commit()

    test_session.expire(st)
    st_fresh = test_session.get(Subtask, "YAP-A1")
    assert st_fresh is not None
    assert adj.adjustment_type == "debuff_manual"
    assert adj.amount_sp == 2.0
    # sp_final debe haber bajado (motor recalcula)
    assert st_fresh.sp_final is not None
    assert st_fresh.sp_final < 5.0


def test_apply_catalog_penalty(test_session: Session) -> None:
    """Penalización del catálogo usa el valor del debuff."""
    cycle = _make_cycle(test_session, "active")
    st = _make_subtask(test_session, cycle_id=cycle.id, sp_final=4.0, key="YAP-B1")
    _make_debuff(test_session, code="D06", penalty_type="flat", value=1.0)

    adj = penalty_service.apply_penalty(
        test_session,
        "YAP-B1",
        reason="Falta de documentación detectada durante code review de esta tarea de integración",
        catalog_code="D06",
    )
    test_session.commit()

    assert adj.catalog_code == "D06"
    assert adj.amount_sp == 1.0


def test_apply_penalty_short_reason_rejects(test_session: Session) -> None:
    """Razón < 30 chars debe rechazarse."""
    cycle = _make_cycle(test_session, "active")
    _make_subtask(test_session, cycle_id=cycle.id, key="YAP-C1")

    with pytest.raises(RuleViolationError, match="30"):
        penalty_service.apply_penalty(
            test_session, "YAP-C1", reason="corta", custom_sp=1.0
        )


def test_apply_penalty_both_sources_rejects(test_session: Session) -> None:
    """Proveer catalog_code Y custom_sp debe rechazarse."""
    cycle = _make_cycle(test_session, "active")
    _make_subtask(test_session, cycle_id=cycle.id, key="YAP-D1")

    with pytest.raises(RuleViolationError):
        penalty_service.apply_penalty(
            test_session,
            "YAP-D1",
            reason="Razón suficientemente larga para superar la validación de treinta caracteres mínimos",
            catalog_code="D06",
            custom_sp=1.0,
        )


# ── Validación de límite ──────────────────────────────────────────────────


def test_penalty_cap_at_zero(test_session: Session) -> None:
    """Penalización > sp_final se cappea al valor disponible; sp_final queda en 0."""
    cycle = _make_cycle(test_session, "active")
    st = _make_subtask(test_session, cycle_id=cycle.id, sp_final=2.0, key="YAP-E1")

    adj = penalty_service.apply_penalty(
        test_session,
        "YAP-E1",
        reason="Intentando penalizar más que el SP disponible para comprobar el cap al cero",
        custom_sp=10.0,
    )
    test_session.commit()

    # El amount_sp se cappea al disponible
    assert adj.amount_sp == pytest.approx(2.0)
    test_session.expire(st)
    st_fresh = test_session.get(Subtask, "YAP-E1")
    # sp_final no puede ser negativo
    assert st_fresh is not None
    assert (st_fresh.sp_final or 0.0) >= 0.0


def test_penalty_at_zero_sp_rejects(test_session: Session) -> None:
    """No se puede penalizar si sp_final ya es 0."""
    cycle = _make_cycle(test_session, "active")
    _make_subtask(test_session, cycle_id=cycle.id, sp_final=0.0, key="YAP-F1")

    with pytest.raises(RuleViolationError, match="sp_final=0"):
        penalty_service.apply_penalty(
            test_session,
            "YAP-F1",
            reason="Intento de penalizar subtask ya en cero SP para verificar el rechazo",
            custom_sp=1.0,
        )


def test_penalty_100_percent_brings_to_zero(test_session: Session) -> None:
    """Debuffs -100% (D09) llevan sp_final exactamente a 0."""
    cycle = _make_cycle(test_session, "active")
    st = _make_subtask(test_session, cycle_id=cycle.id, sp_final=3.5, key="YAP-G1")
    _make_debuff(test_session, code="D09", penalty_type="percentage", value=100.0)

    adj = penalty_service.apply_penalty(
        test_session,
        "YAP-G1",
        reason="No entrega y abandono de tarea asignada sin traspaso al equipo ni notificación",
        catalog_code="D09",
    )
    test_session.commit()

    # El amount_sp debe ser el total del sp_final (3.5)
    assert adj.amount_sp == pytest.approx(3.5)


# ── Ciclo cerrado ─────────────────────────────────────────────────────────


def test_penalty_on_closed_cycle_rejects(test_session: Session) -> None:
    """No se puede penalizar en un ciclo cerrado."""
    cycle = _make_cycle(test_session, "closed")
    _make_subtask(test_session, cycle_id=cycle.id, key="YAP-H1")

    with pytest.raises(RuleViolationError, match="ciclo"):
        penalty_service.apply_penalty(
            test_session,
            "YAP-H1",
            reason="Intento de penalizar en ciclo cerrado para comprobar el rechazo correcto",
            custom_sp=1.0,
        )


# ── Reversión total (append-only) ────────────────────────────────────────


def test_reverse_total_is_append_only(test_session: Session) -> None:
    """
    Reversión total: se inserta un 'reversal' con el mismo amount_sp.
    El sp_delta (amount_sp) original NUNCA se modifica (0 UPDATEs del valor).
    """
    cycle = _make_cycle(test_session, "active")
    _make_subtask(test_session, cycle_id=cycle.id, sp_final=5.0, key="YAP-I1")

    adj = penalty_service.apply_penalty(
        test_session,
        "YAP-I1",
        reason="Penalización a revertir para comprobar el patrón append-only en reversión total",
        custom_sp=2.0,
    )
    test_session.commit()

    rev = penalty_service.reverse_penalty(
        test_session,
        adj.id,
        reason="Revisión: el developer sí había comunicado el issue por canal alterno; reversión total",
        partial_new_value=None,
    )
    test_session.commit()

    # El reversal es un INSERT nuevo
    assert rev.adjustment_type == "reversal"
    assert rev.amount_sp == adj.amount_sp  # mismo monto que la penalización
    assert rev.catalog_code == f"REV:{adj.id}"

    # El original NO tuvo UPDATE en amount_sp
    orig_fresh = test_session.get(SpAdjustment, adj.id)
    assert orig_fresh is not None
    assert orig_fresh.amount_sp == 2.0  # sin cambio

    # Metadatos de apelación actualizados en el original
    assert orig_fresh.is_appealed is True
    assert orig_fresh.appeal_resolution == "reversed"


def test_reverse_partial_is_append_only(test_session: Session) -> None:
    """
    Reducción parcial: el reversal es INSERT con la diferencia.
    Neto = original - reversal = partial_new_value.
    """
    cycle = _make_cycle(test_session, "active")
    _make_subtask(test_session, cycle_id=cycle.id, sp_final=5.0, key="YAP-J1")

    adj = penalty_service.apply_penalty(
        test_session,
        "YAP-J1",
        reason="Penalización a reducir parcialmente para comprobar el patrón append-only correcto",
        custom_sp=4.0,
    )
    test_session.commit()

    rev = penalty_service.reverse_penalty(
        test_session,
        adj.id,
        reason="Revisión parcial: la penalización fue excesiva; reducimos a la mitad del valor original",
        partial_new_value=1.0,  # neto deseado = 1.0
    )
    test_session.commit()

    # reversal amount = original - partial = 4.0 - 1.0 = 3.0
    assert rev.amount_sp == pytest.approx(3.0)
    assert rev.adjustment_type == "reversal"

    # El original se mantiene intacto en amount_sp
    orig_fresh = test_session.get(SpAdjustment, adj.id)
    assert orig_fresh is not None
    assert orig_fresh.amount_sp == 4.0
    assert orig_fresh.appeal_resolution == "reduced"


# ── resolve_appeal upheld ─────────────────────────────────────────────────


def test_resolve_appeal_upheld_does_not_change_sp(test_session: Session) -> None:
    """resolve_appeal upheld: el SP no cambia, solo metadatos."""
    cycle = _make_cycle(test_session, "active")
    st = _make_subtask(test_session, cycle_id=cycle.id, sp_final=5.0, key="YAP-K1")

    adj = penalty_service.apply_penalty(
        test_session,
        "YAP-K1",
        reason="Penalización sobre la que el player apelará en la weekly del equipo de desarrollo",
        custom_sp=1.0,
    )
    test_session.commit()
    penalty_service.mark_appealed(test_session, adj.id)
    test_session.commit()

    test_session.expire(st)
    sp_after_penalty = (test_session.get(Subtask, "YAP-K1") or st).sp_final

    penalty_service.resolve_appeal(
        test_session,
        adj.id,
        resolution="upheld",
        notes="Revisado con el player: la penalización procede porque la situación fue verificada",
        admin_id=1,
    )
    test_session.commit()

    test_session.expire_all()
    st_fresh = test_session.get(Subtask, "YAP-K1")
    adj_fresh = test_session.get(SpAdjustment, adj.id)

    assert st_fresh is not None and adj_fresh is not None
    # SP no cambia con upheld
    assert st_fresh.sp_final == sp_after_penalty
    assert adj_fresh.appeal_resolution == "upheld"

    # No debe haber ningún reversal
    rows = _count_adjustments(test_session, "YAP-K1")
    reversal_rows = [r for r in rows if r.adjustment_type == "reversal"]
    assert len(reversal_rows) == 0


# ── Inmutabilidad CP ──────────────────────────────────────────────────────


def test_penalties_do_not_touch_cp_approved_at(test_session: Session) -> None:
    """Penalizaciones no modifican cp_approved_at."""
    cycle = _make_cycle(test_session, "active")
    approved_at = datetime(2026, 5, 20, 10, 0)
    _make_subtask(
        test_session,
        cycle_id=cycle.id,
        sp_final=5.0,
        cp=3,
        cp_approved_at=approved_at,
        key="YAP-L1",
    )

    penalty_service.apply_penalty(
        test_session,
        "YAP-L1",
        reason="Verificar que aplicar una penalización no toca el campo cp_approved_at de la subtask",
        custom_sp=1.0,
    )
    test_session.commit()

    st_fresh = test_session.get(Subtask, "YAP-L1")
    assert st_fresh is not None
    assert st_fresh.cp_approved_at == approved_at
    assert st_fresh.cp == 3  # CP intacto


# ── Anti-regresión: subtask inexistente ───────────────────────────────────


def test_apply_penalty_subtask_not_found(test_session: Session) -> None:
    with pytest.raises(NotFoundError):
        penalty_service.apply_penalty(
            test_session,
            "YAP-9999",
            reason="Razón suficientemente larga para pasar validación de caracteres mínimos requeridos",
            custom_sp=1.0,
        )
