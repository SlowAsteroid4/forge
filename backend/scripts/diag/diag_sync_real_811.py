"""Corre el SyncOrchestrator REAL de una sola subtask sobre /tmp/diag_sync_811.db.

Intercepta el SQL generado para ver exactamente qué UPDATE emite SQLAlchemy.
No toca forge.db real.
"""

import asyncio
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

REAL_DB = Path(__file__).parent.parent.parent / "forge.db"
COPY_DB = Path("/tmp/diag_sync_811.db")
KEY = "YAP-811"


async def main() -> None:
    shutil.copy2(REAL_DB, COPY_DB)
    print(f"Copia: {REAL_DB} → {COPY_DB}")

    # Engine con echo=True para capturar SQL
    engine = create_engine(f"sqlite:///{COPY_DB}", echo=False)

    # Interceptar UPDATE statements
    updates_seen: list[str] = []

    @event.listens_for(engine, "before_execute")
    def before_execute(conn, clauseelement, multiparams, params, execution_options):
        sql_str = str(clauseelement)
        if "UPDATE" in sql_str.upper() and "subtasks" in sql_str.lower():
            updates_seen.append(sql_str[:500])

    Session = sessionmaker(bind=engine)
    session = Session()

    # Estado ANTES
    before = session.execute(
        text("SELECT complexity_size, cp, last_synced_at FROM subtasks WHERE jira_key = :k"),
        {"k": KEY},
    ).one()
    print(f"\n[ANTES] complexity_size={before.complexity_size!r}  cp={before.cp!r}")
    session.close()

    # Corre el SyncOrchestrator real con JQL forzado a YAP-811
    session2 = Session()
    from forge.etl.sync_orchestrator import SyncOrchestrator
    orch = SyncOrchestrator(session=session2)
    # Patch la BD para que use nuestra copia
    # (el engine ya apunta a /tmp — la session factory ya creó la sesión con ese engine)

    print(f"\n[Sync] Corriendo sync con JQL='issue = \"{KEY}\"'...")
    stats = await orch.sync_all(jql=f'issue = "{KEY}"')
    print(f"Stats: {stats}")

    # Estado DESPUÉS
    after = session2.execute(
        text("SELECT complexity_size, cp, last_synced_at FROM subtasks WHERE jira_key = :k"),
        {"k": KEY},
    ).one()
    print(f"\n[DESPUÉS] complexity_size={after.complexity_size!r}  cp={after.cp!r}")

    # Mostrar UPDATE SQL interceptados
    print("\n[SQL interceptados — UPDATE subtasks]")
    if updates_seen:
        for sql in updates_seen:
            # Muestra si complexity_size aparece en el SET
            if "complexity_size" in sql:
                print("  ✅ complexity_size APARECE en el UPDATE")
            else:
                print("  ❌ complexity_size NO aparece en el UPDATE")
            print(f"  SQL: {sql[:300]}")
    else:
        print("  (ningún UPDATE interceptado — posiblemente SQLAlchemy usó flush implícito)")

    # Diagnóstico final
    print(f"\n{'='*70}")
    if after.complexity_size == "M":
        print("✅ Sync real con SyncOrchestrator SÍ persiste complexity_size='M'")
        print("   → El bug está en el JQL del sync real (updated >= -14d excluye issues viejos)")
        print("   → YAP-811 no entra al sync diario porque fue updated hace 23+ días")
    else:
        print("❌ Sync real NO persiste complexity_size — bug en el orchestrator")
        print("   → Revisar qué SQL generó SQLAlchemy (ver arriba)")

    # forge.db intacto
    check_engine = create_engine(f"sqlite:///{REAL_DB}", echo=False)
    with check_engine.connect() as conn:
        real_val = conn.execute(
            text("SELECT complexity_size FROM subtasks WHERE jira_key = :k"), {"k": KEY}
        ).scalar()
    print(f"\nforge.db real: complexity_size = {real_val!r} (debe ser NULL)")
    check_engine.dispose()
    session2.close()
    engine.dispose()
    COPY_DB.unlink(missing_ok=True)
    print("/tmp/diag_sync_811.db borrado ✓")


if __name__ == "__main__":
    asyncio.run(main())
