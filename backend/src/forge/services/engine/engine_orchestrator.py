"""
Orquestador del motor de cálculo CP/SP (JPDS v2.0).

Flujo completo de recalculo para una subtask:
  1. Cargar subtask + sprint desde DB
  2. Recomputar métricas de tiempo desde raw_changelog
  3. Calcular multiplicadores (m_calidad, m_eficiencia, ...)
  4. Detectar debuffs automáticos (D01, D03, D04, D10, D11, D13)
  5. Persistir debuffs nuevos como SpAdjustments (idempotente)
  6. Sumar todos los SpAdjustments existentes para la subtask
  7. Calcular sp_final con la fórmula completa
  8. Escribir todos los campos calculados en la subtask
  9. Marcar sp_last_calculated_at + engine_version_id

Idempotencia:
  Correr recalculate_subtask dos veces produce exactamente el mismo resultado.
  - Los debuffs se crean una sola vez: se comprueba si ya existe un
    SpAdjustment con (subtask_key, catalog_code) antes de crear uno nuevo.
  - Los campos numéricos en Subtask se sobreescriben; no se acumulan.

Inmutabilidad CP:
  Si subtask.cp_approved_at IS NOT NULL, el orquestador NO modifica cp ni
  complexity_size. El resto del cálculo (multiplicadores, SP) sí se actualiza.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError
from forge.db.models.cycle import Cycle
from forge.db.models.engine_version import EngineVersion
from forge.db.models.sp_adjustment import SpAdjustment
from forge.db.models.subtask import Subtask
from forge.services.engine.debuff_detector import DetectedDebuff, detect_all
from forge.services.engine.sp_calculator import SpComponents, calculate_sp, needs_recalculation
from forge.services.engine.time_calculator import recompute_time_metrics

logger = logging.getLogger(__name__)


# ── Recalculo individual ──────────────────────────────────────────────────


def recalculate_subtask(
    session: Session,
    subtask_key: str,
    system_player_id: int,
    *,
    force: bool = False,
) -> SpComponents:
    """
    Recalcular SP completo para una subtask.

    Args:
        session: Sesión SQLAlchemy activa.
        subtask_key: Jira key de la subtask (p.ej. "YAP-123").
        system_player_id: ID del player que actúa como "sistema" para los
                          SpAdjustments auto-creados (normalmente PM/lead).
        force: Si True, recalcula aunque la versión del engine no haya cambiado.

    Returns:
        SpComponents con todos los valores calculados.

    Raises:
        NotFoundError: Si la subtask no existe en DB.
    """
    # 1. Cargar subtask
    subtask = session.get(Subtask, subtask_key)
    if subtask is None:
        raise NotFoundError(f"Subtask '{subtask_key}' no encontrada.")

    # 2. Cargar engine version activa
    engine_version = _get_active_engine_version(session)

    # 3. Verificar si se necesita recálculo
    if not force and engine_version and not needs_recalculation(subtask, engine_version.id):
        logger.debug(f"Subtask {subtask_key}: ya calculada con versión actual, omitiendo.")
        return _build_components_from_subtask(subtask)

    # 4. Cargar ciclo asociado (usado por D13)
    cycle: Cycle | None = None
    if subtask.cycle_id:
        cycle = session.get(Cycle, subtask.cycle_id)

    # 5. Recomputar métricas de tiempo desde raw_changelog
    time_metrics = recompute_time_metrics(subtask)
    _apply_time_metrics(subtask, time_metrics)

    # 6. Detectar debuffs automáticos
    debuffs = detect_all(subtask, cycle=cycle)

    # 7. Persistir debuffs nuevos (idempotente), vinculados al ciclo
    _persist_debuffs(session, subtask_key, debuffs, system_player_id, cycle_id=subtask.cycle_id)

    # 8. Sumar todos los SpAdjustments vigentes
    sp_flat_bonus, sp_penalty = _sum_adjustments(session, subtask_key)

    # 9. Calcular SP completo
    components = calculate_sp(
        subtask,
        sp_flat_bonus=sp_flat_bonus,
        sp_penalty=sp_penalty,
    )

    # 10. Escribir resultados en la subtask
    _apply_sp_components(subtask, components)
    if engine_version:
        subtask.engine_version_id = engine_version.id
    subtask.sp_last_calculated_at = datetime.now(UTC).replace(tzinfo=None)

    session.flush()  # La transacción la gestiona el llamador

    logger.info(
        f"Subtask {subtask_key}: recalculada. "
        f"CP={subtask.cp} SP={components.sp_final:.2f} "
        f"(base={components.sp_base:.2f}, bonus={sp_flat_bonus:.2f}, "
        f"penalty={sp_penalty:.2f})"
    )

    return components


# ── Recalculo de ciclo completo ───────────────────────────────────────────


def recalculate_cycle(
    session: Session,
    cycle_id: int,
    system_player_id: int,
    *,
    force: bool = False,
) -> dict[str, int | float]:
    """
    Recalcular SP para todas las subtasks de un ciclo.

    Commits SOLO al finalizar todas las subtasks (transacción única).
    Si una subtask falla, se registra el error pero se continúa con las demás.

    Args:
        session: Sesión SQLAlchemy activa (NO hace commit; lo hace el llamador).
        cycle_id: ID del ciclo a recalcular.
        system_player_id: Player que actúa como sistema para SpAdjustments.
        force: Si True, recalcula todas aunque la versión no haya cambiado.

    Returns:
        Dict con estadísticas: processed, skipped, errors.

    Raises:
        NotFoundError: Si el ciclo no existe.
    """
    cycle = session.get(Cycle, cycle_id)
    if cycle is None:
        raise NotFoundError(f"Cycle id={cycle_id} no encontrado.")

    subtask_keys_result = session.execute(
        select(Subtask.jira_key).where(Subtask.cycle_id == cycle_id)
    )
    keys = [row[0] for row in subtask_keys_result]

    stats: dict[str, int | float] = {
        "cycle_id": cycle_id,
        "total": len(keys),
        "processed": 0,
        "skipped": 0,
        "errors": 0,
        "sp_total": 0.0,
    }

    engine_version = _get_active_engine_version(session)

    for key in keys:
        try:
            subtask = session.get(Subtask, key)
            if subtask is None:
                continue

            if not force and engine_version and not needs_recalculation(
                subtask, engine_version.id
            ):
                stats["skipped"] = int(stats["skipped"]) + 1
                continue

            components = recalculate_subtask(
                session, key, system_player_id, force=force
            )
            stats["processed"] = int(stats["processed"]) + 1
            stats["sp_total"] = float(stats["sp_total"]) + components.sp_final

        except Exception as exc:
            stats["errors"] = int(stats["errors"]) + 1
            logger.error(f"Error recalculando {key}: {exc}")

    logger.info(
        f"recalculate_cycle id={cycle_id}: "
        f"{stats['processed']} procesadas, {stats['skipped']} omitidas, "
        f"{stats['errors']} errores. SP total={stats['sp_total']:.2f}"
    )
    return stats


def recalculate_sprint(
    session: Session,
    sprint_id: int,
    system_player_id: int,
    *,
    force: bool = False,
) -> dict[str, int | float]:
    """DEPRECATED (WP-01b): usar recalculate_cycle en su lugar.

    Alias que delega a recalculate_cycle usando cycle_id = sprint_id.
    Se mantiene para compatibilidad con CLI legado.
    """
    logger.warning(
        "recalculate_sprint is deprecated; use recalculate_cycle (cycle_id) instead."
    )
    return recalculate_cycle(session, sprint_id, system_player_id, force=force)


# ── Helpers privados ──────────────────────────────────────────────────────


def _get_active_engine_version(session: Session) -> EngineVersion | None:
    """Obtener la versión activa del engine. None si no está configurada."""
    stmt = select(EngineVersion).where(EngineVersion.is_active.is_(True)).limit(1)
    return session.scalars(stmt).first()


def _apply_time_metrics(subtask: Subtask, metrics: dict) -> None:
    """Escribir métricas de tiempo calculadas en el modelo Subtask."""
    # done_at solo se actualiza si aún no está definido (evita sobrescribir
    # valores correctos en casos donde la API de Jira lo reporta explícitamente)
    if metrics.get("done_at") and subtask.done_at is None:
        subtask.done_at = metrics["done_at"]

    for field in (
        "lt_biz_hours",
        "ct_biz_hours",
        "adj_ct_biz_hours",
        "dev_resp_biz_hours",
        "qa_biz_hours",
        "blocked_biz_hours",
        "waiting_biz_hours",
        "review_biz_hours",
    ):
        value = metrics.get(field)
        if value is not None:
            setattr(subtask, field, value)


def _apply_sp_components(subtask: Subtask, components: SpComponents) -> None:
    """Escribir todos los campos SP calculados en el modelo Subtask."""
    for field, value in components.as_dict().items():
        setattr(subtask, field, value)


def _persist_debuffs(
    session: Session,
    subtask_key: str,
    debuffs: list[DetectedDebuff],
    system_player_id: int,
    cycle_id: int | None = None,
) -> int:
    """
    Persistir debuffs detectados como SpAdjustments (idempotente).

    Un debuff se crea SOLO si no existe ya un SpAdjustment con el mismo
    (subtask_key, catalog_code). Esto garantiza idempotencia.

    Returns:
        Número de nuevos SpAdjustments creados.
    """
    if not debuffs:
        return 0

    # Leer catalog_codes ya existentes para esta subtask
    existing_stmt = select(SpAdjustment.catalog_code).where(
        SpAdjustment.subtask_key == subtask_key,
        SpAdjustment.adjustment_type == "penalty",
    )
    existing_codes = {row[0] for row in session.execute(existing_stmt)}

    created = 0
    for debuff in debuffs:
        if debuff.catalog_code in existing_codes:
            logger.debug(
                f"Debuff {debuff.catalog_code} ya existe para {subtask_key}, omitiendo."
            )
            continue

        adjustment = SpAdjustment(
            subtask_key=subtask_key,
            adjustment_type="penalty",
            catalog_code=debuff.catalog_code,
            amount_sp=debuff.amount_sp,
            reason=debuff.reason,
            applied_by=system_player_id,
            applied_at=datetime.utcnow(),
            cycle_id=cycle_id,
        )
        session.add(adjustment)
        existing_codes.add(debuff.catalog_code)  # Evitar duplicados en el mismo batch
        created += 1

    if created:
        session.flush()  # Hacer visible para la suma que sigue

    return created


def _sum_adjustments(session: Session, subtask_key: str) -> tuple[float, float]:
    """
    Sumar todos los SpAdjustments de la subtask.

    Returns:
        (total_bonus, total_penalty) — ambos valores positivos.
    """
    rows = session.execute(
        select(SpAdjustment.adjustment_type, SpAdjustment.amount_sp).where(
            SpAdjustment.subtask_key == subtask_key
        )
    ).fetchall()

    total_bonus = sum(r.amount_sp for r in rows if r.adjustment_type == "bonus")
    total_penalty = sum(r.amount_sp for r in rows if r.adjustment_type == "penalty")
    return total_bonus, total_penalty


def _build_components_from_subtask(subtask: Subtask) -> SpComponents:
    """Construir SpComponents desde los campos ya guardados en la subtask."""
    return SpComponents(
        m_calidad=subtask.m_calidad or 1.0,
        m_eficiencia=subtask.m_eficiencia or 1.0,
        m_dificultad=subtask.m_dificultad or 1.0,
        m_lider=subtask.m_lider or 1.0,
        m_cooperacion=subtask.m_cooperacion or 1.0,
        sp_base=subtask.sp_base or 0.0,
        sp_flat_bonus=subtask.sp_flat_bonus or 0.0,
        sp_penalty=subtask.sp_penalty or 0.0,
        sp_final=subtask.sp_final or 0.0,
    )
