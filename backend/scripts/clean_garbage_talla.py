"""
Limpia las 8 filas basura de complexity_size que quedaron del setup de WP-02a.

Estas filas tienen cp_approved_at seteado con datos incorrectos (0/8 coinciden
con Jira según diagnóstico T-01). El resync posterior traerá los valores reales.

Idempotente: si se corre dos veces, la segunda no modifica nada (WHERE filtra
por complexity_size IS NOT NULL, que ya estaría NULL tras la primera ejecución).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import select, text

from forge.db.models.subtask import Subtask
from forge.db.session import SessionLocal


def main() -> None:
    session = SessionLocal()
    try:
        rows = session.execute(
            select(
                Subtask.jira_key,
                Subtask.complexity_size,
                Subtask.cp,
                Subtask.cp_approved_at,
                Subtask.cp_proposed_at,
            ).where(Subtask.complexity_size.is_not(None))
        ).fetchall()

        print(f"\n=== ANTES: {len(rows)} filas con complexity_size ===")
        print(f"{'jira_key':<12} {'talla':<6} {'cp':<5} {'cp_approved_at':<30} {'cp_proposed_at'}")
        print("-" * 90)
        for r in rows:
            print(f"{r.jira_key:<12} {r.complexity_size or '':<6} {str(r.cp or ''):<5} "
                  f"{str(r.cp_approved_at or ''):<30} {r.cp_proposed_at or ''}")

        if not rows:
            print("Nada que limpiar — ya estaba limpio.")
            return

        keys = [r.jira_key for r in rows]

        # Limpiar todos los campos CP relacionados
        session.execute(
            text(
                """
                UPDATE subtasks SET
                    complexity_size         = NULL,
                    cp                      = NULL,
                    cp_proposed_by          = NULL,
                    cp_proposed_at          = NULL,
                    cp_approved_by          = NULL,
                    cp_approved_at          = NULL,
                    cp_approval_required    = 0,
                    cp_rejection_reason     = NULL,
                    cp_modified_post_approval = 0
                WHERE complexity_size IS NOT NULL
                """
            )
        )
        session.commit()

        remaining = session.execute(
            select(Subtask.jira_key).where(Subtask.complexity_size.is_not(None))
        ).fetchall()

        print(f"\n=== DESPUÉS: {len(remaining)} filas con complexity_size (debe ser 0) ===")
        print(f"Limpiadas: {len(keys)} filas → {', '.join(keys)}")

    finally:
        session.close()


if __name__ == "__main__":
    main()
