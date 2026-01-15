"""
Main CLI entry point for Facebook Auto-Poster
Supports multiple profiles for different Facebook accounts/campaigns
"""
import click
from rich.console import Console
from rich.table import Table

from ..utils.logger import setup_logger, get_logger
from ..utils.config import get_config, set_profile, get_current_profile, list_profiles
from ..data.storage import DataStore, LogStore

console = Console()
logger = setup_logger()


@click.group()
@click.option('--profile', '-p', default=None, help='Profile to use (for multi-account support)')
@click.pass_context
def cli(ctx, profile):
    """Facebook Auto-Poster - Automated group posting with scheduling"""
    # Set profile before initializing anything else
    if profile:
        set_profile(profile)
        console.print(f"[dim]Using profile: [cyan]{profile}[/cyan][/dim]")

    # Initialize context (profile-aware)
    ctx.ensure_object(dict)
    ctx.obj['profile'] = profile
    ctx.obj['data_store'] = DataStore()
    ctx.obj['log_store'] = LogStore()
    ctx.obj['config'] = get_config()


@cli.command()
@click.pass_context
def status(ctx):
    """Show system status and statistics"""
    profile = get_current_profile()
    if profile:
        console.print(f"\n[bold cyan]Facebook Auto-Poster Status[/bold cyan] [dim](profile: {profile})[/dim]\n")
    else:
        console.print("\n[bold cyan]Facebook Auto-Poster Status[/bold cyan]\n")

    # Get statistics from context
    data_store = ctx.obj['data_store']
    log_store = ctx.obj['log_store']

    groups = data_store.load_groups()
    texts = data_store.load_texts()
    jobs = data_store.load_jobs()

    # Statistics table
    stats_table = Table(show_header=False, box=None)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="green")

    stats_table.add_row("Total Groups", str(len(groups)))
    stats_table.add_row("Active Groups", str(len([g for g in groups if g.active])))
    stats_table.add_row("Text Templates", str(len(texts)))
    stats_table.add_row("Jobs Configured", str(len(jobs)))
    stats_table.add_row("Enabled Jobs", str(len([j for j in jobs if j.enabled])))

    console.print(stats_table)

    # Show available profiles
    profiles = list_profiles()
    if profiles:
        console.print(f"\n[bold]Available Profiles:[/bold] {', '.join(profiles)}")

    # Recent posting stats
    stats = log_store.get_success_rate(days=7)
    console.print(f"\n[bold]Last 7 Days:[/bold]")
    console.print(f"  Total Posts: {stats['total']}")
    console.print(f"  Successful: [green]{stats['successful']}[/green]")
    console.print(f"  Failed: [red]{stats['failed']}[/red]")
    if stats['total'] > 0:
        console.print(f"  Success Rate: [cyan]{stats['success_rate']:.1f}%[/cyan]")

    console.print()


@cli.command()
@click.option('--tail', '-n', default=20, help='Number of recent logs to show')
@click.pass_context
def logs(ctx, tail):
    """View recent posting logs"""
    log_store = ctx.obj['log_store']
    recent_logs = log_store.get_recent_logs(limit=tail)

    if not recent_logs:
        console.print("[yellow]No logs found[/yellow]")
        return

    table = Table(title=f"Recent Posting Logs (last {tail})")
    table.add_column("Time", style="cyan")
    table.add_column("City", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Group URL", overflow="fold", max_width=50)

    for log in recent_logs:
        status_style = "green" if log['status'] == 'success' else "red"
        table.add_row(
            log['timestamp'][:19],
            log['city'],
            f"[{status_style}]{log['status']}[/{status_style}]",
            log['group_url']
        )

    console.print(table)


@cli.command()
def version():
    """Show version information"""
    console.print("[bold cyan]Facebook Auto-Poster v1.0.0[/bold cyan]")
    console.print("Automated Facebook group posting with scheduling\n")


# Import command modules to register them (must be after cli is defined)
from . import groups, texts, jobs, migrate, profiles, telegram, web


if __name__ == '__main__':
    cli(obj={})
