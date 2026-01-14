"""
CLI commands for managing text templates
"""
import click
import subprocess
import tempfile
import os
import shutil
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from ..data.models import Text
from ..data.storage import DataStore
from .main import cli

console = Console()


@cli.group()
def texts():
    """Manage post text templates"""
    pass


@texts.command('list')
def list_texts():
    """List all text templates"""
    data_store = DataStore()
    all_texts = data_store.load_texts()

    if not all_texts:
        console.print("[yellow]No text templates found[/yellow]")
        return

    table = Table(title="Text Templates")
    table.add_column("ID", style="dim", width=8)
    table.add_column("Name", style="cyan")
    table.add_column("Preview", overflow="fold", max_width=50)
    table.add_column("Image", justify="center", width=5)

    for text in all_texts:
        preview = text.content[:50] + "..." if len(text.content) > 50 else text.content
        has_image = "✓" if text.image_url else "✗"
        table.add_row(
            text.id[:8],
            text.name,
            preview.replace('\n', ' '),
            has_image
        )

    console.print(table)
    console.print(f"\n[bold]Total:[/bold] {len(all_texts)} templates")


@texts.command('show')
@click.argument('text_id')
def show_text(text_id):
    """Show full text template content"""
    data_store = DataStore()

    # Find the text
    text = data_store.get_text(text_id)
    if not text:
        console.print(f"[red]Error:[/red] Text template not found: {text_id}")
        return

    # Display
    console.print(f"\n[bold cyan]{text.name}[/bold cyan]")
    console.print(f"[dim]ID: {text.id}[/dim]\n")

    console.print(Panel(text.content, title="Content", expand=False))

    if text.image_url:
        console.print(f"\n[bold]Image URL:[/bold] {text.image_url}")

    if text.user_id:
        console.print(f"[bold]User ID:[/bold] {text.user_id}")

    if text.tags:
        console.print(f"[bold]Tags:[/bold] {', '.join(text.tags)}")

    console.print()


@texts.command('add')
@click.option('--name', prompt=True, help='Template name')
@click.option('--content', help='Template content (or omit to open editor)')
@click.option('--image-url', help='Image URL')
@click.option('--user-id', help='Facebook user ID')
def add_text(name, content, image_url, user_id):
    """Add a new text template"""
    # If no content provided, open editor
    if not content:
        content = _edit_in_editor()
        if not content:
            console.print("[yellow]Cancelled - no content provided[/yellow]")
            return

    try:
        text = Text(
            name=name,
            content=content,
            image_url=image_url,
            user_id=user_id or ""
        )

        data_store = DataStore()
        data_store.add_text(text)

        console.print(f"[green]✓[/green] Text template added successfully")
        console.print(f"  ID: {text.id}")
        console.print(f"  Name: {text.name}")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")


@texts.command('edit')
@click.argument('text_id')
def edit_text(text_id):
    """Edit an existing text template"""
    data_store = DataStore()

    # Find the text
    text = data_store.get_text(text_id)
    if not text:
        console.print(f"[red]Error:[/red] Text template not found: {text_id}")
        return

    # Edit in editor
    new_content = _edit_in_editor(text.content)
    if not new_content:
        console.print("[yellow]Cancelled - no changes made[/yellow]")
        return

    # Update
    text.content = new_content

    all_texts = data_store.load_texts()
    for i, t in enumerate(all_texts):
        if t.id == text_id:
            all_texts[i] = text
            break

    data_store.save_texts(all_texts)
    console.print(f"[green]✓[/green] Text template updated successfully")


@texts.command('remove')
@click.argument('text_id')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
def remove_text(text_id, yes):
    """Remove a text template"""
    data_store = DataStore()

    # Find the text
    text = data_store.get_text(text_id)
    if not text:
        console.print(f"[red]Error:[/red] Text template not found: {text_id}")
        return

    # Confirm deletion
    if not yes:
        console.print(f"\n[yellow]About to delete:[/yellow]")
        console.print(f"  Name: {text.name}")
        console.print(f"  Content: {text.content[:50]}...")
        if not Confirm.ask("\nAre you sure?", default=False):
            console.print("[yellow]Cancelled[/yellow]")
            return

    # Delete (use full ID from resolved text object)
    if data_store.remove_text(text.id):
        console.print(f"[green]✓[/green] Text template removed successfully")
    else:
        console.print(f"[red]Error:[/red] Failed to remove text template")


def _edit_in_editor(initial_content: str = "") -> str:
    """Open system editor for text editing"""
    # Try to find an available editor
    editors = ['nano', 'vim', 'vi']
    editor = os.environ.get('EDITOR')

    if not editor:
        for ed in editors:
            if shutil.which(ed):
                editor = ed
                break

    if not editor:
        console.print("[red]Error:[/red] No text editor found (nano, vim, or vi)")
        console.print("Please install nano: sudo apt-get install nano")
        return ""

    # Show instructions based on editor
    console.print(f"\n[cyan]Opening {editor} editor...[/cyan]")
    if editor in ['vi', 'vim']:
        console.print("[yellow]Vi/Vim Instructions:[/yellow]")
        console.print("  1. Press [bold]i[/bold] to start typing (INSERT mode)")
        console.print("  2. Type or paste your text")
        console.print("  3. Press [bold]Esc[/bold] to exit insert mode")
        console.print("  4. Type [bold]:wq[/bold] and press Enter to save and quit")
        console.print("  5. Or type [bold]:q![/bold] to quit without saving")
    elif editor == 'nano':
        console.print("[yellow]Nano Instructions:[/yellow]")
        console.print("  1. Type or paste your text")
        console.print("  2. Press [bold]Ctrl+X[/bold] to exit")
        console.print("  3. Press [bold]Y[/bold] to save, then Enter")
    console.print("\n[dim]Press Enter to continue...[/dim]")
    input()

    with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as tf:
        if initial_content:
            tf.write(initial_content)
        tf.flush()
        temp_path = tf.name

    try:
        result = subprocess.call([editor, temp_path])
        if result != 0:
            console.print(f"[yellow]Warning:[/yellow] Editor exited with code {result}")

        with open(temp_path, 'r') as f:
            content = f.read().strip()

        return content

    except Exception as e:
        console.print(f"[red]Error opening editor:[/red] {e}")
        return ""
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
