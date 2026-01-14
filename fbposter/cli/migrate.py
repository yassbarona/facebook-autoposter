"""
CLI commands for migrating data from old Windows script
"""
import click
import json
from pathlib import Path
from rich.console import Console

from ..data.models import Group, Text
from ..data.storage import DataStore
from .main import cli

console = Console()


@cli.command()
@click.option('--from', 'source_dir', required=True, type=click.Path(exists=True),
              help='Source directory with old data files')
@click.option('--dry-run', is_flag=True, help='Show what would be migrated without actually doing it')
def migrate(source_dir, dry_run):
    """Migrate data from old Windows script format"""
    source_path = Path(source_dir)
    console.print(f"\n[bold cyan]Migrating data from:[/bold cyan] {source_path}\n")

    # Load old data files
    old_groups_file = source_path / "groups.json"
    old_texts_file = source_path / "text_data.json"

    if not old_groups_file.exists():
        console.print(f"[red]Error:[/red] {old_groups_file} not found")
        return

    if not old_texts_file.exists():
        console.print(f"[yellow]Warning:[/yellow] {old_texts_file} not found, skipping texts")
        old_texts = {}
    else:
        with open(old_texts_file, 'r', encoding='utf-8') as f:
            old_texts = json.load(f)

    with open(old_groups_file, 'r', encoding='utf-8') as f:
        old_groups = json.load(f)

    # Migrate groups
    new_groups = []
    for city, urls in old_groups.items():
        console.print(f"[cyan]{city}:[/cyan] {len(urls)} groups")
        for url in urls:
            try:
                group = Group(
                    url=url,
                    city=city,
                    name="",
                    active=True
                )
                new_groups.append(group)
            except ValueError as e:
                console.print(f"  [red]Error:[/red] {url}: {e}")

    # Migrate texts
    new_texts = []
    for name, data in old_texts.items():
        console.print(f"[magenta]Text:[/magenta] {name}")
        try:
            text = Text(
                name=name,
                content=data.get('text', ''),
                image_url=data.get('image_url'),
                user_id=data.get('user_id', '')
            )
            new_texts.append(text)
        except ValueError as e:
            console.print(f"  [red]Error:[/red] {name}: {e}")

    # Summary
    console.print(f"\n[bold]Migration Summary:[/bold]")
    console.print(f"  Groups: {len(new_groups)}")
    console.print(f"  Texts: {len(new_texts)}")

    if dry_run:
        console.print("\n[yellow](DRY RUN - no changes made)[/yellow]")
        return

    # Confirm
    if not click.confirm("\nProceed with migration?"):
        console.print("[yellow]Cancelled[/yellow]")
        return

    # Save
    data_store = DataStore()
    data_store.save_groups(new_groups)
    data_store.save_texts(new_texts)

    console.print("\n[green]✓[/green] Migration completed successfully!")
    console.print("\n[bold]Next steps:[/bold]")
    console.print("  1. Review migrated data: fbposter groups list && fbposter texts list")
    console.print("  2. Create posting jobs: fbposter jobs create")
    console.print("  3. Test a job: fbposter run <job-id> --dry-run")
