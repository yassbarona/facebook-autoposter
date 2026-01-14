"""
CLI commands for managing Facebook groups
"""
import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

from ..data.models import Group
from ..data.storage import DataStore
from .main import cli

console = Console()


@cli.group()
def groups():
    """Manage Facebook groups"""
    pass


@groups.command('list')
@click.option('--city', help='Filter by city')
@click.option('--active/--inactive', default=None, help='Filter by active status')
def list_groups(city, active):
    """List all groups"""
    data_store = DataStore()
    all_groups = data_store.load_groups()

    # Apply filters
    if city:
        all_groups = [g for g in all_groups if g.city == city]
    if active is not None:
        all_groups = [g for g in all_groups if g.active == active]

    if not all_groups:
        console.print("[yellow]No groups found[/yellow]")
        return

    # Group by city
    cities = {}
    for group in all_groups:
        if group.city not in cities:
            cities[group.city] = []
        cities[group.city].append(group)

    # Display by city
    for city_name, city_groups in sorted(cities.items()):
        console.print(f"\n[bold cyan]{city_name}[/bold cyan] ({len(city_groups)} groups)")

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column("ID", style="dim", width=8)
        table.add_column("URL", overflow="fold", max_width=60)
        table.add_column("Active", justify="center", width=8)

        for group in city_groups:
            active_icon = "✓" if group.active else "✗"
            active_style = "green" if group.active else "red"
            table.add_row(
                group.id[:8],
                group.url,
                f"[{active_style}]{active_icon}[/{active_style}]"
            )

        console.print(table)

    console.print(f"\n[bold]Total:[/bold] {len(all_groups)} groups")


@groups.command('add')
@click.option('--city', prompt=True, help='City/category label')
@click.option('--url', prompt=True, help='Facebook group URL')
@click.option('--name', default='', help='Optional group name')
def add_group(city, url, name):
    """Add a new group"""
    try:
        group = Group(
            url=url,
            city=city,
            name=name,
            active=True
        )

        data_store = DataStore()
        data_store.add_group(group)

        console.print(f"[green]✓[/green] Group added successfully")
        console.print(f"  ID: {group.id}")
        console.print(f"  City: {group.city}")
        console.print(f"  URL: {group.url}")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")


@groups.command('remove')
@click.argument('group_id')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
def remove_group(group_id, yes):
    """Remove a group by ID"""
    data_store = DataStore()

    # Find the group
    group = data_store.get_group(group_id)
    if not group:
        console.print(f"[red]Error:[/red] Group not found: {group_id}")
        return

    # Confirm deletion
    if not yes:
        console.print(f"\n[yellow]About to delete:[/yellow]")
        console.print(f"  City: {group.city}")
        console.print(f"  URL: {group.url}")
        if not Confirm.ask("\nAre you sure?", default=False):
            console.print("[yellow]Cancelled[/yellow]")
            return

    # Delete
    if data_store.remove_group(group_id):
        console.print(f"[green]✓[/green] Group removed successfully")
    else:
        console.print(f"[red]Error:[/red] Failed to remove group")


@groups.command('toggle')
@click.argument('group_id')
def toggle_active(group_id):
    """Toggle active/inactive status of a group"""
    data_store = DataStore()

    # Find the group
    group = data_store.get_group(group_id)
    if not group:
        console.print(f"[red]Error:[/red] Group not found: {group_id}")
        return

    # Toggle active status
    group.active = not group.active

    # Save
    all_groups = data_store.load_groups()
    for i, g in enumerate(all_groups):
        if g.id == group_id:
            all_groups[i] = group
            break

    data_store.save_groups(all_groups)

    status = "[green]active[/green]" if group.active else "[red]inactive[/red]"
    console.print(f"[green]✓[/green] Group is now {status}")


@groups.command('cities')
def list_cities():
    """List all cities with group counts"""
    data_store = DataStore()
    all_groups = data_store.load_groups()

    cities = {}
    for group in all_groups:
        if group.city not in cities:
            cities[group.city] = {'total': 0, 'active': 0}
        cities[group.city]['total'] += 1
        if group.active:
            cities[group.city]['active'] += 1

    table = Table(title="Cities")
    table.add_column("City", style="cyan")
    table.add_column("Total Groups", justify="right")
    table.add_column("Active", justify="right", style="green")

    for city, counts in sorted(cities.items()):
        table.add_row(
            city,
            str(counts['total']),
            str(counts['active'])
        )

    console.print(table)
    console.print(f"\n[bold]Total Cities:[/bold] {len(cities)}")
