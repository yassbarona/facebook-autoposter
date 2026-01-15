"""
Web Dashboard CLI commands
"""
import click
from rich.console import Console

from .main import cli

console = Console()


@cli.group()
def web():
    """Web dashboard commands"""
    pass


@web.command("start")
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, help="Port to run on")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def start(host: str, port: int, reload: bool):
    """Start the web dashboard server"""
    import uvicorn

    console.print(f"\n[bold cyan]Starting FB Auto-Poster Dashboard...[/bold cyan]")
    console.print(f"Access at: [green]http://{host}:{port}[/green]")
    console.print(f"Default password: [yellow]admin[/yellow] (set DASHBOARD_PASSWORD to change)")
    console.print()

    uvicorn.run(
        "fbposter.web.app:app",
        host=host,
        port=port,
        reload=reload
    )


@web.command("info")
def info():
    """Show web dashboard information"""
    import os

    password = os.getenv("DASHBOARD_PASSWORD", "admin")
    secret_key = os.getenv("DASHBOARD_SECRET_KEY", "change-this-secret-key-in-production")

    console.print("\n[bold cyan]Web Dashboard Configuration[/bold cyan]")
    console.print("=" * 40)
    console.print()
    console.print(f"Password: {'[yellow](default: admin)[/yellow]' if password == 'admin' else '[green](custom)[/green]'}")
    console.print(f"Secret Key: {'[red](default - CHANGE IN PRODUCTION!)[/red]' if 'change-this' in secret_key else '[green](custom)[/green]'}")
    console.print()
    console.print("[bold]Environment Variables:[/bold]")
    console.print("  DASHBOARD_PASSWORD - Set dashboard login password")
    console.print("  DASHBOARD_SECRET_KEY - Set session secret key")
    console.print()
    console.print("[bold]Start the dashboard with:[/bold]")
    console.print("  fbposter web start")
    console.print("  fbposter web start --port 8080")
    console.print("  fbposter web start --reload  [dim]# for development[/dim]")
    console.print()
