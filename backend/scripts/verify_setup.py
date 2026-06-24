"""Script para verificar que todo está configurado correctamente."""

import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()


def check_env_file():
    """Verificar que existe .env."""
    env_path = Path(".env")
    if not env_path.exists():
        console.print("[red]❌ Archivo .env no encontrado[/red]")
        console.print("   Ejecuta: cp .env.example .env")
        return False
    console.print("[green]✅ Archivo .env encontrado[/green]")
    return True


def check_database():
    """Verificar que la BD está inicializada."""
    try:
        from sqlalchemy import text

        from forge.db.session import engine

        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1"))
            if result.fetchone():
                console.print("[green]✅ Base de datos inicializada[/green]")
                return True
            else:
                console.print("[yellow]⚠️  BD vacía, ejecuta: alembic upgrade head[/yellow]")
                return False
    except Exception as e:
        console.print(f"[red]❌ Error con BD: {e}[/red]")
        return False


def check_jira_config():
    """Verificar configuración de Jira."""
    try:
        from forge.core.config import get_settings

        settings = get_settings()

        if "your-" in settings.jira_api_token or "REPLACE" in settings.jira_api_token:
            console.print("[yellow]⚠️  API token de Jira no configurado[/yellow]")
            console.print(
                "   Genera uno en: https://id.atlassian.com/manage-profile/security/api-tokens"
            )
            return False

        console.print("[green]✅ Configuración de Jira encontrada[/green]")
        return True
    except Exception as e:
        console.print(f"[red]❌ Error cargando config: {e}[/red]")
        return False


def main():
    """Verificación completa del setup."""
    console.print("\n[bold blue]🔍 Verificando setup de Forge...[/bold blue]\n")

    checks = [
        ("Archivo .env", check_env_file()),
        ("Base de datos", check_database()),
        ("Configuración Jira", check_jira_config()),
    ]

    # Resumen
    table = Table(title="Estado del Setup")
    table.add_column("Check", style="cyan")
    table.add_column("Estado", style="white")

    for name, passed in checks:
        status = "[green]✅ OK[/green]" if passed else "[red]❌ Falta[/red]"
        table.add_row(name, status)

    console.print(table)

    if all(passed for _, passed in checks):
        console.print("\n[bold green]🎉 Todo listo! Ejecuta:[/bold green]")
        console.print("   [cyan]uv run forge test-jira[/cyan]")
        return 0
    else:
        console.print("\n[bold yellow]⚠️  Completa los pasos faltantes[/bold yellow]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
