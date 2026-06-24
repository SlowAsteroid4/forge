"""Diagnóstico forense de velocity CP/día para Juan Castillo (player_id=7).

Read-only. No modifica la base de datos.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from forge.db.session import SessionLocal
from forge.db.models import Subtask, Cycle
from forge.services.analytics_service import AnalyticsService

JUAN_ID = 7


def main() -> None:
    session = SessionLocal()
    try:
        svc = AnalyticsService(session)

        print(f"\n{'='*70}")
        print("VELOCITY CP/DÍA FORENSE — Juan Castillo (player_id=7)")
        print(f"{'='*70}")

        # --- Service output per scope ---
        for scope in ("cycle", "window"):
            devs = svc.cp_per_day_by_dev(scope=scope)
            juan_row = next((d for d in devs if d["player_id"] == JUAN_ID), None)
            print(f"\n[scope={scope}]  row del servicio para Juan:")
            if juan_row:
                print(f"  done_count={juan_row['done_count']}  total_cp={juan_row['total_cp']}"
                      f"  biz_days={juan_row['biz_days']}  cp_per_day={juan_row['cp_per_day']}")
            else:
                print("  (Juan no aparece en el resultado — done_count=0 o total_cp=0 o fuera del scope)")

        # --- Raw Done subtasks ---
        done_all = (
            session.query(Subtask)
            .filter(Subtask.assignee_player_id == JUAN_ID, Subtask.status == "Done")
            .order_by(Subtask.cycle_id.asc().nullslast(), Subtask.jira_key)
            .all()
        )

        print(f"\n{'='*70}")
        print("DUMP CRUDO — Done subtasks de Juan")
        print(f"{'jira_key':<12} {'cycle_id':>9} {'cp':>5} {'complexity_size':>15} {'sp_final':>9}")
        print("-" * 55)
        for s in done_all:
            print(f"{s.jira_key:<12} {str(s.cycle_id or ''):>9} {str(s.cp or ''):>5}"
                  f" {str(s.complexity_size or ''):>15} {str(s.sp_final or ''):>9}")

        # --- Window cycle IDs ---
        window_ids = (
            session.query(Cycle.id)
            .filter(Cycle.status.in_(["closed", "archived"]))
            .order_by(Cycle.start_date.desc())
            .limit(4)
            .all()
        )
        window_ids = [r[0] for r in window_ids]
        active_id = session.query(Cycle.id).filter(Cycle.status == "active").scalar()

        print(f"\nWindow cycle_ids: {window_ids}")
        print(f"Active cycle_id:  {active_id}")

        # --- Diagnostic counts ---
        done_cp_gt0 = [s for s in done_all if s.cp is not None and s.cp > 0]
        done_in_window = [s for s in done_all if s.cycle_id in window_ids]
        done_in_window_cp_gt0 = [s for s in done_in_window if s.cp is not None and s.cp > 0]
        done_in_active = [s for s in done_all if s.cycle_id == active_id]

        print(f"\n{'='*70}")
        print("DIAGNÓSTICO — Causas de velocity=0")
        print(f"  Total Done de Juan:                      {len(done_all)}")
        print(f"  Done con cp>0:                           {len(done_cp_gt0)}   ← H1: {'CONFIRMADO' if not done_cp_gt0 else 'DESCARTADO'}")
        print(f"  Done en ventana (cycles {window_ids}):  {len(done_in_window)}")
        print(f"  Done en ventana con cp>0:                {len(done_in_window_cp_gt0)}  ← H2: {'CONFIRMADO' if not done_in_window else 'DESCARTADO'}")
        print(f"  Done en ciclo activo ({active_id}):          {len(done_in_active)}  ← H3: {'CONFIRMADO' if not done_in_active and not done_in_window else 'DESCARTADO'}")

        print(f"\n{'='*70}")
        if not done_cp_gt0:
            print("CAUSA RAÍZ: H1 — cp=NULL en todos los Done de Juan.")
            print("  SUM(cp)=0 → cp_per_day=0 independientemente del scope.")
            print("  Query que lo prueba:")
            print("    SELECT COUNT(*) FROM subtasks")
            print(f"    WHERE assignee_player_id=7 AND status='Done' AND cp > 0;")
            print(f"    → {len(done_cp_gt0)} filas")
            print("\n  Fix implicado: correr motor de CP sobre Done de Juan (make recalc")
            print("  o aprobación CP si L/XL requiere approval). NO aplicado en este WP.")
        elif not done_in_window:
            print("CAUSA RAÍZ: H2 — Juan no tiene Done en la ventana móvil.")
        else:
            print("CAUSA RAÍZ: H3 — scope default muestra ciclo activo (vacío).")

        print()

    finally:
        session.close()


if __name__ == "__main__":
    main()
