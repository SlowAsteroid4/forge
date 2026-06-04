"""PASO 4: sync instrumentado de YAP-811 sobre /tmp/diag_811.db.

Único script que escribe — pero SOLO a la copia temporal, nunca a forge.db.
Demuestra si el problema es commit faltante o campo fuera del UPDATE.
"""

import asyncio
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import sqlalchemy as sa
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from forge.etl.jira_client import JiraClient
from forge.etl.time_metrics import extract_time_metrics
from forge.etl.quality_metrics import extract_quality_metrics
from forge.services.engine.cp_calculator import calculate_cp, needs_approval

KEY = "YAP-811"
REAL_DB = Path(__file__).parent.parent.parent / "forge.db"
COPY_DB = Path("/tmp/diag_811.db")


def make_copy_engine():
    """Copia forge.db → /tmp/diag_811.db y crea engine apuntando a la copia."""
    shutil.copy2(REAL_DB, COPY_DB)
    print(f"  Copia: {REAL_DB} → {COPY_DB}")
    engine = create_engine(f"sqlite:///{COPY_DB}", echo=False)
    return engine


async def main() -> None:
    client = JiraClient()

    print(f"\n{'='*70}")
    print(f"PASO 4: WRITE INSTRUMENTADO en copia — {KEY}")
    print(f"{'='*70}")

    # ── Copia de la BD ────────────────────────────────────────────────────────
    print("\n[Setup] Creando copia temporal...")
    engine = make_copy_engine()
    Session = sessionmaker(bind=engine)
    session = Session()

    # ── Estado inicial en la COPIA ────────────────────────────────────────────
    row = session.execute(
        text("SELECT jira_key, complexity_size, cp, cp_approved_at FROM subtasks WHERE jira_key = :k"),
        {"k": KEY},
    ).one()
    print(f"\n[COPIA - ANTES]")
    print(f"  complexity_size = {row.complexity_size!r}")
    print(f"  cp              = {row.cp!r}")
    print(f"  cp_approved_at  = {row.cp_approved_at!r}")

    # ── Fetch desde Jira ──────────────────────────────────────────────────────
    print(f"\n[Fetch Jira] {KEY}...")
    resp = await client.search_issues(jql=f'issue = "{KEY}"', max_results=1, expand="changelog")
    issue = resp["issues"][0]
    fields = issue["fields"]

    # Replica exacta de _sync_subtask
    time_metrics = extract_time_metrics(issue)
    quality_metrics = extract_quality_metrics(issue)

    complexity_option = fields.get("customfield_10851")
    complexity_size: str | None = None
    if isinstance(complexity_option, dict):
        raw_value = complexity_option.get("value")
        if raw_value:
            complexity_size = raw_value.strip().upper()

    cp = calculate_cp(complexity_size) if complexity_size else None
    cp_approval_required = needs_approval(complexity_size) if complexity_size else False

    subtask_data = {
        "jira_key": KEY,
        "issue_type": fields.get("issuetype", {}).get("name", "Sub-task"),
        "summary": fields.get("summary", ""),
        "status": fields.get("status", {}).get("name", "Unknown"),
        "complexity_size": complexity_size,
        "cp": cp,
        "cp_approval_required": cp_approval_required,
        "last_synced_at": datetime.utcnow(),
        "raw_changelog": json.dumps(issue.get("changelog", {})),
        **time_metrics,
        **quality_metrics,
    }

    print(f"\n[Mapeo en memoria]")
    print(f"  complexity_size = {subtask_data.get('complexity_size')!r}")
    print(f"  cp = {subtask_data.get('cp')!r}")

    # ── Upsert sobre la COPIA ─────────────────────────────────────────────────
    print(f"\n[Write a /tmp/diag_811.db — guard inactivo (cp_approved_at IS NULL)]")

    # Fetch existing from copy (same logic as session.get)
    existing_row = session.execute(
        text("SELECT * FROM subtasks WHERE jira_key = :k"), {"k": KEY}
    ).mappings().one()

    # Apply all fields (same loop as sync_orchestrator)
    for k, v in subtask_data.items():
        if k == "jira_key":
            continue
        session.execute(
            text(f"UPDATE subtasks SET {k} = :{k} WHERE jira_key = :jk"),
            {k: v, "jk": KEY},
        )

    print(f"  UPDATE ejecutado para todos los campos de subtask_data")
    print(f"  complexity_size en el UPDATE = {subtask_data.get('complexity_size')!r}")

    # ── COMMIT EXPLÍCITO ──────────────────────────────────────────────────────
    session.commit()
    print(f"  session.commit() — EXPLÍCITO")

    # ── Verificar en la COPIA ─────────────────────────────────────────────────
    row_after = session.execute(
        text("SELECT complexity_size, cp FROM subtasks WHERE jira_key = :k"),
        {"k": KEY},
    ).one()
    print(f"\n[COPIA - DESPUÉS del commit]")
    print(f"  complexity_size = {row_after.complexity_size!r}")
    print(f"  cp              = {row_after.cp!r}")

    # ── Veredicto ─────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    if row_after.complexity_size == complexity_size:
        print(f"✅ Con commit explícito SÍ persiste — complexity_size = {row_after.complexity_size!r}")
        print("   CAUSA RAÍZ: el sync real pierde el commit, o el ORM no trackea el cambio.")
        print("   Patrón idéntico a WP-03b (flush sin commit).")
    else:
        print(f"❌ Aún NULL tras commit explícito — el campo no está en el UPDATE")
        print("   CAUSA RAÍZ: complexity_size no se escribe aunque esté en subtask_data")

    # ── Verificar que forge.db no fue tocado ─────────────────────────────────
    print(f"\n[Verificación: forge.db real intacto]")
    check_engine = create_engine(f"sqlite:///{REAL_DB}", echo=False)
    with check_engine.connect() as conn:
        real_val = conn.execute(
            text("SELECT complexity_size FROM subtasks WHERE jira_key = :k"), {"k": KEY}
        ).scalar()
    print(f"  forge.db complexity_size = {real_val!r}  ← debe seguir NULL")
    check_engine.dispose()

    session.close()
    engine.dispose()

    # Borrar copia
    COPY_DB.unlink(missing_ok=True)
    print(f"  /tmp/diag_811.db borrado ✓")


if __name__ == "__main__":
    asyncio.run(main())
