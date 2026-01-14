"""
Profile management commands for Facebook Auto-Poster
Allows managing multiple profiles for different Facebook accounts/campaigns
"""
import click
import shutil
from pathlib import Path
from rich.console import Console
from rich.table import Table

from ..utils.config import get_profiles_dir, get_profile_dir, list_profiles
from .main import cli

console = Console()


@cli.group()
def profiles():
    """Manage profiles for multi-account support"""
    pass


@profiles.command(name='list')
def list_cmd():
    """List all available profiles"""
    profile_names = list_profiles()

    if not profile_names:
        console.print("[yellow]No profiles found.[/yellow]")
        console.print("\nCreate a profile with: [cyan]fbposter profiles create <name>[/cyan]")
        console.print("Or use existing data without profiles (default mode).")
        return

    table = Table(title="Available Profiles")
    table.add_column("Profile Name", style="cyan")
    table.add_column("Groups", style="green")
    table.add_column("Texts", style="green")
    table.add_column("Jobs", style="green")
    table.add_column("Has Chrome Profile", style="yellow")

    for name in profile_names:
        profile_dir = get_profile_dir(name)

        # Count items in each file
        groups_file = profile_dir / "groups.json"
        texts_file = profile_dir / "texts.json"
        jobs_file = profile_dir / "jobs.json"
        chrome_dir = profile_dir / "chrome-profile"

        groups_count = _count_json_items(groups_file)
        texts_count = _count_json_items(texts_file)
        jobs_count = _count_json_items(jobs_file)
        has_chrome = "Yes" if chrome_dir.exists() else "No"

        table.add_row(name, str(groups_count), str(texts_count), str(jobs_count), has_chrome)

    console.print(table)
    console.print("\n[dim]Use: fbposter --profile <name> <command>[/dim]")


@profiles.command()
@click.argument('name')
def create(name):
    """Create a new profile"""
    profile_dir = get_profile_dir(name)

    if profile_dir.exists():
        console.print(f"[red]Error: Profile '{name}' already exists.[/red]")
        return

    # Create profile directory structure
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / "logs").mkdir(exist_ok=True)

    # Create empty data files
    import json
    for filename in ["groups.json", "texts.json", "jobs.json"]:
        with open(profile_dir / filename, 'w') as f:
            json.dump([], f)

    console.print(f"[green]Profile '{name}' created successfully![/green]")
    console.print(f"\nProfile directory: [cyan]{profile_dir}[/cyan]")
    console.print(f"\nUsage:")
    console.print(f"  [cyan]fbposter --profile {name} groups list[/cyan]")
    console.print(f"  [cyan]fbposter --profile {name} groups add --city Frankfurt --url <url>[/cyan]")
    console.print(f"  [cyan]fbposter -p {name} status[/cyan]")


@profiles.command()
@click.argument('name')
@click.option('--force', '-f', is_flag=True, help='Force deletion without confirmation')
def delete(name, force):
    """Delete a profile and all its data"""
    profile_dir = get_profile_dir(name)

    if not profile_dir.exists():
        console.print(f"[red]Error: Profile '{name}' does not exist.[/red]")
        return

    if not force:
        console.print(f"[yellow]Warning: This will delete all data for profile '{name}':[/yellow]")
        console.print(f"  - Groups, texts, and jobs")
        console.print(f"  - Chrome profile (login session)")
        console.print(f"  - Posting logs")
        if not click.confirm("Are you sure?"):
            console.print("[dim]Cancelled.[/dim]")
            return

    shutil.rmtree(profile_dir)
    console.print(f"[green]Profile '{name}' deleted.[/green]")


@profiles.command()
@click.argument('name')
def show(name):
    """Show details of a profile"""
    profile_dir = get_profile_dir(name)

    if not profile_dir.exists():
        console.print(f"[red]Error: Profile '{name}' does not exist.[/red]")
        return

    console.print(f"\n[bold cyan]Profile: {name}[/bold cyan]\n")
    console.print(f"Directory: [cyan]{profile_dir}[/cyan]\n")

    # Show data counts
    groups_file = profile_dir / "groups.json"
    texts_file = profile_dir / "texts.json"
    jobs_file = profile_dir / "jobs.json"
    chrome_dir = profile_dir / "chrome-profile"
    logs_dir = profile_dir / "logs"

    table = Table(show_header=False, box=None)
    table.add_column("Item", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Groups", str(_count_json_items(groups_file)))
    table.add_row("Texts", str(_count_json_items(texts_file)))
    table.add_row("Jobs", str(_count_json_items(jobs_file)))
    table.add_row("Chrome Profile", "Yes" if chrome_dir.exists() else "No")
    table.add_row("Has Logs", "Yes" if logs_dir.exists() and any(logs_dir.iterdir()) else "No")

    console.print(table)

    # Show cities if groups exist
    groups_count = _count_json_items(groups_file)
    if groups_count > 0:
        import json
        with open(groups_file, 'r') as f:
            groups = json.load(f)
        cities = set(g.get('city', 'Unknown') for g in groups)
        console.print(f"\n[bold]Cities:[/bold] {', '.join(sorted(cities))}")


@profiles.command()
@click.argument('source')
@click.argument('target')
def copy(source, target):
    """Copy a profile to create a new one"""
    source_dir = get_profile_dir(source)
    target_dir = get_profile_dir(target)

    if not source_dir.exists():
        console.print(f"[red]Error: Source profile '{source}' does not exist.[/red]")
        return

    if target_dir.exists():
        console.print(f"[red]Error: Target profile '{target}' already exists.[/red]")
        return

    # Copy everything except chrome-profile (login sessions shouldn't be copied)
    target_dir.mkdir(parents=True)

    for item in source_dir.iterdir():
        if item.name == 'chrome-profile':
            continue  # Skip chrome profile
        if item.is_file():
            shutil.copy2(item, target_dir / item.name)
        elif item.is_dir():
            shutil.copytree(item, target_dir / item.name)

    console.print(f"[green]Profile '{source}' copied to '{target}'[/green]")
    console.print("[dim]Note: Chrome profile was not copied. You'll need to log in again.[/dim]")


@profiles.command('init')
@click.argument('name')
@click.option('--from-default', is_flag=True, help='Copy data from default (non-profile) data directory')
def init_from_default(name, from_default):
    """Initialize a profile from existing data"""
    profile_dir = get_profile_dir(name)

    if profile_dir.exists():
        console.print(f"[red]Error: Profile '{name}' already exists.[/red]")
        console.print(f"[dim]Use 'fbposter profiles delete {name}' first if you want to replace it.[/dim]")
        return

    # Get the default data directory
    package_dir = Path(__file__).parent.parent.parent
    default_data_dir = package_dir / "data"
    default_chrome_dir = package_dir / "chrome-profile"

    if from_default:
        if not default_data_dir.exists():
            console.print(f"[red]Error: Default data directory not found at {default_data_dir}[/red]")
            return

        # Create profile directory
        profile_dir.mkdir(parents=True, exist_ok=True)
        (profile_dir / "logs").mkdir(exist_ok=True)

        # Copy data files
        for filename in ["groups.json", "texts.json", "jobs.json"]:
            src = default_data_dir / filename
            dst = profile_dir / filename
            if src.exists():
                shutil.copy2(src, dst)
                console.print(f"  [green]Copied[/green] {filename}")
            else:
                # Create empty file
                import json
                with open(dst, 'w') as f:
                    json.dump([], f)
                console.print(f"  [dim]Created empty[/dim] {filename}")

        # Copy chrome profile if it exists
        if default_chrome_dir.exists():
            dst_chrome = profile_dir / "chrome-profile"
            shutil.copytree(default_chrome_dir, dst_chrome)
            console.print(f"  [green]Copied[/green] chrome-profile (login session)")

        console.print(f"\n[green]Profile '{name}' initialized from default data![/green]")
    else:
        # Just create empty profile
        profile_dir.mkdir(parents=True, exist_ok=True)
        (profile_dir / "logs").mkdir(exist_ok=True)

        import json
        for filename in ["groups.json", "texts.json", "jobs.json"]:
            with open(profile_dir / filename, 'w') as f:
                json.dump([], f)

        console.print(f"[green]Profile '{name}' created (empty).[/green]")

    console.print(f"\nUsage: [cyan]fbposter --profile {name} status[/cyan]")


def _count_json_items(file_path: Path) -> int:
    """Count items in a JSON array file"""
    if not file_path.exists():
        return 0
    try:
        import json
        with open(file_path, 'r') as f:
            data = json.load(f)
        return len(data) if isinstance(data, list) else 0
    except:
        return 0
