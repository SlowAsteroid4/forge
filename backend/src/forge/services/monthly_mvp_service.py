"""MonthlyMvpService — UC-17: ritual de cierre mensual y MVP del Mes."""

from __future__ import annotations

import calendar
import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from forge.core.exceptions import NotFoundError, RuleViolationError
from forge.core.time_utils import business_hours
from forge.db.models.achievement import Achievement
from forge.db.models.achievement_unlock import AchievementUnlock
from forge.db.models.audit_log import AuditLog
from forge.db.models.cycle import Cycle
from forge.db.models.mvp_monthly import MvpMonthly
from forge.db.models.player import Player
from forge.db.models.sp_adjustment import SpAdjustment
from forge.db.models.subtask import Subtask

logger = logging.getLogger(__name__)

_MONTHLY_MVP_BONUS_SP = 10.0
_MONTHLY_MVP_BUFF_CODE = "B17M"
_MVP_ACH_CODE = "ACH04"
_REASON_MIN_LEN = 30
# 72 business hours for edit window (vs 24h for weekly)
_EDIT_WINDOW_BIZ_HOURS = 72.0

# AC-17.6: el mes necesita >=4 ciclos del mes en estado closed/archived para el cierre.
# GATE: número de ciclos cerrados (independiente de cuántos MVPs distintos haya —
# un player puede repetir MVP en varios ciclos del mismo mes).
# CANDIDATOS: DISTINCT mvp_player_id de esos ciclos (puede ser < 4 si alguien repitió).
_MIN_CLOSED_CYCLES_FOR_CLOSE = 4


class MonthlyMvpService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Candidatos ────────────────────────────────────────────────────────

    def list_candidates(self, year: int, month: int) -> list[dict[str, Any]]:
        """
        Devuelve los players que fueron MVP semanal en al menos un ciclo del mes.

        AC-17.4: solo MVPs semanales del mes son elegibles.
        """
        cycles = self._get_month_cycles(year, month)
        if not cycles:
            raise NotFoundError(f"No hay ciclos registrados para {year}-{month:02d}")

        candidates: list[dict[str, Any]] = []
        seen: set[int] = set()

        for cycle in cycles:
            if cycle.mvp_player_id is None:
                continue
            pid = cycle.mvp_player_id
            if pid in seen:
                continue
            seen.add(pid)

            player = self._session.get(Player, pid)
            if player is None or not player.is_active:
                continue

            # Ciclos del mes donde fue MVP semanal
            source_cycles = [c for c in cycles if c.mvp_player_id == pid]
            source_names = [c.name for c in source_cycles]

            # Métricas del player en el mes
            subtask_rows = self._session.execute(
                select(Subtask.sp_final, Subtask.cp, Subtask.m_calidad).where(
                    Subtask.cycle_id.in_([c.id for c in cycles]),
                    Subtask.assignee_player_id == pid,
                    Subtask.status == "Done",
                )
            ).fetchall()

            sp_total = sum(r.sp_final or 0.0 for r in subtask_rows)
            cp_total = sum(r.cp or 0 for r in subtask_rows)
            subtasks_done = len(subtask_rows)
            calidad_vals = [r.m_calidad for r in subtask_rows if r.m_calidad is not None]
            avg_calidad = sum(calidad_vals) / len(calidad_vals) if calidad_vals else None

            candidates.append(
                {
                    "player_id": pid,
                    "display_name": player.display_name,
                    "area": player.area or "",
                    "mvp_cycles": source_names,
                    "mvp_cycle_ids": [c.id for c in source_cycles],
                    "sp_total_month": round(sp_total, 2),
                    "cp_total_month": cp_total,
                    "subtasks_done_month": subtasks_done,
                    "avg_m_calidad": round(avg_calidad, 3) if avg_calidad else None,
                    "metric_highlight": (
                        f"{sp_total:.1f} SP en {subtasks_done} subtasks — "
                        f"MVP en: {', '.join(source_names)}"
                    ),
                }
            )

        return sorted(candidates, key=lambda x: x["sp_total_month"], reverse=True)

    # ── Resumen pre-cierre ────────────────────────────────────────────────

    def get_month_close_summary(self, year: int, month: int) -> dict[str, Any]:
        """Resumen del mes con KPIs, candidatos y validaciones bloqueantes/warnings."""
        cycles = self._get_month_cycles(year, month)
        all_cycle_ids = [c.id for c in cycles]

        # KPIs del mes
        subtask_rows = self._session.execute(
            select(Subtask.assignee_player_id, Subtask.cp, Subtask.sp_final).where(
                Subtask.cycle_id.in_(all_cycle_ids),
                Subtask.status == "Done",
            )
        ).fetchall() if all_cycle_ids else []

        cp_done = sum(r.cp or 0 for r in subtask_rows)
        sp_generated = sum(r.sp_final or 0.0 for r in subtask_rows)
        subtasks_done = len(subtask_rows)

        # Ciclos por estado
        by_status: dict[str, list[str]] = {}
        for c in cycles:
            by_status.setdefault(c.status, []).append(c.name)

        # Candidatos
        try:
            candidates = self.list_candidates(year, month)
        except NotFoundError:
            candidates = []

        # ¿Ya existe cierre mensual?
        existing = self._get_existing_monthly(year, month)

        # Validaciones bloqueantes
        blocking_errors: list[str] = []

        # 1. AC-17.6: gate de >=4 ciclos del mes en closed/archived con MVP semanal asignado
        cycles_with_mvp = [c for c in cycles if c.status in ("closed", "archived") and c.mvp_player_id is not None]
        n_closed_with_mvp = len(cycles_with_mvp)
        if n_closed_with_mvp < _MIN_CLOSED_CYCLES_FOR_CLOSE:
            blocking_errors.append(
                f"Este mes tiene {n_closed_with_mvp} ciclo(s) cerrado(s) con MVP semanal; "
                f"se requieren {_MIN_CLOSED_CYCLES_FOR_CLOSE} para el cierre mensual."
            )

        # 2. No debe existir ya un cierre mensual
        if existing is not None:
            blocking_errors.append(
                f"El mes {year}-{month:02d} ya tiene MVP del Mes asignado "
                f"(player_id={existing.player_id}, period={existing.period_label})."
            )

        # Warnings
        warnings: list[str] = []
        active_in_month = by_status.get("active", [])
        if active_in_month:
            warnings.append(
                f"Hay {len(active_in_month)} ciclo(s) aún activo(s) en el mes: "
                f"{', '.join(active_in_month)}. Idealmente deben estar closed/archived."
            )
        planned_in_month = by_status.get("planned", [])
        if planned_in_month:
            warnings.append(
                f"{len(planned_in_month)} ciclo(s) planned en el mes: "
                f"{', '.join(planned_in_month)}."
            )

        return {
            "year": year,
            "month": month,
            "period_label": f"{year}-{month:02d}",
            "cycles": [
                {
                    "cycle_id": c.id,
                    "name": c.name,
                    "status": c.status,
                    "mvp_player_id": c.mvp_player_id,
                }
                for c in cycles
            ],
            "kpis": {
                "cp_done": cp_done,
                "sp_generated": round(sp_generated, 2),
                "subtasks_done": subtasks_done,
                "cycles_total": len(cycles),
                "cycles_closed_or_archived": sum(
                    1 for c in cycles if c.status in ("closed", "archived")
                ),
            },
            "candidates": candidates,
            "already_closed": existing is not None,
            "can_close": len(blocking_errors) == 0,
            "blocking_errors": blocking_errors,
            "warnings": warnings,
        }

    # ── Cierre mensual ────────────────────────────────────────────────────

    def close_month(
        self,
        year: int,
        month: int,
        mvp_player_id: int,
        reason: str,
        admin_id: int,
    ) -> MvpMonthly:
        """
        Ritual de cierre mensual (transacción única).

        Pasos:
          1. Validaciones
          2. REGLA BLOQUEANTE: mvp_player_id must be a weekly MVP of the month (SQL check)
          3. INSERT mvp_monthly
          4. SpAdjustment B17M +10 SP
          5. AchievementUnlock ACH04 (primera vez)
          6. AuditLog
        """
        if len(reason.strip()) < _REASON_MIN_LEN:
            raise RuleViolationError(
                f"reason debe tener al menos {_REASON_MIN_LEN} caracteres.",
                details={"len": len(reason.strip()), "min": _REASON_MIN_LEN},
            )

        summary = self.get_month_close_summary(year, month)
        if not summary["can_close"]:
            raise RuleViolationError(
                f"El mes {year}-{month:02d} no puede cerrarse.",
                details={"blocking_errors": summary["blocking_errors"]},
            )

        # 2. REGLA BLOQUEANTE (SQL): mvp_player_id must have been a weekly MVP in this month
        cycles = self._get_month_cycles(year, month)
        eligible_ids = {c.mvp_player_id for c in cycles if c.mvp_player_id is not None}
        if mvp_player_id not in eligible_ids:
            raise RuleViolationError(
                f"Player id={mvp_player_id} no fue MVP semanal en ningún ciclo de "
                f"{year}-{month:02d}. Solo son elegibles: {sorted(eligible_ids)}. "
                "AC-17.4: el MVP del Mes debe ser uno de los MVPs semanales del mes.",
                details={
                    "requested_player_id": mvp_player_id,
                    "eligible_player_ids": sorted(eligible_ids),
                },
            )

        player = self._session.get(Player, mvp_player_id)
        if player is None or not player.is_active:
            raise RuleViolationError(
                f"Player id={mvp_player_id} no existe o no está activo.",
                details={"player_id": mvp_player_id},
            )

        now = datetime.utcnow()
        cycle_ids = [c.id for c in cycles]
        period_label = f"{year}-{month:02d}"

        # 3. INSERT mvp_monthly
        record = MvpMonthly(
            year=year,
            month=month,
            player_id=mvp_player_id,
            reason=reason.strip(),
            sp_reward=int(_MONTHLY_MVP_BONUS_SP),
            assigned_at=now,
            assigned_by=admin_id,
            period_label=period_label,
            source_cycle_ids=json.dumps(cycle_ids),
        )
        self._session.add(record)

        # 4. SpAdjustment B17M +10
        adj = SpAdjustment(
            subtask_key=None,
            player_id=mvp_player_id,
            adjustment_type="mvp_bonus",
            catalog_code=_MONTHLY_MVP_BUFF_CODE,
            amount_sp=_MONTHLY_MVP_BONUS_SP,
            reason=f"MVP del Mes {period_label}: {reason.strip()}",
            applied_by=admin_id,
            applied_at=now,
            cycle_id=None,
        )
        self._session.add(adj)

        # 5. ACH04 (primera vez)
        self._maybe_unlock_ach04(mvp_player_id, now)

        # 6. AuditLog
        self._audit(
            "mvp_monthly_assigned",
            "mvp_monthly",
            period_label,
            admin_id,
            {
                "player_id": mvp_player_id,
                "display_name": player.display_name,
                "reason": reason.strip(),
                "source_cycle_ids": cycle_ids,
            },
        )

        self._session.flush()
        return record

    # ── Edición MVP (72h hábiles) ─────────────────────────────────────────

    def edit_monthly_mvp(
        self,
        year: int,
        month: int,
        new_player_id: int,
        reason: str,
        admin_id: int,
    ) -> MvpMonthly:
        """
        Edita el MVP del mes dentro de la ventana de 72h hábiles.

        Reversal append-only: INSERT SpAdjustment -10 (al anterior) + INSERT +10 (al nuevo).
        """
        record = self._get_existing_monthly(year, month)
        if record is None:
            raise NotFoundError(
                f"No existe cierre mensual para {year}-{month:02d}. Cierra el mes primero."
            )

        elapsed_biz = business_hours(record.assigned_at, datetime.utcnow())
        if elapsed_biz > _EDIT_WINDOW_BIZ_HOURS:
            raise RuleViolationError(
                f"La ventana de edición de {_EDIT_WINDOW_BIZ_HOURS}h hábiles expiró "
                f"(transcurridas {elapsed_biz:.1f}h hábiles).",
                details={
                    "elapsed_biz_hours": round(elapsed_biz, 2),
                    "window_biz_hours": _EDIT_WINDOW_BIZ_HOURS,
                },
            )

        if len(reason.strip()) < _REASON_MIN_LEN:
            raise RuleViolationError(
                f"reason debe tener al menos {_REASON_MIN_LEN} caracteres.",
                details={"len": len(reason.strip()), "min": _REASON_MIN_LEN},
            )

        # REGLA BLOQUEANTE: nuevo player también debe ser MVP semanal del mes
        cycles = self._get_month_cycles(year, month)
        eligible_ids = {c.mvp_player_id for c in cycles if c.mvp_player_id is not None}
        if new_player_id not in eligible_ids:
            raise RuleViolationError(
                f"Player id={new_player_id} no fue MVP semanal en ningún ciclo de "
                f"{year}-{month:02d}. Elegibles: {sorted(eligible_ids)}.",
                details={
                    "requested_player_id": new_player_id,
                    "eligible_player_ids": sorted(eligible_ids),
                },
            )

        new_player = self._session.get(Player, new_player_id)
        if new_player is None or not new_player.is_active:
            raise RuleViolationError(
                f"Player id={new_player_id} no existe o no está activo.",
                details={"player_id": new_player_id},
            )

        old_player_id = record.player_id
        now = datetime.utcnow()
        period_label = f"{year}-{month:02d}"

        # Reversal append-only: -10 al anterior (si es distinto)
        if old_player_id != new_player_id:
            reversal = SpAdjustment(
                subtask_key=None,
                player_id=old_player_id,
                adjustment_type="mvp_reversal",
                catalog_code=_MONTHLY_MVP_BUFF_CODE,
                amount_sp=_MONTHLY_MVP_BONUS_SP,
                reason=(
                    f"Reversión MVP Mensual {period_label} — "
                    f"reasignado a player {new_player_id}"
                ),
                applied_by=admin_id,
                applied_at=now,
                cycle_id=None,
            )
            self._session.add(reversal)

        # Nuevo +10 al nuevo MVP
        new_adj = SpAdjustment(
            subtask_key=None,
            player_id=new_player_id,
            adjustment_type="mvp_bonus",
            catalog_code=_MONTHLY_MVP_BUFF_CODE,
            amount_sp=_MONTHLY_MVP_BONUS_SP,
            reason=f"MVP del Mes {period_label} (editado): {reason.strip()}",
            applied_by=admin_id,
            applied_at=now,
            cycle_id=None,
        )
        self._session.add(new_adj)

        # ACH04 al nuevo MVP si no lo tiene
        self._maybe_unlock_ach04(new_player_id, now)

        old_values = {
            "player_id": old_player_id,
            "reason": record.reason,
        }

        # Update record (solo metadata mutable, SP es append-only)
        record.player_id = new_player_id
        record.reason = reason.strip()
        record.assigned_at = now
        record.assigned_by = admin_id

        self._audit(
            "mvp_monthly_edited",
            "mvp_monthly",
            period_label,
            admin_id,
            {
                "before": old_values,
                "after": {
                    "player_id": new_player_id,
                    "reason": reason.strip(),
                },
            },
        )

        self._session.flush()
        return record

    # ── Historial ─────────────────────────────────────────────────────────

    def get_history(
        self,
        year: int | None = None,
        player_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Historial de MVPs mensuales con filtros opcionales."""
        stmt = select(MvpMonthly).order_by(MvpMonthly.year.desc(), MvpMonthly.month.desc())
        if year is not None:
            stmt = stmt.where(MvpMonthly.year == year)
        if player_id is not None:
            stmt = stmt.where(MvpMonthly.player_id == player_id)

        records = list(self._session.scalars(stmt))
        results = []
        for r in records:
            player = self._session.get(Player, r.player_id)
            assigner = self._session.get(Player, r.assigned_by)
            results.append(
                {
                    "id": r.id,
                    "period_label": r.period_label,
                    "year": r.year,
                    "month": r.month,
                    "player_id": r.player_id,
                    "display_name": player.display_name if player else f"Player {r.player_id}",
                    "area": player.area if player else None,
                    "reason": r.reason,
                    "sp_reward": r.sp_reward,
                    "assigned_at": r.assigned_at,
                    "assigned_by_name": assigner.display_name if assigner else f"Player {r.assigned_by}",
                    "source_cycle_ids": json.loads(r.source_cycle_ids) if r.source_cycle_ids else [],
                }
            )
        return results

    # ── Reversión auditada (admin) ────────────────────────────────────────

    def revert_month(self, year: int, month: int, reason: str, admin_id: int) -> None:
        """
        Revierte un cierre mensual de demo/error de forma append-only y auditada.

        - SpAdjustment reversal -10 (B17M) al player anterior.
        - Elimina la fila mvp_monthly (es un registro de demo inválido bajo regla estricta).
        - NO toca AchievementUnlock: si el player ya tenía ACH04 por otra vía, no se altera.
        - AuditLog action_type='mvp_monthly_reverted'.
        """
        record = self._get_existing_monthly(year, month)
        if record is None:
            raise NotFoundError(f"No existe cierre mensual para {year}-{month:02d}.")

        now = datetime.utcnow()
        period_label = f"{year}-{month:02d}"

        # Reversal SP append-only
        reversal = SpAdjustment(
            subtask_key=None,
            player_id=record.player_id,
            adjustment_type="mvp_reversal",
            catalog_code=_MONTHLY_MVP_BUFF_CODE,
            amount_sp=float(record.sp_reward),
            reason=f"Reversión cierre mensual {period_label} (demo con umbral relajado): {reason}",
            applied_by=admin_id,
            applied_at=now,
            cycle_id=None,
        )
        self._session.add(reversal)

        self._audit(
            "mvp_monthly_reverted",
            "mvp_monthly",
            period_label,
            admin_id,
            {
                "reverted_player_id": record.player_id,
                "reverted_sp": record.sp_reward,
                "reason": reason,
                "original_assigned_at": record.assigned_at.isoformat(),
            },
        )

        self._session.delete(record)
        self._session.flush()

    # ── Helpers privados ──────────────────────────────────────────────────

    def _get_month_cycles(self, year: int, month: int) -> list[Cycle]:
        """Devuelve todos los ciclos que pertenecen al mes dado (por start_date)."""
        _, last_day = calendar.monthrange(year, month)
        # Match cycles that start within the month
        from sqlalchemy import extract

        stmt = select(Cycle).where(
            extract("year", Cycle.start_date) == year,
            extract("month", Cycle.start_date) == month,
        ).order_by(Cycle.start_date.asc())
        return list(self._session.scalars(stmt))

    def _get_existing_monthly(self, year: int, month: int) -> MvpMonthly | None:
        return self._session.scalar(
            select(MvpMonthly).where(
                MvpMonthly.year == year,
                MvpMonthly.month == month,
            )
        )

    def _maybe_unlock_ach04(self, player_id: int, now: datetime) -> None:
        """Desbloquea ACH04 si el player no lo tiene ya."""
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
            logger.info(f"Player {player_id} ya tiene ACH04 — no se duplica.")
            return

        unlock = AchievementUnlock(
            player_id=player_id,
            achievement_code=_MVP_ACH_CODE,
            unlocked_at=now,
        )
        self._session.add(unlock)
        logger.info(f"ACH04 desbloqueado para player_id={player_id}")

    def _audit(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        user_id: int,
        extra: dict[str, Any],
    ) -> None:
        log = AuditLog(
            event_type=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_player_id=user_id,
            extra_metadata=json.dumps(extra),
            timestamp=datetime.utcnow(),
        )
        self._session.add(log)
