"""CycleService — UC-05: ritual de cierre de ciclo semanal + MVP."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from forge.core.config import get_settings
from forge.core.exceptions import NotFoundError, RuleViolationError
from forge.core.time_utils import business_hours
from forge.db.models.achievement import Achievement
from forge.db.models.achievement_unlock import AchievementUnlock
from forge.db.models.audit_log import AuditLog
from forge.db.models.cycle import Cycle
from forge.db.models.leaderboard_snapshot import LeaderboardSnapshot
from forge.db.models.player import Player
from forge.db.models.sp_adjustment import SpAdjustment
from forge.db.models.subtask import Subtask
from forge.repositories.cycle import CycleRepository
from forge.services.engine.engine_orchestrator import recalculate_subtask

logger = logging.getLogger(__name__)

_MVP_BONUS_SP = 5.0
_MVP_BUFF_CODE = "B17"
_MVP_ACH_CODE = "ACH04"
_MVP_REASON_MIN_LEN = 20
_EDIT_MVP_WINDOW_BIZ_HOURS = 24.0

# ── Reconciliación de ajustes no-issue (WP-23) ──────────────────────────────
# Ajustes player-level (subtask_key IS NULL) que NO están en sp_final. Su signo
# define cómo contribuyen al SP del ciclo del player.
_ADJ_SUBTRACT_TYPES = {"penalty", "debuff_manual", "mvp_reversal"}
_ADJ_LABELS = {
    "mvp_bonus": "Bono MVP",
    "mvp_reversal": "Reversión MVP",
    "bonus": "Bono",
    "reversal": "Reversión",
    "penalty": "Penalización",
    "debuff_manual": "Penalización",
}


def _signed_adjustment(adj_type: str, amount: float) -> float:
    """Contribución firmada de un ajuste al SP del player (negativa si penaliza)."""
    return -amount if adj_type in _ADJ_SUBTRACT_TYPES else amount


def _adjustment_label(adj_type: str, catalog_code: str | None) -> str:
    """Etiqueta legible de una línea de ajuste no-issue (p.ej. 'Penalización D07')."""
    base = _ADJ_LABELS.get(adj_type, adj_type)
    if adj_type in ("penalty", "debuff_manual") and catalog_code and catalog_code != "CUSTOM":
        return f"{base} {catalog_code}"
    return base


class CycleService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = CycleRepository(session)

    # ── Candidatos MVP ────────────────────────────────────────────────────

    def get_mvp_candidates(self, cycle_id: int) -> list[dict[str, Any]]:
        """
        Sugiere 3-5 players candidatos a MVP del ciclo por métricas objetivas.

        Métricas usadas hoy (objetivas disponibles):
          1. Mayor SP del ciclo
          2. Mayor CP completado
          3. Más subtasks Done

        TODO: agregar métricas de mentorías (B13) y desbloqueos (B16) cuando estén construidas.
        """
        cycle = self._get_cycle(cycle_id)
        if cycle.status not in ("active", "planned"):
            raise RuleViolationError(
                f"Candidatos MVP solo disponibles para ciclos active/planned, "
                f"no '{cycle.status}'",
                details={"cycle_id": cycle_id, "status": cycle.status},
            )

        # Subtasks Done del ciclo con assignee
        rows = self._session.execute(
            select(
                Subtask.assignee_player_id,
                Subtask.sp_final,
                Subtask.cp,
            ).where(
                Subtask.cycle_id == cycle_id,
                Subtask.status == "Done",
                Subtask.assignee_player_id.isnot(None),
            )
        ).fetchall()

        # Agrupar por player
        stats: dict[int, dict[str, Any]] = {}
        for player_id, sp_final, cp in rows:
            if player_id not in stats:
                stats[player_id] = {
                    "player_id": player_id,
                    "sp_total": 0.0,
                    "cp_total": 0,
                    "subtasks_done": 0,
                }
            stats[player_id]["sp_total"] += sp_final or 0.0
            stats[player_id]["cp_total"] += cp or 0
            stats[player_id]["subtasks_done"] += 1

        if not stats:
            return []

        # Ordenar por SP desc, luego CP
        ordered = sorted(
            stats.values(),
            key=lambda x: (x["sp_total"], x["cp_total"]),
            reverse=True,
        )[:5]

        # Enriquecer con nombre del player y m_calidad promedio
        results = []
        for s in ordered:
            player = self._session.get(Player, s["player_id"])
            if player is None or not player.is_active:
                continue

            m_calidad_rows = self._session.execute(
                select(Subtask.m_calidad).where(
                    Subtask.cycle_id == cycle_id,
                    Subtask.assignee_player_id == s["player_id"],
                    Subtask.status == "Done",
                    Subtask.m_calidad.isnot(None),
                )
            ).fetchall()
            avg_calidad = (
                sum(r[0] for r in m_calidad_rows) / len(m_calidad_rows)
                if m_calidad_rows
                else None
            )

            results.append(
                {
                    "player_id": s["player_id"],
                    "display_name": player.display_name,
                    "area": player.area,
                    "sp_total": round(s["sp_total"], 2),
                    "cp_total": s["cp_total"],
                    "subtasks_done": s["subtasks_done"],
                    "avg_m_calidad": round(avg_calidad, 3) if avg_calidad else None,
                    "metric_highlight": f"{s['sp_total']:.1f} SP en {s['subtasks_done']} subtasks",
                }
            )

        return results

    # ── Resumen de cierre ─────────────────────────────────────────────────

    def get_close_summary(self, cycle_id: int) -> dict[str, Any]:
        """
        Genera resumen pre-cierre con KPIs y validaciones bloqueantes/warnings.

        Validaciones BLOQUEANTES (impiden cierre):
          - Subtasks Done sin sp_final calculado.

        Validaciones WARNING (no bloquean):
          - CP propuestos (cp_approval_required=1, cp_approved_at=None) sin aprobar.
        """
        cycle = self._get_cycle(cycle_id)

        # KPIs del ciclo — se trae jira_key + summary para el drill-down (WP-23)
        done_rows = self._session.execute(
            select(
                Subtask.jira_key,
                Subtask.summary,
                Subtask.assignee_player_id,
                Subtask.cp,
                Subtask.sp_final,
                Subtask.qa_attempts,
            ).where(Subtask.cycle_id == cycle_id, Subtask.status == "Done")
        ).fetchall()

        cp_done = sum(r.cp or 0 for r in done_rows)
        sp_generated = sum(r.sp_final or 0.0 for r in done_rows)
        subtasks_done = len(done_rows)
        bugs_derived = sum(r.qa_attempts or 0 for r in done_rows)  # proxy: QA re-attempts

        # ── Drill-down por player: issues + ajustes no-issue (WP-23) ──────────
        # Issues Done por player (cada uno aporta su sp_final, que ya absorbe
        # penalties/bonos ligados a subtask).
        issues_by_player: dict[int, list[dict[str, Any]]] = {}
        for r in done_rows:
            if r.assignee_player_id is None:
                continue
            issues_by_player.setdefault(r.assignee_player_id, []).append(
                {
                    "jira_key": r.jira_key,
                    "title": r.summary,
                    "cp": r.cp,
                    "sp_final": r.sp_final,
                }
            )

        # Ajustes player-level del ciclo (subtask_key IS NULL): NO están en sp_final.
        adj_rows = self._session.execute(
            select(
                SpAdjustment.player_id,
                SpAdjustment.adjustment_type,
                SpAdjustment.catalog_code,
                SpAdjustment.amount_sp,
            ).where(
                SpAdjustment.cycle_id == cycle_id,
                SpAdjustment.subtask_key.is_(None),
                SpAdjustment.player_id.isnot(None),
            )
        ).fetchall()

        adjustments_by_player: dict[int, list[dict[str, Any]]] = {}
        for pid, atype, code, amount in adj_rows:
            adjustments_by_player.setdefault(pid, []).append(
                {
                    "label": _adjustment_label(atype, code),
                    "amount_sp": round(_signed_adjustment(atype, amount or 0.0), 2),
                }
            )

        # SP total del ciclo por player = Σ sp_final(issues) + Σ ajustes firmados.
        # La fila DEBE cuadrar con su desglose (reconciliación obligatoria WP-23).
        player_sp: dict[int, float] = {}
        for pid in set(issues_by_player) | set(adjustments_by_player):
            issue_sp = sum(i["sp_final"] or 0.0 for i in issues_by_player.get(pid, []))
            adj_sp = sum(a["amount_sp"] for a in adjustments_by_player.get(pid, []))
            player_sp[pid] = round(issue_sp + adj_sp, 2)

        top_players = []
        for pid, sp in sorted(player_sp.items(), key=lambda x: x[1], reverse=True)[:5]:
            p = self._session.get(Player, pid)
            top_players.append(
                {
                    "player_id": pid,
                    "display_name": p.display_name if p else f"Player {pid}",
                    "area": p.area if p else "?",
                    "sp": sp,
                    "por_issue": issues_by_player.get(pid, []),
                    "ajustes_no_issue": adjustments_by_player.get(pid, []),
                }
            )

        # Validaciones bloqueantes — estructuradas con claves de issue (WP-23)
        done_no_sp_keys = [r.jira_key for r in done_rows if r.sp_final is None]
        blocking_errors: list[dict[str, Any]] = []
        if done_no_sp_keys:
            blocking_errors.append(
                {
                    "type": "done_without_sp_final",
                    "message": (
                        f"{len(done_no_sp_keys)} subtasks Done sin sp_final calculado. "
                        "Recalcula el SP del ciclo antes de cerrar."
                    ),
                    "issue_keys": done_no_sp_keys,
                }
            )

        # Validaciones warning
        from sqlalchemy import func

        pending_cp_count: int = self._session.scalar(
            select(func.count()).select_from(Subtask).where(
                Subtask.cycle_id == cycle_id,
                Subtask.cp_approval_required.is_(True),
                Subtask.cp_approved_at.is_(None),
            )
        ) or 0

        warnings: list[str] = []
        if pending_cp_count:
            warnings.append(
                f"{pending_cp_count} subtasks con CP propuesto sin aprobar. "
                "El cierre procederá pero su SP puede estar incompleto."
            )

        return {
            "cycle_id": cycle_id,
            "cycle_name": cycle.name,
            "cycle_status": cycle.status,
            "kpis": {
                "cp_done": cp_done,
                "sp_generated": round(sp_generated, 2),
                "subtasks_done": subtasks_done,
                "bugs_derived": bugs_derived,
            },
            "top_players": top_players,
            "can_close": len(blocking_errors) == 0,
            "blocking_errors": blocking_errors,
            "warnings": warnings,
            "jira_base_url": (get_settings().jira_instance_url or "").rstrip("/") or None,
        }

    # ── Recalc contextual del cierre (WP-23) ─────────────────────────────

    def recalc_cycle_sp(
        self, cycle_id: int, system_player_id: int
    ) -> dict[str, Any]:
        """
        Recalcula sp_final de las subtasks Done del ciclo sin sp_final, vía el motor.

        Frontera dura:
          - Acotado al ciclo (NO --all-cycles) y solo a las Done con sp_final IS NULL.
          - Invoca recalculate_subtask (la función atómica del motor que envuelve
            'make recalc'); NO usa subprocess/shell.
          - Escribe sp_final (y sus componentes derivados); NO modifica el ledger
            sp_adjustments salvo lo que el propio motor materialice de forma
            idempotente, ni cp/complexity_size (inmutables).
          - Idempotente: re-correr no selecciona nada (sp_final ya no es NULL).
          - Re-ejecuta la validación bloqueante y devuelve el estado resultante.

        Returns:
            dict con cycle_id, recalculated (n), message y summary (re-validado).
        """
        self._get_cycle(cycle_id)  # valida existencia

        keys = [
            row[0]
            for row in self._session.execute(
                select(Subtask.jira_key).where(
                    Subtask.cycle_id == cycle_id,
                    Subtask.status == "Done",
                    Subtask.sp_final.is_(None),
                )
            )
        ]

        for key in keys:
            recalculate_subtask(self._session, key, system_player_id, force=False)

        self._audit(
            "cycle_recalc",
            "cycle",
            str(cycle_id),
            system_player_id,
            {"recalculated": len(keys), "issue_keys": keys},
        )
        self._session.flush()

        summary = self.get_close_summary(cycle_id)
        return {
            "cycle_id": cycle_id,
            "recalculated": len(keys),
            "message": (
                f"Recalculadas {len(keys)} subtasks Done sin sp_final."
                if keys
                else "No había subtasks Done sin sp_final; nada que recalcular."
            ),
            "summary": summary,
        }

    # ── Cierre de ciclo ───────────────────────────────────────────────────

    def close_cycle(
        self,
        cycle_id: int,
        mvp_player_id: int,
        mvp_reason: str,
        closed_by: int,
    ) -> Cycle:
        """
        Ritual de cierre en transacción única.

        Pasos:
          1. Validaciones pre-cierre
          2. closing_snapshot_json inmutable
          3. SpAdjustment MVP +5 SP (B17)
          4. AchievementUnlock ACH04 (primera vez)
          5. LeaderboardSnapshot period_type='weekly'
          6. LeaderboardSnapshot period_type='rolling_4'
          7. Hook forecast stub
          8. cycle.status='closed'
          9. Activar siguiente ciclo 'planned'
          10. AuditLog
        """
        cycle = self._get_cycle(cycle_id)

        # Validaciones
        if cycle.status != "active":
            raise RuleViolationError(
                f"Solo se puede cerrar un ciclo 'active'. Estado actual: '{cycle.status}'",
                details={"cycle_id": cycle_id, "status": cycle.status},
            )
        if len(mvp_reason.strip()) < _MVP_REASON_MIN_LEN:
            raise RuleViolationError(
                f"mvp_reason debe tener al menos {_MVP_REASON_MIN_LEN} caracteres.",
                details={"len": len(mvp_reason.strip())},
            )
        mvp_player = self._session.get(Player, mvp_player_id)
        if mvp_player is None or not mvp_player.is_active:
            raise RuleViolationError(
                f"Player id={mvp_player_id} no existe o no está activo.",
                details={"player_id": mvp_player_id},
            )

        summary = self.get_close_summary(cycle_id)
        if not summary["can_close"]:
            raise RuleViolationError(
                "El ciclo no puede cerrarse por validaciones bloqueantes.",
                details={"blocking_errors": summary["blocking_errors"]},
            )

        now = datetime.utcnow()

        # 2. closing_snapshot_json
        cycle.closing_snapshot_json = json.dumps(
            {
                "closed_at": now.isoformat(),
                "closed_by": closed_by,
                "mvp_player_id": mvp_player_id,
                "mvp_display_name": mvp_player.display_name,
                "kpis": summary["kpis"],
                "top_players": summary["top_players"],
            }
        )

        # 3. SpAdjustment MVP +5
        mvp_adj = SpAdjustment(
            subtask_key=None,
            player_id=mvp_player_id,
            adjustment_type="mvp_bonus",
            catalog_code=_MVP_BUFF_CODE,
            amount_sp=_MVP_BONUS_SP,
            reason=f"MVP del ciclo {cycle.name}: {mvp_reason.strip()}",
            applied_by=closed_by,
            applied_at=now,
            cycle_id=cycle_id,
        )
        self._session.add(mvp_adj)

        # 4. AchievementUnlock ACH04 (solo si no lo tiene)
        self._maybe_unlock_ach04(mvp_player_id, cycle_id, now)

        # 5. LeaderboardSnapshot weekly
        self._generate_leaderboard_snapshot(cycle_id, "weekly", now)

        # 6. LeaderboardSnapshot rolling_4
        self._generate_rolling4_snapshot(cycle_id, now)

        # 7. Forecast hook stub
        self._trigger_forecast_stub(cycle_id)

        # 8. Cerrar ciclo
        cycle.status = "closed"
        cycle.closed_at = now
        cycle.closed_by = closed_by
        cycle.mvp_player_id = mvp_player_id
        cycle.mvp_reason = mvp_reason.strip()
        cycle.mvp_assigned_at = now
        cycle.mvp_assigned_by = closed_by

        # 9. Activar siguiente ciclo planned
        self._activate_next_cycle(cycle)

        # 10. AuditLog
        self._audit("cycle_closed", "cycle", str(cycle_id), closed_by, {"cycle_name": cycle.name})
        self._audit(
            "mvp_assigned",
            "cycle",
            str(cycle_id),
            closed_by,
            {"mvp_player_id": mvp_player_id, "mvp_reason": mvp_reason.strip()},
        )

        self._session.flush()
        return cycle

    # ── Editar MVP (ventana 24h hábiles) ─────────────────────────────────

    def edit_mvp(
        self,
        cycle_id: int,
        new_mvp_player_id: int,
        reason: str,
        edited_by: int,
    ) -> Cycle:
        """
        Edita el MVP de un ciclo cerrado dentro de la ventana de 24h hábiles.

        Revierte el SpAdjustment del MVP anterior e inserta uno nuevo para el nuevo MVP.
        """
        cycle = self._get_cycle(cycle_id)

        if cycle.status != "closed":
            raise RuleViolationError(
                "Solo se puede editar el MVP de un ciclo 'closed'.",
                details={"cycle_id": cycle_id, "status": cycle.status},
            )
        if cycle.closed_at is None:
            raise RuleViolationError("El ciclo no tiene closed_at registrado.")

        elapsed_biz = business_hours(cycle.closed_at, datetime.utcnow())
        if elapsed_biz > _EDIT_MVP_WINDOW_BIZ_HOURS:
            raise RuleViolationError(
                f"La ventana de edición de MVP de {_EDIT_MVP_WINDOW_BIZ_HOURS}h hábiles "
                f"ha expirado (transcurridas {elapsed_biz:.1f}h hábiles).",
                details={
                    "elapsed_biz_hours": round(elapsed_biz, 2),
                    "window_biz_hours": _EDIT_MVP_WINDOW_BIZ_HOURS,
                },
            )
        if len(reason.strip()) < _MVP_REASON_MIN_LEN:
            raise RuleViolationError(
                f"reason debe tener al menos {_MVP_REASON_MIN_LEN} caracteres.",
                details={"len": len(reason.strip())},
            )

        new_player = self._session.get(Player, new_mvp_player_id)
        if new_player is None or not new_player.is_active:
            raise RuleViolationError(
                f"Player id={new_mvp_player_id} no existe o no está activo.",
                details={"player_id": new_mvp_player_id},
            )

        old_mvp_id = cycle.mvp_player_id
        now = datetime.utcnow()

        # Revertir SpAdjustment del MVP anterior
        if old_mvp_id and old_mvp_id != new_mvp_player_id:
            reversal = SpAdjustment(
                subtask_key=None,
                player_id=old_mvp_id,
                adjustment_type="mvp_reversal",
                catalog_code=_MVP_BUFF_CODE,
                amount_sp=_MVP_BONUS_SP,
                reason=f"Reversión MVP ciclo {cycle.name} — reasignado a player {new_mvp_player_id}",
                applied_by=edited_by,
                applied_at=now,
                cycle_id=cycle_id,
            )
            self._session.add(reversal)

        # Nuevo SpAdjustment para el nuevo MVP
        new_adj = SpAdjustment(
            subtask_key=None,
            player_id=new_mvp_player_id,
            adjustment_type="mvp_bonus",
            catalog_code=_MVP_BUFF_CODE,
            amount_sp=_MVP_BONUS_SP,
            reason=f"MVP del ciclo {cycle.name} (editado): {reason.strip()}",
            applied_by=edited_by,
            applied_at=now,
            cycle_id=cycle_id,
        )
        self._session.add(new_adj)

        # Unlock ACH04 al nuevo MVP si no lo tiene
        self._maybe_unlock_ach04(new_mvp_player_id, cycle_id, now)

        old_values = {
            "mvp_player_id": old_mvp_id,
            "mvp_reason": cycle.mvp_reason,
        }
        cycle.mvp_player_id = new_mvp_player_id
        cycle.mvp_reason = reason.strip()
        cycle.mvp_assigned_at = now
        cycle.mvp_assigned_by = edited_by

        self._audit(
            "mvp_edited",
            "cycle",
            str(cycle_id),
            edited_by,
            {"before": old_values, "after": {"mvp_player_id": new_mvp_player_id, "mvp_reason": reason.strip()}},
        )

        self._session.flush()
        return cycle

    # ── Historial MVP ─────────────────────────────────────────────────────

    def get_mvp_history(
        self,
        area: str | None = None,
        player_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Devuelve historial de MVPs de ciclos cerrados/archivados."""
        stmt = (
            select(Cycle)
            .where(Cycle.status.in_(["closed", "archived"]))
            .where(Cycle.mvp_player_id.isnot(None))
            .order_by(Cycle.closed_at.desc())
        )
        if player_id is not None:
            stmt = stmt.where(Cycle.mvp_player_id == player_id)

        cycles = list(self._session.scalars(stmt))

        results = []
        for c in cycles:
            player = self._session.get(Player, c.mvp_player_id)
            if player is None:
                continue
            if area and player.area != area:
                continue
            results.append(
                {
                    "cycle_id": c.id,
                    "cycle_name": c.name,
                    "closed_at": c.closed_at,
                    "mvp_player_id": c.mvp_player_id,
                    "mvp_display_name": player.display_name,
                    "mvp_area": player.area,
                    "mvp_reason": c.mvp_reason,
                }
            )
        return results

    # ── Helpers privados ──────────────────────────────────────────────────

    def _get_cycle(self, cycle_id: int) -> Cycle:
        cycle = self._session.get(Cycle, cycle_id)
        if cycle is None:
            raise NotFoundError(f"Cycle id={cycle_id} no encontrado")
        return cycle

    def _maybe_unlock_ach04(
        self, player_id: int, cycle_id: int, now: datetime
    ) -> None:
        """Desbloquea ACH04 al player si no lo tiene ya."""
        ach = self._session.get(Achievement, _MVP_ACH_CODE)
        if ach is None:
            logger.warning("Achievement ACH04 no encontrado en BD. Ejecuta 'make seed'.")
            return

        already = self._session.scalar(
            select(AchievementUnlock).where(
                AchievementUnlock.player_id == player_id,
                AchievementUnlock.achievement_code == _MVP_ACH_CODE,
            )
        )
        if already is not None:
            return

        unlock = AchievementUnlock(
            player_id=player_id,
            achievement_code=_MVP_ACH_CODE,
            unlocked_at=now,
        )
        self._session.add(unlock)
        logger.info(f"ACH04 desbloqueado para player_id={player_id}")

    def _generate_leaderboard_snapshot(
        self, cycle_id: int, period_type: str, now: datetime
    ) -> None:
        """Genera LeaderboardSnapshot ranked por SP del ciclo."""
        rows = self._session.execute(
            select(Subtask.assignee_player_id, Subtask.sp_final, Subtask.cp).where(
                Subtask.cycle_id == cycle_id,
                Subtask.status == "Done",
                Subtask.assignee_player_id.isnot(None),
            )
        ).fetchall()

        player_stats: dict[int, dict[str, float]] = {}
        for pid, sp, cp in rows:
            if pid not in player_stats:
                player_stats[pid] = {"sp": 0.0, "cp": 0.0}
            player_stats[pid]["sp"] += sp or 0.0
            player_stats[pid]["cp"] += cp or 0

        ranked = sorted(player_stats.items(), key=lambda x: x[1]["sp"], reverse=True)
        for rank, (pid, s) in enumerate(ranked, start=1):
            snap = LeaderboardSnapshot(
                sprint_id=None,
                cycle_id=cycle_id,
                player_id=pid,
                rank=rank,
                sp_total=round(s["sp"], 2),
                cp_completed=s["cp"],
                period_type=period_type,
                snapshot_at=now,
            )
            self._session.add(snap)

    def _generate_rolling4_snapshot(self, cycle_id: int, now: datetime) -> None:
        """Genera LeaderboardSnapshot rolling_4 (4 últimos ciclos cerrados incluyendo el actual)."""
        recent = self._repo.list_recent_closed(limit=4)
        recent_ids = [c.id for c in recent] + [cycle_id]
        recent_ids = list(dict.fromkeys(recent_ids))[:4]  # dedup, max 4

        rows = self._session.execute(
            select(Subtask.assignee_player_id, Subtask.sp_final, Subtask.cp).where(
                Subtask.cycle_id.in_(recent_ids),
                Subtask.status == "Done",
                Subtask.assignee_player_id.isnot(None),
            )
        ).fetchall()

        player_stats: dict[int, dict[str, float]] = {}
        for pid, sp, cp in rows:
            if pid not in player_stats:
                player_stats[pid] = {"sp": 0.0, "cp": 0.0}
            player_stats[pid]["sp"] += sp or 0.0
            player_stats[pid]["cp"] += cp or 0

        ranked = sorted(player_stats.items(), key=lambda x: x[1]["sp"], reverse=True)
        for rank, (pid, s) in enumerate(ranked, start=1):
            snap = LeaderboardSnapshot(
                sprint_id=None,
                cycle_id=cycle_id,
                player_id=pid,
                rank=rank,
                sp_total=round(s["sp"], 2),
                cp_completed=s["cp"],
                period_type="rolling_4",
                snapshot_at=now,
            )
            self._session.add(snap)

    def _activate_next_cycle(self, current_cycle: Cycle) -> None:
        """Activa el ciclo 'planned' con menor start_date posterior al actual."""
        stmt = (
            select(Cycle)
            .where(
                Cycle.status == "planned",
                Cycle.start_date > current_cycle.start_date,
            )
            .order_by(Cycle.start_date.asc())
            .limit(1)
        )
        next_cycle = self._session.scalars(stmt).first()
        if next_cycle is None:
            logger.warning(
                f"No hay ciclo 'planned' después de {current_cycle.name}. "
                "Ejecuta 'forge cycle-generate' para crear ciclos futuros."
            )
            return
        next_cycle.status = "active"
        next_cycle.opened_at = datetime.utcnow()
        logger.info(f"Ciclo {next_cycle.name} activado automáticamente al cierre.")

    def _trigger_forecast_stub(self, cycle_id: int) -> None:
        """Hook de forecast — stub hasta WP-05."""
        from forge.services.forecast_service import ForecastService

        ForecastService(self._session).recalculate_open_epics(cycle_id)

    def _audit(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        actor_id: int,
        changes: dict[str, Any],
    ) -> None:
        log = AuditLog(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_player_id=actor_id,
            changes=json.dumps(changes),
            timestamp=datetime.utcnow(),
        )
        self._session.add(log)
