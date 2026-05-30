"""CLI de Forge usando Typer."""

import asyncio
from datetime import date, datetime
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

from forge.core.config import get_settings
from forge.db.models.cycle import Cycle
from forge.db.models.player import Player
from forge.db.models.project import Project
from forge.db.models.sprint import Sprint  # DEPRECATED: solo para compatibilidad seed
from forge.db.session import SessionLocal
from forge.etl.jira_client import JiraClient
from forge.etl.sync_orchestrator import SyncOrchestrator

app = typer.Typer(help="Forge CLI - Comandos de gestión del sistema")
console = Console()

# backend/seed/  (4 niveles arriba desde cli.py: scripts → forge → src → backend)
SEED_DIR = Path(__file__).parent.parent.parent.parent / "seed"


@app.command()
def sync(
    jql: str = typer.Option(None, help="Query JQL personalizada"),
):
    """Sincronizar con Jira (UC-01)."""
    console.print("[bold blue]🔄 Iniciando sincronización con Jira...[/bold blue]")

    session = SessionLocal()
    try:
        orchestrator = SyncOrchestrator(session)
        stats = asyncio.run(orchestrator.sync_all(jql=jql))

        table = Table(title="Resultados de Sincronización")
        table.add_column("Tipo", style="cyan")
        table.add_column("Creados", style="green")
        table.add_column("Actualizados", style="yellow")

        table.add_row("Epics", str(stats["epics_created"]), str(stats["epics_updated"]))
        table.add_row("Stories", str(stats["stories_created"]), str(stats["stories_updated"]))
        table.add_row("Subtasks", str(stats["subtasks_created"]), str(stats["subtasks_updated"]))

        console.print(table)

        if stats.get("errors"):
            console.print(f"\n[bold red]⚠️  {len(stats['errors'])} errores:[/bold red]")
            for error in stats["errors"][:5]:
                console.print(f"  • {error}")

    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        raise typer.Exit(1)
    finally:
        session.close()


@app.command()
def test_jira():
    """Probar conexión a Jira."""
    console.print("[bold blue]🔌 Probando conexión a Jira...[/bold blue]")

    try:
        client = JiraClient()
        result = asyncio.run(client.test_connection())

        console.print("[bold green]✅ Conexión exitosa![/bold green]")
        console.print(f"Usuario: {result['user']}")
        console.print(f"Account ID: {result['account_id']}")
        console.print(f"Instancia: {result['instance']}")

    except Exception as e:
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def seed():
    """Cargar datos seed desde archivos YAML (players, sprints, proyectos)."""
    console.print("[bold blue]🌱 Cargando datos seed...[/bold blue]")
    console.print(f"  Directorio: {SEED_DIR}")

    session = SessionLocal()
    now = datetime.utcnow()
    totals: dict[str, int] = {"creados": 0, "actualizados": 0}

    try:
        _seed_projects(session, now, totals)
        _seed_players(session, now, totals)
        _seed_sprints(session, now, totals)
        _seed_engine_versions(session, now, totals)
        session.commit()

        console.print(
            f"\n[bold green]✅ Seed completado — "
            f"{totals['creados']} creados, {totals['actualizados']} actualizados[/bold green]"
        )

    except Exception as e:
        session.rollback()
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        raise typer.Exit(1)
    finally:
        session.close()


def _seed_projects(session, now: datetime, totals: dict) -> None:
    """Carga projects.yaml."""
    path = SEED_DIR / "projects.yaml"
    if not path.exists():
        console.print(f"  [yellow]⚠[/yellow]  projects.yaml no encontrado en {SEED_DIR}")
        return

    records = yaml.safe_load(path.read_text()) or []
    created = updated = 0
    for data in records:
        existing = session.get(Project, data["code"])
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            existing.updated_at = now
            updated += 1
        else:
            session.add(Project(**data, created_at=now, updated_at=now))
            created += 1

    totals["creados"] += created
    totals["actualizados"] += updated
    console.print(f"  [green]✓[/green] projects.yaml    — {created} creados, {updated} actualizados")


def _seed_players(session, now: datetime, totals: dict) -> None:
    """Carga players_yapsi.yaml. Hace upsert por jira_account_id."""
    path = SEED_DIR / "players_yapsi.yaml"
    if not path.exists():
        console.print(f"  [yellow]⚠[/yellow]  players_yapsi.yaml no encontrado en {SEED_DIR}")
        return

    records = yaml.safe_load(path.read_text()) or []
    created = updated = 0

    for data in records:
        jira_id = data.get("jira_account_id")
        if not jira_id:
            continue

        # Buscar por jira_account_id (no por PK autoincrement)
        from sqlalchemy import select
        stmt = select(Player).where(Player.jira_account_id == jira_id)
        existing = session.scalars(stmt).first()

        # Convertir campos de fecha si vienen como string
        for date_field in ("joined_at", "class_last_changed_at"):
            if data.get(date_field) and isinstance(data[date_field], str):
                data[date_field] = datetime.fromisoformat(data[date_field])

        # Eliminar nulls explícitos del YAML para no pisar defaults del modelo
        clean = {k: v for k, v in data.items() if v is not None}

        if existing:
            for k, v in clean.items():
                setattr(existing, k, v)
            existing.updated_at = now
            updated += 1
        else:
            session.add(Player(**clean, created_at=now, updated_at=now))
            created += 1

    totals["creados"] += created
    totals["actualizados"] += updated
    console.print(f"  [green]✓[/green] players_yapsi.yaml — {created} creados, {updated} actualizados")


def _seed_sprints(session, now: datetime, totals: dict) -> None:
    """Carga sprints.yaml. Hace upsert por name (único)."""
    path = SEED_DIR / "sprints.yaml"
    if not path.exists():
        console.print(f"  [yellow]⚠[/yellow]  sprints.yaml no encontrado en {SEED_DIR}")
        return

    records = yaml.safe_load(path.read_text()) or []
    created = updated = 0

    for data in records:
        name = data.get("name")
        if not name:
            continue

        from sqlalchemy import select
        stmt = select(Sprint).where(Sprint.name == name)
        existing = session.scalars(stmt).first()

        # Convertir fechas string → date
        for date_field in ("start_date", "end_date"):
            if isinstance(data.get(date_field), str):
                data[date_field] = date.fromisoformat(data[date_field])

        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            existing.updated_at = now
            updated += 1
        else:
            session.add(Sprint(**data, created_at=now, updated_at=now))
            created += 1

    totals["creados"] += created
    totals["actualizados"] += updated
    console.print(f"  [green]✓[/green] sprints.yaml      — {created} creados, {updated} actualizados")


def _seed_engine_versions(session, now: datetime, totals: dict) -> None:
    """Carga engine_versions.yaml. Upsert por version_tag."""
    from forge.db.models.engine_version import EngineVersion
    from sqlalchemy import select

    path = SEED_DIR / "engine_versions.yaml"
    if not path.exists():
        console.print(f"  [yellow]⚠[/yellow]  engine_versions.yaml no encontrado en {SEED_DIR}")
        return

    records = yaml.safe_load(path.read_text()) or []
    created = updated = 0

    for data in records:
        version_tag = data.get("version_tag")
        if not version_tag:
            continue

        stmt = select(EngineVersion).where(EngineVersion.version_tag == version_tag)
        existing = session.scalars(stmt).first()

        ev_data = {
            "version_tag": version_tag,
            "description": data.get("description"),
            "is_active": data.get("is_active", False),
            "rules_snapshot": data.get("rules_snapshot"),
        }
        if data.get("is_active"):
            ev_data["activated_at"] = now

        if existing:
            for k, v in ev_data.items():
                setattr(existing, k, v)
            updated += 1
        else:
            session.add(EngineVersion(**ev_data))
            created += 1

    totals["creados"] += created
    totals["actualizados"] += updated
    console.print(
        f"  [green]✓[/green] engine_versions.yaml — {created} creados, {updated} actualizados"
    )


@app.command()
def recalc(
    cycle_id: int = typer.Option(None, help="Recalcular solo este ciclo (default: activo)"),
    force: bool = typer.Option(False, help="Forzar recálculo aunque engine_version no cambió"),
    system_player: str = typer.Option(
        "PM", help="Área del player que actúa como sistema para auto-debuffs"
    ),
):
    """Recalcular SP de todas las subtasks de un ciclo (CP×multiplicadores + debuffs)."""
    from sqlalchemy import select
    from forge.services.engine import recalculate_cycle

    console.print("[bold blue]⚙️  Recalculando motor JPDS v2.0...[/bold blue]")
    session = SessionLocal()
    try:
        # Resolver ciclo
        if cycle_id is None:
            stmt = select(Cycle).where(Cycle.status == "active").limit(1)
            cycle = session.scalars(stmt).first()
            if cycle is None:
                console.print("[red]❌ No hay ciclo activo y no se pasó --cycle-id[/red]")
                raise typer.Exit(1)
            cycle_id = cycle.id
            console.print(f"  Ciclo activo detectado: [cyan]{cycle.name}[/cyan] (id={cycle_id})")
        else:
            cycle = session.get(Cycle, cycle_id)
            if cycle is None:
                console.print(f"[red]❌ Cycle id={cycle_id} no encontrado[/red]")
                raise typer.Exit(1)
            console.print(f"  Ciclo: [cyan]{cycle.name}[/cyan]")

        # Resolver system_player (necesario para applied_by en SpAdjustments)
        stmt = select(Player).where(Player.area == system_player).limit(1)
        system_p = session.scalars(stmt).first()
        if system_p is None:
            console.print(f"[red]❌ No hay player con area='{system_player}' para system_player[/red]")
            raise typer.Exit(1)
        console.print(f"  System player: [cyan]{system_p.display_name}[/cyan] (id={system_p.id})")
        console.print(f"  Force: [cyan]{force}[/cyan]")
        console.print()

        # Ejecutar
        stats = recalculate_cycle(session, cycle_id, system_p.id, force=force)
        session.commit()

        # Mostrar resultados
        table = Table(title=f"Recalc Engine — {cycle.name}")
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="white", justify="right")
        table.add_row("Total subtasks", str(stats["total"]))
        table.add_row("Procesadas", str(stats["processed"]))
        table.add_row("Omitidas (sin cambios)", str(stats["skipped"]))
        table.add_row("Errores", str(stats["errors"]))
        table.add_row("SP total acumulado", f"{float(stats['sp_total']):.2f}")
        console.print(table)
        console.print("[bold green]✅ Recalc completado[/bold green]")

    except Exception as e:
        session.rollback()
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        raise typer.Exit(1)
    finally:
        session.close()


@app.command()
def engine_demo(
    sample_size: int = typer.Option(10, help="Cuántas subtasks de ejemplo asignar"),
    cycle_id: int = typer.Option(None, help="Ciclo a samplear (default: activo)"),
    dry_run: bool = typer.Option(False, help="No persiste cambios, solo simula"),
):
    """
    Asigna tallas demo a una muestra de subtasks y recalcula. Útil para validar el engine.

    Heurística de asignación (basada en ct_biz_hours):
      < 4h    → XS
      4-8h    → S
      8-16h   → M
      16-32h  → L
      32-56h  → XL
      > 56h   → XXL (rechazada)

    Si la subtask no tiene ct_biz_hours, se asigna M por defecto.
    """
    from sqlalchemy import select
    from datetime import date as _date, datetime as _dt

    from forge.services.engine import (
        calculate_cp,
        calc_all_multipliers,
        calculate_sp,
        detect_all,
        recalculate_subtask,
    )

    console.print("[bold blue]🧪 Engine Demo — asignación de tallas + recálculo[/bold blue]")
    session = SessionLocal()
    try:
        # Resolver ciclo
        if cycle_id is None:
            stmt = select(Cycle).where(Cycle.status == "active").limit(1)
            cycle = session.scalars(stmt).first()
            if cycle is None:
                console.print("[red]❌ No hay ciclo activo[/red]")
                raise typer.Exit(1)
            cycle_id = cycle.id

        # Sample subtasks del ciclo
        from forge.db.models.subtask import Subtask

        stmt = (
            select(Subtask)
            .where(Subtask.cycle_id == cycle_id)
            .where(Subtask.status == "Done")
            .where(Subtask.assignee_player_id.isnot(None))
            .limit(sample_size)
        )
        subtasks = list(session.scalars(stmt))

        if not subtasks:
            console.print("[yellow]⚠ No hay subtasks Done con assignee en este sprint[/yellow]")
            raise typer.Exit(0)

        # System player (PM)
        system_p = session.scalars(select(Player).where(Player.area == "PM").limit(1)).first()
        if system_p is None:
            console.print("[red]❌ No hay player PM[/red]")
            raise typer.Exit(1)

        # Heurística de tallas
        def infer_size(ct: float | None) -> str:
            if ct is None:
                return "M"
            if ct < 4:
                return "XS"
            if ct < 8:
                return "S"
            if ct < 16:
                return "M"
            if ct < 32:
                return "L"
            if ct < 56:
                return "XL"
            return "XXL"

        # Asignar tallas
        console.print(f"\n[bold]Asignando tallas a {len(subtasks)} subtasks...[/bold]")
        assignment_table = Table(title="Asignación de tallas")
        assignment_table.add_column("Subtask", style="cyan")
        assignment_table.add_column("CT (h)", justify="right")
        assignment_table.add_column("Talla", style="yellow")
        assignment_table.add_column("CP", justify="right", style="green")

        for st in subtasks:
            size = infer_size(st.ct_biz_hours)
            cp = calculate_cp(size)
            assignment_table.add_row(
                st.jira_key,
                f"{st.ct_biz_hours:.1f}" if st.ct_biz_hours else "—",
                size,
                str(cp),
            )
            if not dry_run:
                st.complexity_size = size
                st.cp = cp
                # Marcar como aprobado (demo: PM aprueba inmediato)
                st.cp_approved_at = _dt.utcnow()
                st.cp_approved_by = system_p.id

        console.print(assignment_table)

        if dry_run:
            console.print("\n[yellow]⚠ Dry run — no se persistió nada[/yellow]")
            return

        session.flush()

        # Recalcular cada una y mostrar componentes
        console.print(f"\n[bold]Recalculando SP para cada subtask...[/bold]")
        sp_table = Table(title="Resultado del Engine")
        sp_table.add_column("Subtask", style="cyan")
        sp_table.add_column("Player", style="white")
        sp_table.add_column("CP", justify="right", style="green")
        sp_table.add_column("M_cal", justify="right")
        sp_table.add_column("M_efic", justify="right")
        sp_table.add_column("M_dif", justify="right")
        sp_table.add_column("SP base", justify="right", style="yellow")
        sp_table.add_column("Debuffs", justify="right", style="red")
        sp_table.add_column("SP final", justify="right", style="bold green")

        total_sp = 0.0
        for st in subtasks:
            components = recalculate_subtask(
                session, st.jira_key, system_p.id, force=True
            )
            player = session.get(Player, st.assignee_player_id)
            player_name = player.display_name.split()[0] if player else "—"
            total_sp += components.sp_final
            sp_table.add_row(
                st.jira_key,
                player_name,
                str(st.cp),
                f"{components.m_calidad:.2f}",
                f"{components.m_eficiencia:.2f}",
                f"{components.m_dificultad:.2f}",
                f"{components.sp_base:.2f}",
                f"-{components.sp_penalty:.2f}" if components.sp_penalty else "0",
                f"{components.sp_final:.2f}",
            )

        session.commit()
        console.print(sp_table)
        console.print(f"\n[bold green]✅ Total SP del sample: {total_sp:.2f}[/bold green]")

        # Mostrar debuffs creados
        from forge.db.models.sp_adjustment import SpAdjustment
        debuff_rows = session.execute(
            select(SpAdjustment.catalog_code, SpAdjustment.subtask_key, SpAdjustment.amount_sp, SpAdjustment.reason)
            .where(SpAdjustment.subtask_key.in_([s.jira_key for s in subtasks]))
        ).fetchall()

        if debuff_rows:
            console.print(f"\n[bold]Debuffs auto-detectados ({len(debuff_rows)}):[/bold]")
            db_table = Table()
            db_table.add_column("Subtask", style="cyan")
            db_table.add_column("Código", style="red")
            db_table.add_column("Penalty SP", justify="right")
            db_table.add_column("Razón")
            for code, key, amount, reason in debuff_rows:
                db_table.add_row(key, code, f"-{amount:.2f}", reason[:60] + "...")
            console.print(db_table)
        else:
            console.print("\n[dim]No se detectaron debuffs en este sample.[/dim]")

    except Exception as e:
        session.rollback()
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)
    finally:
        session.close()


@app.command()
def cycle_generate(
    weeks: int = typer.Option(12, help="Cantidad de ciclos a generar hacia adelante"),
    start: str = typer.Option(
        None,
        help="Fecha de inicio del primer ciclo (YYYY-MM-DD, debe ser lunes). "
        "Por defecto: lunes de la semana siguiente al último ciclo registrado (o hoy).",
    ),
    dry_run: bool = typer.Option(False, help="Mostrar sin persistir"),
):
    """Generar ciclos semanales (lunes a viernes) con nombre Ciclo YYYY-WWW. Idempotente."""
    from datetime import date as _date, timedelta
    from sqlalchemy import select, func

    console.print(f"[bold blue]📅 Generando {weeks} ciclos semanales...[/bold blue]")
    session = SessionLocal()
    try:
        # Determinar fecha de inicio
        if start:
            first_start = _date.fromisoformat(start)
            if first_start.weekday() != 0:
                console.print("[red]❌ La fecha de inicio debe ser un lunes (weekday=0)[/red]")
                raise typer.Exit(1)
        else:
            # Buscar el último ciclo y arrancar la semana siguiente
            last_end = session.scalar(select(func.max(Cycle.end_date)))
            if last_end:
                first_start = last_end + timedelta(days=3)  # lunes siguiente (fin = viernes)
                while first_start.weekday() != 0:
                    first_start += timedelta(days=1)
            else:
                today = _date.today()
                first_start = today - timedelta(days=today.weekday())

        table = Table(title="Ciclos a crear")
        table.add_column("Nombre", style="cyan")
        table.add_column("Inicio", style="white")
        table.add_column("Fin (Vie)", style="white")
        table.add_column("Estado", style="yellow")

        created = skipped = 0
        current = first_start
        for _ in range(weeks):
            end = current + timedelta(days=4)  # lunes → viernes (5 días)
            iso_year, iso_week, _ = current.isocalendar()
            name = f"Ciclo {iso_year}-W{iso_week:02d}"

            stmt = select(Cycle).where(Cycle.iso_year == iso_year, Cycle.iso_week == iso_week)
            existing = session.scalars(stmt).first()

            if existing:
                table.add_row(name, str(current), str(end), "⏭ ya existe")
                skipped += 1
            else:
                table.add_row(name, str(current), str(end), "✅ nuevo")
                if not dry_run:
                    session.add(
                        Cycle(
                            name=name,
                            iso_year=iso_year,
                            iso_week=iso_week,
                            start_date=current,
                            end_date=end,
                            status="planned",
                        )
                    )
                created += 1

            current += timedelta(days=7)

        console.print(table)

        if dry_run:
            console.print("\n[yellow]⚠ Dry run — no se persistió nada[/yellow]")
        else:
            session.commit()
            console.print(
                f"\n[bold green]✅ Listo — {created} creados, {skipped} ya existían[/bold green]"
            )

    except Exception as e:
        session.rollback()
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        raise typer.Exit(1)
    finally:
        session.close()


@app.command()
def cycles_list(
    limit: int = typer.Option(10, help="Número de ciclos a mostrar"),
):
    """Listar ciclos recientes."""
    from sqlalchemy import select

    session = SessionLocal()
    try:
        stmt = select(Cycle).order_by(Cycle.start_date.desc()).limit(limit)
        cycles = list(session.scalars(stmt))

        table = Table(title=f"Ciclos recientes (últimos {limit})")
        table.add_column("ID", style="dim")
        table.add_column("Nombre", style="cyan")
        table.add_column("Inicio", style="white")
        table.add_column("Fin", style="white")
        table.add_column("Status", style="yellow")

        for c in cycles:
            table.add_row(str(c.id), c.name, str(c.start_date), str(c.end_date), c.status)

        console.print(table)
    finally:
        session.close()


@app.command()
def sprint_generate(
    weeks: int = typer.Option(12, help="[DEPRECATED] Usar cycle-generate"),
    start: str = typer.Option(None),
    dry_run: bool = typer.Option(False),
):
    """[DEPRECATED] Alias de cycle-generate. Usar forge cycle-generate en su lugar."""
    console.print("[yellow]⚠ sprint-generate está deprecado. Usa forge cycle-generate[/yellow]")
    cycle_generate(weeks=weeks, start=start, dry_run=dry_run)


@app.command()
def shell():
    """Abrir IPython con sesión de DB cargada."""
    try:
        import IPython

        from forge.db.models.subtask import Subtask
        session = SessionLocal()
        console.print("[bold green]Shell Forge — sesión DB disponible como `session`[/bold green]")
        IPython.embed(
            header="Forge Shell\nVariables: session, Player, Cycle, Subtask, Project",
            user_ns={
                "session": session,
                "Player": Player,
                "Cycle": Cycle,
                "Subtask": Subtask,
                "Project": Project,
            },
        )
    except ImportError:
        console.print("[red]IPython no instalado. Agrega ipython a dev deps.[/red]")
    finally:
        session.close()  # noqa: F821  (session defined in try block)


@app.command()
def info():
    """Mostrar información del sistema."""
    settings = get_settings()

    table = Table(title="Forge System Info")
    table.add_column("Config", style="cyan")
    table.add_column("Valor", style="white")

    table.add_row("Entorno", settings.app_env)
    table.add_row("Versión", settings.app_version)
    table.add_row("Database", settings.database_url)
    table.add_row("Jira Instance", settings.jira_instance_url)
    table.add_row("Engine Version", settings.default_engine_version)
    table.add_row("Seed Dir", str(SEED_DIR))

    console.print(table)


if __name__ == "__main__":
    app()
