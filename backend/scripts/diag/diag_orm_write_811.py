"""Prueba el path ORM exacto de _sync_subtask sobre copia.

Usa session.get() + setattr() + commit() — idéntico al sync real.
Verifica si SQLAlchemy trackea el cambio y lo persiste.
"""

import asyncio
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import os
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/diag_orm_811.db")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from forge.db.models.subtask import Subtask
from forge.etl.jira_client import JiraClient
from forge.etl.time_metrics import extract_time_metrics
from forge.etl.quality_metrics import extract_quality_metrics
from forge.services.engine.cp_calculator import calculate_cp, needs_approval

KEY = "YAP-811"
REAL_DB = Path(__file__).parent.parent.parent / "forge.db"
COPY_DB = Path("/tmp/diag_orm_811.db")


async def main() -> None:
    # ── Copia ────────────────────────────────────────────────────────────────
    shutil.copy2(REAL_DB, COPY_DB)
    engine = create_engine(f"sqlite:///{COPY_DB}", echo=False)
    SessionCls = sessionmaker(bind=engine)
    session = SessionCls()

    print(f"\n{'='*70}")
    print(f"ORM PATH EXACTO (setattr + commit) — {KEY} en /tmp/diag_orm_811.db")
    print(f"{'='*70}")

    # ── Estado inicial ────────────────────────────────────────────────────────
    existing = session.get(Subtask, KEY)
    print(f"\n[ANTES] complexity_size={existing.complexity_size!r}  cp={existing.cp!r}")
    print(f"  cp_approved_at = {existing.cp_approved_at!r}")
    print(f"  → guard activo: {existing.cp_approved_at is not None}")

    # ── Fetch Jira ────────────────────────────────────────────────────────────
    client = JiraClient()
    resp = await client.search_issues(jql=f'issue = "{KEY}"', max_results=1, expand="changelog")
    issue = resp["issues"][0]
    fields = issue["fields"]

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
        **time_metrics,
        **quality_metrics,
    }

    print(f"\n[Fetch] complexity_size en memoria = {complexity_size!r}  cp = {cp!r}")

    # ── Replica EXACTA de _sync_subtask ──────────────────────────────────────
    if existing.cp_approved_at is not None:
        incoming_cp = subtask_data.pop("cp", None)
        incoming_size = subtask_data.pop("complexity_size", None)
        subtask_data.pop("cp_approval_required", None)
        print(f"  ⚠️  Guard activo — popped complexity_size = {incoming_size!r}")
    else:
        print(f"  Guard inactivo")

    print(f"\n[ORM setattr loop]")
    for k, v in subtask_data.items():
        setattr(existing, k, v)

    # Inspect SQLAlchemy dirty state BEFORE commit
    from sqlalchemy import inspect as sa_inspect
    insp = sa_inspect(existing)
    attrs_modified = {k: v for k, v in insp.attrs.items()
                      if insp.attrs[k].history.has_changes()}
    print(f"  Attrs marcados dirty por SQLAlchemy: {list(attrs_modified.keys())[:10]}")
    if "complexity_size" in attrs_modified:
        hist = insp.attrs["complexity_size"].history
        print(f"  complexity_size history: added={hist.added}  deleted={hist.deleted}")
    else:
        print(f"  ⚠️  'complexity_size' NO está en dirty attrs — SQLAlchemy no lo trackeará!")

    # ── Commit ────────────────────────────────────────────────────────────────
    session.commit()
    print(f"  → session.commit() ejecutado")

    # ── Resultado ─────────────────────────────────────────────────────────────
    # New session to avoid identity map cache
    session2 = SessionCls()
    row_after = session2.execute(
        text("SELECT complexity_size, cp FROM subtasks WHERE jira_key = :k"),
        {"k": KEY},
    ).one()
    print(f"\n[DESPUÉS del commit — sesión nueva]")
    print(f"  complexity_size = {row_after.complexity_size!r}")
    print(f"  cp              = {row_after.cp!r}")

    print(f"\n{'='*70}")
    if row_after.complexity_size == complexity_size:
        print(f"✅ ORM setattr + commit SÍ persiste: complexity_size = {row_after.complexity_size!r}")
        print("   → El bug NO es que SQLAlchemy no persista — es algo del sync real.")
        print("   → Hipótesis: el sync real corre sobre instancias ya expiradas / identity map.")
    else:
        print(f"❌ ORM setattr + commit NO persiste — complexity_size sigue NULL")
        if "complexity_size" not in attrs_modified:
            print("   CAUSA: SQLAlchemy no marcó complexity_size como dirty")
            print("   → El campo se setea pero el ORM cree que no cambió (None→None o tipo mismatch)")

    # forge.db intacto
    check_engine = create_engine(f"sqlite:///{REAL_DB}", echo=False)
    with check_engine.connect() as conn:
        real_val = conn.execute(
            text("SELECT complexity_size FROM subtasks WHERE jira_key = :k"), {"k": KEY}
        ).scalar()
    print(f"\nforge.db real intacto: complexity_size = {real_val!r} (debe ser NULL)")
    check_engine.dispose()

    session.close()
    session2.close()
    engine.dispose()
    COPY_DB.unlink(missing_ok=True)
    print(f"/tmp/diag_orm_811.db borrado ✓")


if __name__ == "__main__":
    asyncio.run(main())
