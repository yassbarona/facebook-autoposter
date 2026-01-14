"""
CLI commands for managing posting jobs
"""
import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.panel import Panel

from ..data.models import Job
from ..data.storage import DataStore
from ..core.browser import Browser
from ..core.poster import run_job
from .main import cli

console = Console()


@cli.group()
def jobs():
    """Manage posting jobs"""
    pass


@jobs.command('list')
@click.option('--all', 'show_all', is_flag=True, help='Show disabled jobs too')
def list_jobs(show_all):
    """List all posting jobs"""
    data_store = DataStore()
    all_jobs = data_store.load_jobs()

    if not show_all:
        all_jobs = [j for j in all_jobs if j.enabled]

    if not all_jobs:
        console.print("[yellow]No jobs found[/yellow]")
        return

    table = Table(title="Posting Jobs")
    table.add_column("ID", style="dim", width=8)
    table.add_column("Name", style="cyan")
    table.add_column("Text", style="magenta")
    table.add_column("Cities", overflow="fold", max_width=30)
    table.add_column("Schedule")
    table.add_column("Enabled", justify="center", width=8)

    for job in all_jobs:
        # Get text name
        text = data_store.get_text(job.text_id)
        text_name = text.name if text else "[dim]unknown[/dim]"

        # Get cities
        cities = job.group_filters.get('cities', [])
        cities_str = ', '.join(cities) if cities else 'all'

        # Enabled status
        enabled_icon = "✓" if job.enabled else "✗"
        enabled_style = "green" if job.enabled else "red"

        table.add_row(
            job.id[:8],
            job.name,
            text_name,
            cities_str,
            job.schedule,
            f"[{enabled_style}]{enabled_icon}[/{enabled_style}]"
        )

    console.print(table)
    console.print(f"\n[bold]Total:[/bold] {len(all_jobs)} jobs")


@jobs.command('create')
def create_job():
    """Create a new posting job (interactive)"""
    data_store = DataStore()

    console.print("\n[bold cyan]Creating new posting job[/bold cyan]")
    console.print("━" * 50 + "\n")

    # Job name
    name = Prompt.ask("[bold]Job name[/bold]")

    # Select text template
    texts = data_store.load_texts()
    if not texts:
        console.print("[red]Error:[/red] No text templates found. Create one first with 'fbposter texts add'")
        return

    console.print("\n[bold]Select text template:[/bold]")
    for i, text in enumerate(texts, 1):
        console.print(f"  {i}. {text.name}")

    text_idx = IntPrompt.ask("Choice", default=1) - 1
    if text_idx < 0 or text_idx >= len(texts):
        console.print("[red]Invalid choice[/red]")
        return
    selected_text = texts[text_idx]

    # Select cities
    groups = data_store.load_groups()
    all_cities = sorted(set(g.city for g in groups))

    if not all_cities:
        console.print("[red]Error:[/red] No groups found. Add groups first with 'fbposter groups add'")
        return

    console.print(f"\n[bold]Available cities:[/bold] {', '.join(all_cities)}")
    cities_input = Prompt.ask("Select cities (comma-separated, or 'all')", default="all")

    if cities_input.lower() == 'all':
        selected_cities = all_cities
    else:
        selected_cities = [c.strip() for c in cities_input.split(',')]

    # Count affected groups
    matching_groups = [g for g in groups if g.city in selected_cities and g.active]
    console.print(f"\n[dim]This will post to {len(matching_groups)} active groups[/dim]")

    # Schedule
    console.print("\n[bold]Schedule:[/bold]")
    console.print("  1. Daily at specific time (e.g., 08:00)")
    console.print("  2. Manual (run on demand)")

    schedule_type = IntPrompt.ask("Choice", default=1)

    if schedule_type == 1:
        time = Prompt.ask("Time (HH:MM, 24-hour format)", default="08:00")
        schedule = f"0 {time.split(':')[1]} {time.split(':')[0]} * * *"  # Cron format
    else:
        schedule = "manual"

    # Summary
    console.print("\n[bold cyan]Summary:[/bold cyan]")
    console.print(f"  Name: {name}")
    console.print(f"  Text: {selected_text.name}")
    console.print(f"  Cities: {', '.join(selected_cities)}")
    console.print(f"  Groups: {len(matching_groups)} active groups")
    console.print(f"  Schedule: {schedule}")

    if not Confirm.ask("\n[bold]Save job?[/bold]", default=True):
        console.print("[yellow]Cancelled[/yellow]")
        return

    # Create job
    try:
        job = Job(
            name=name,
            text_id=selected_text.id,
            group_filters={
                'cities': selected_cities,
                'active_only': True
            },
            schedule=schedule,
            enabled=True
        )

        data_store.add_job(job)

        console.print(f"\n[green]✓[/green] Job created: [cyan]{job.id}[/cyan]")

        if schedule != "manual":
            console.print(f"\n[bold]To enable systemd scheduling:[/bold]")
            console.print(f"  sudo systemctl enable fbposter@{job.id}.timer")
            console.print(f"  sudo systemctl start fbposter@{job.id}.timer")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")


@jobs.command('show')
@click.argument('job_id')
def show_job(job_id):
    """Show job details"""
    data_store = DataStore()

    job = data_store.get_job(job_id)
    if not job:
        console.print(f"[red]Error:[/red] Job not found: {job_id}")
        return

    # Get text
    text = data_store.get_text(job.text_id)
    text_name = text.name if text else "[dim]unknown[/dim]"

    # Get groups
    groups = data_store.get_groups_for_job(job)

    console.print(f"\n[bold cyan]{job.name}[/bold cyan]")
    console.print(f"[dim]ID: {job.id}[/dim]\n")

    info = [
        ("Text Template", text_name),
        ("Cities", ', '.join(job.group_filters.get('cities', []))),
        ("Active Groups", str(len(groups))),
        ("Schedule", job.schedule),
        ("Enabled", "Yes" if job.enabled else "No"),
    ]

    if job.last_run:
        info.append(("Last Run", job.last_run.strftime("%Y-%m-%d %H:%M:%S")))

    for key, value in info:
        console.print(f"[bold]{key}:[/bold] {value}")

    console.print()


@jobs.command('toggle')
@click.argument('job_id')
def toggle_job(job_id):
    """Toggle enabled/disabled status of a job"""
    data_store = DataStore()

    job = data_store.get_job(job_id)
    if not job:
        console.print(f"[red]Error:[/red] Job not found: {job_id}")
        return

    job.enabled = not job.enabled
    data_store.update_job(job)

    status = "[green]enabled[/green]" if job.enabled else "[red]disabled[/red]"
    console.print(f"[green]✓[/green] Job is now {status}")


@jobs.command('remove')
@click.argument('job_id')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
def remove_job(job_id, yes):
    """Remove a job"""
    data_store = DataStore()

    job = data_store.get_job(job_id)
    if not job:
        console.print(f"[red]Error:[/red] Job not found: {job_id}")
        return

    if not yes:
        console.print(f"\n[yellow]About to delete:[/yellow]")
        console.print(f"  Name: {job.name}")
        if not Confirm.ask("\nAre you sure?", default=False):
            console.print("[yellow]Cancelled[/yellow]")
            return

    if data_store.remove_job(job_id):
        console.print(f"[green]✓[/green] Job removed successfully")
        console.print(f"\n[dim]Note: Don't forget to disable the systemd timer:[/dim]")
        console.print(f"  sudo systemctl disable fbposter@{job_id}.timer")
        console.print(f"  sudo systemctl stop fbposter@{job_id}.timer")
    else:
        console.print(f"[red]Error:[/red] Failed to remove job")


@cli.command('run')
@click.argument('job_id')
@click.option('--dry-run', is_flag=True, help='Simulate without actually posting')
@click.option('--headless/--no-headless', default=True, help='Run browser in headless mode')
def run_job_command(job_id, dry_run, headless):
    """Run a posting job"""
    data_store = DataStore()

    job = data_store.get_job(job_id)
    if not job:
        console.print(f"[red]Error:[/red] Job not found: {job_id}")
        return

    if not job.enabled:
        console.print(f"[yellow]Warning:[/yellow] Job is disabled")
        if not Confirm.ask("Run anyway?", default=False):
            return

    console.print(f"\n[bold cyan]Running job:[/bold cyan] {job.name}")
    if dry_run:
        console.print("[yellow](DRY RUN - not actually posting)[/yellow]")

    try:
        with Browser(headless=headless) as browser:
            results = run_job(job, browser, data_store, dry_run=dry_run)

            # Display results
            console.print(f"\n[bold]Results:[/bold]")
            console.print(f"  Total groups: {results['total']}")
            console.print(f"  [green]Successful: {results['successful']}[/green]")
            console.print(f"  [red]Failed: {results['failed']}[/red]")
            if results['skipped'] > 0:
                console.print(f"  [yellow]Skipped: {results['skipped']}[/yellow]")

            if results['errors']:
                console.print(f"\n[bold red]Errors:[/bold red]")
                for error in results['errors'][:5]:  # Show first 5 errors
                    console.print(f"  • {error}")

    except Exception as e:
        console.print(f"\n[red]Error running job:[/red] {e}")
        raise
