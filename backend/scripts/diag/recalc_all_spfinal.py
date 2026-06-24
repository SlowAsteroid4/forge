"""
Recalc global de sp_final para todas las subtasks Done con cp.

Contexto: make recalc solo opera el ciclo activo. Este script recalcula
todas las subtasks Done con cp IS NOT NULL, sin importar ciclo. Usado
en WP-07i para materializar sp_final tras el backfill de talla (WP-07f/g)
y el ajuste de dev_resp_biz_hours (WP-07h).

Inmutabilidad: el engine garantiza que cp y complexity_size nunca se
modifican por el recalc. Solo se actualizan multiplicadores y sp_final.
"""

import sys
from pathlib import Path

# Asegurar que src/ esté en el path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlalchemy import select

from forge.db.models.player import Player
from forge.db.models.subtask import Subtask
from forge.db.session import SessionLocal
from forge.services.engine.engine_orchestrator import recalculate_subtask


def main() -> None:
    session = SessionLocal()
    try:
        # Sistema: PM player
        system_player = session.scalars(
            select(Player).where(Player.area == "PM").limit(1)
        ).first()
        if system_player is None:
            print("ERROR: No hay player con area='PM' para system_player")
            sys.exit(1)
        print(f"System player: {system_player.display_name} (id={system_player.id})")

        # Contar estado inicial
        from sqlalchemy import func, text

        result = session.execute(
            text(
                "SELECT COUNT(*) done, "
                "SUM(cp IS NOT NULL) con_cp, "
                "SUM(sp_final IS NOT NULL) con_sp, "
                "SUM(cp IS NOT NULL AND sp_final IS NULL) cp_sin_sp "
                "FROM subtasks WHERE status='Done'"
            )
        ).fetchone()
        print(
            f"\nESTADO INICIAL: done={result[0]}, con_cp={result[1]}, "
            f"con_sp={result[2]}, cp_sin_sp={result[3]}"
        )

        # Capturar cp de subtasks aprobadas ANTES (para verificar inmutabilidad global)
        approved_before = {
            row.jira_key: row.cp
            for row in session.execute(
                select(Subtask.jira_key, Subtask.cp).where(
                    Subtask.cp_approved_at.is_not(None)
                )
            ).fetchall()
        }
        print(f"Subtasks aprobadas: {len(approved_before)}")

        # Obtener todas las subtasks Done con cp (independiente de ciclo)
        keys_result = session.execute(
            select(Subtask.jira_key).where(
                Subtask.status == "Done",
                Subtask.cp.is_not(None),
            )
        ).fetchall()
        keys = [row[0] for row in keys_result]
        print(f"\nSubtasks Done con cp a recalcular: {len(keys)}")

        processed = 0
        skipped = 0
        errors = 0
        sp_total = 0.0

        for i, key in enumerate(keys):
            try:
                components = recalculate_subtask(
                    session, key, system_player.id, force=True
                )
                processed += 1
                sp_total += components.sp_final
                if (i + 1) % 25 == 0:
                    print(f"  ... {i+1}/{len(keys)} procesadas")
            except Exception as exc:
                errors += 1
                print(f"  ERROR en {key}: {exc}")

        print(f"\nRESULTADO RECALC:")
        print(f"  Procesadas: {processed}")
        print(f"  Omitidas:   {skipped}")
        print(f"  Errores:    {errors}")
        print(f"  SP total:   {sp_total:.2f}")

        # Commit
        session.commit()
        print("\n✅ COMMIT realizado.")

        # VERIFICAR PERSISTENCIA EN BD (no creerle al log — lección WP-03b/07f)
        result2 = session.execute(
            text(
                "SELECT COUNT(*) done, "
                "SUM(cp IS NOT NULL) con_cp, "
                "SUM(sp_final IS NOT NULL) con_sp, "
                "SUM(cp IS NOT NULL AND sp_final IS NULL) cp_sin_sp "
                "FROM subtasks WHERE status='Done'"
            )
        ).fetchone()
        print(
            f"\nESTADO POST-COMMIT (verificación real BD):\n"
            f"  done={result2[0]}, con_cp={result2[1]}, "
            f"con_sp={result2[2]}, cp_sin_sp={result2[3]}"
        )

        if result2[3] == 0:
            print("  ✅ cp_sin_sp = 0: todos los cp tienen sp_final")
        else:
            print(f"  ⚠️  cp_sin_sp = {result2[3]}: quedan subtasks sin sp_final")

        # Verificar inmutabilidad global
        approved_after = {
            row.jira_key: row.cp
            for row in session.execute(
                select(Subtask.jira_key, Subtask.cp).where(
                    Subtask.cp_approved_at.is_not(None)
                )
            ).fetchall()
        }
        mutated = [k for k, v in approved_before.items() if approved_after.get(k) != v]
        if mutated:
            print(f"\n🚨 VIOLACIÓN INMUTABILIDAD: {len(mutated)} cp aprobados cambiaron: {mutated[:5]}")
        else:
            print(
                f"\n✅ INMUTABILIDAD GLOBAL INTACTA: {len(approved_before)} cp aprobados "
                f"— ninguno cambió de valor"
            )

        # Leaderboard post-recalc
        print("\n📊 LEADERBOARD POST-RECALC:")
        lb = session.execute(
            text(
                "SELECT p.display_name, p.area, ROUND(SUM(s.sp_final),1) sp "
                "FROM subtasks s "
                "JOIN players p ON s.assignee_player_id = p.id "
                "WHERE s.status='Done' AND s.sp_final IS NOT NULL "
                "GROUP BY s.assignee_player_id "
                "ORDER BY sp DESC"
            )
        ).fetchall()
        for row in lb:
            print(f"  {row[0]:35s} | {row[1]:4s} | {row[2]:6.1f} SP")

    except Exception as exc:
        session.rollback()
        print(f"\n❌ ERROR FATAL: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
