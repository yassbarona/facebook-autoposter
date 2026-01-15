"""
CLI commands for Telegram bot management
"""
import click
from rich.console import Console
from rich.panel import Panel

from ..utils.telegram import get_notifier, TelegramNotifier
from ..utils.config import get_config, get_current_profile
from ..data.storage import DataStore, LogStore
from .main import cli

console = Console()


@cli.group()
def telegram():
    """Manage Telegram bot notifications"""
    pass


@telegram.command('test')
def test_connection():
    """Test Telegram bot connection"""
    console.print("\n[bold cyan]Testing Telegram Connection...[/bold cyan]\n")

    notifier = get_notifier()

    # Check configuration
    if not notifier.bot_token:
        console.print("[red]Error:[/red] TELEGRAM_BOT_TOKEN not set in config/.env")
        console.print("\nTo configure Telegram:")
        console.print("  1. Create a bot with @BotFather on Telegram")
        console.print("  2. Copy the bot token")
        console.print("  3. Add to config/.env: TELEGRAM_BOT_TOKEN=your_token")
        return

    if not notifier.chat_id:
        console.print("[red]Error:[/red] TELEGRAM_CHAT_ID not set in config/.env")
        console.print("\nTo get your chat ID:")
        console.print("  1. Message @userinfobot on Telegram")
        console.print("  2. Copy your chat ID")
        console.print("  3. Add to config/.env: TELEGRAM_CHAT_ID=your_id")
        return

    console.print(f"Bot Token: [dim]{notifier.bot_token[:10]}...{notifier.bot_token[-5:]}[/dim]")
    console.print(f"Chat ID: [dim]{notifier.chat_id}[/dim]")
    console.print()

    # Test connection
    result = notifier.test_connection()

    if result['success']:
        console.print(f"[green]Success![/green] Connected to bot: @{result['bot_username']}")
        console.print(f"Bot name: {result['bot_name']}")
        console.print("\n[dim]A test message was sent to your Telegram.[/dim]")
    else:
        console.print(f"[red]Failed:[/red] {result['error']}")


@telegram.command('status')
@click.pass_context
def send_status(ctx):
    """Send current status to Telegram"""
    notifier = get_notifier()

    if not notifier.is_configured:
        console.print("[red]Error:[/red] Telegram not configured")
        console.print("Run 'fbposter telegram test' for setup instructions")
        return

    # Gather stats
    data_store = ctx.obj['data_store']
    log_store = ctx.obj['log_store']
    profile = get_current_profile()

    groups = data_store.load_groups()
    texts = data_store.load_texts()
    jobs = data_store.load_jobs()
    success_stats = log_store.get_success_rate(days=7)

    stats = {
        'total_groups': len(groups),
        'active_groups': len([g for g in groups if g.active]),
        'texts': len(texts),
        'jobs': len(jobs),
        'enabled_jobs': len([j for j in jobs if j.enabled]),
        'total_posts': success_stats['total'],
        'success_rate': success_stats['success_rate']
    }

    console.print("[dim]Sending status to Telegram...[/dim]")

    if notifier.send_status(stats, profile):
        console.print("[green]Status sent successfully![/green]")
    else:
        console.print("[red]Failed to send status[/red]")


@telegram.command('enable')
def enable_notifications():
    """Enable Telegram notifications"""
    config = get_config()

    # Check if configured
    notifier = get_notifier()
    if not notifier.is_configured:
        console.print("[red]Error:[/red] Configure Telegram first")
        console.print("Run 'fbposter telegram test' for setup instructions")
        return

    console.print("[yellow]Note:[/yellow] To enable Telegram, add this to config/config.yaml:")
    console.print()
    console.print(Panel(
        "telegram:\n"
        "  enabled: true\n"
        "  notify_on_success: true\n"
        "  notify_on_failure: true\n"
        "  notify_on_start: false",
        title="config/config.yaml",
        border_style="cyan"
    ))
    console.print()
    console.print("Or set [cyan]enabled: true[/cyan] if the section already exists.")


@telegram.command('disable')
def disable_notifications():
    """Disable Telegram notifications"""
    console.print("[yellow]Note:[/yellow] To disable Telegram, edit config/config.yaml:")
    console.print()
    console.print(Panel(
        "telegram:\n"
        "  enabled: false",
        title="config/config.yaml",
        border_style="cyan"
    ))


@telegram.command('info')
def show_info():
    """Show Telegram configuration info"""
    config = get_config()
    notifier = get_notifier()

    console.print("\n[bold cyan]Telegram Configuration[/bold cyan]\n")

    # Status
    if notifier.is_configured:
        console.print(f"Status: [green]Configured[/green]")
        console.print(f"Bot Token: [dim]{notifier.bot_token[:10]}...{notifier.bot_token[-5:]}[/dim]")
        console.print(f"Chat ID: [dim]{notifier.chat_id}[/dim]")
    else:
        console.print(f"Status: [red]Not Configured[/red]")
        if not notifier.bot_token:
            console.print("  Missing: TELEGRAM_BOT_TOKEN")
        if not notifier.chat_id:
            console.print("  Missing: TELEGRAM_CHAT_ID")

    # Settings
    console.print(f"\n[bold]Notification Settings:[/bold]")
    console.print(f"  Enabled: {'[green]Yes[/green]' if config.get('telegram.enabled', False) else '[red]No[/red]'}")
    console.print(f"  Notify on Success: {'Yes' if config.get('telegram.notify_on_success', True) else 'No'}")
    console.print(f"  Notify on Failure: {'Yes' if config.get('telegram.notify_on_failure', True) else 'No'}")
    console.print(f"  Notify on Start: {'Yes' if config.get('telegram.notify_on_start', False) else 'No'}")

    console.print()
