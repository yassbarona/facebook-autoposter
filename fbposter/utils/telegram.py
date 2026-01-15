"""
Telegram Bot integration for Facebook Auto-Poster
Provides notifications and remote control via Telegram
"""
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from telegram import Bot
from telegram.error import TelegramError

from .config import get_config
from .logger import get_logger

logger = get_logger("telegram")


class TelegramNotifier:
    """Handles Telegram bot notifications"""

    def __init__(self):
        self.config = get_config()
        self.bot_token = self.config.get_env('TELEGRAM_BOT_TOKEN')
        self.chat_id = self.config.get_env('TELEGRAM_CHAT_ID')
        self._bot: Optional[Bot] = None

    @property
    def is_configured(self) -> bool:
        """Check if Telegram is properly configured"""
        return bool(self.bot_token and self.chat_id)

    @property
    def is_enabled(self) -> bool:
        """Check if Telegram notifications are enabled"""
        return self.config.get('telegram.enabled', False) and self.is_configured

    def _get_bot(self) -> Bot:
        """Get or create bot instance"""
        if self._bot is None:
            if not self.bot_token:
                raise ValueError("TELEGRAM_BOT_TOKEN not configured")
            self._bot = Bot(token=self.bot_token)
        return self._bot

    def _run_async(self, coro):
        """Run async code in sync context"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a new loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, coro)
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(coro)

    async def _send_message_async(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send a message asynchronously"""
        try:
            bot = self._get_bot()
            await bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode
            )
            return True
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send a message to the configured chat"""
        if not self.is_configured:
            logger.warning("Telegram not configured, skipping notification")
            return False

        try:
            return self._run_async(self._send_message_async(text, parse_mode))
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    def notify_job_start(self, job_name: str, total_groups: int, profile: str = None):
        """Send notification when a job starts"""
        if not self.is_enabled:
            return

        if not self.config.get('telegram.notify_on_start', False):
            return

        profile_text = f" <i>(profile: {profile})</i>" if profile else ""
        message = (
            f"<b>Job Started</b>{profile_text}\n\n"
            f"<b>Job:</b> {job_name}\n"
            f"<b>Groups:</b> {total_groups}\n"
            f"<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.send_message(message)

    def notify_job_complete(self, job_name: str, results: Dict[str, Any], profile: str = None):
        """Send notification when a job completes"""
        if not self.is_enabled:
            return

        successful = results.get('successful', 0)
        failed = results.get('failed', 0)
        total = results.get('total', 0)
        skipped = results.get('skipped', 0)

        # Determine if we should notify based on settings
        has_failures = failed > 0
        has_successes = successful > 0

        if has_failures and not self.config.get('telegram.notify_on_failure', True):
            return
        if not has_failures and not self.config.get('telegram.notify_on_success', True):
            return

        # Build message
        if failed == 0 and successful > 0:
            status_emoji = "✅"
            status_text = "Completed Successfully"
        elif successful == 0 and failed > 0:
            status_emoji = "❌"
            status_text = "Failed"
        else:
            status_emoji = "⚠️"
            status_text = "Completed with Errors"

        profile_text = f" <i>(profile: {profile})</i>" if profile else ""

        message = (
            f"<b>{status_emoji} {status_text}</b>{profile_text}\n\n"
            f"<b>Job:</b> {job_name}\n"
            f"<b>Results:</b>\n"
            f"  • Total: {total}\n"
            f"  • Successful: {successful}\n"
            f"  • Failed: {failed}\n"
        )

        if skipped > 0:
            message += f"  • Skipped: {skipped}\n"

        # Add success rate
        if total > 0:
            rate = (successful / total) * 100
            message += f"\n<b>Success Rate:</b> {rate:.1f}%"

        # Add errors summary if any
        errors = results.get('errors', [])
        if errors and len(errors) > 0:
            message += f"\n\n<b>Errors ({len(errors)}):</b>\n"
            for error in errors[:3]:  # Show first 3 errors
                # Truncate long error messages
                error_short = error[:100] + "..." if len(error) > 100 else error
                message += f"• {error_short}\n"
            if len(errors) > 3:
                message += f"<i>...and {len(errors) - 3} more</i>"

        message += f"\n\n<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        self.send_message(message)

    def notify_error(self, error_message: str, job_name: str = None, profile: str = None):
        """Send notification for critical errors"""
        if not self.is_enabled:
            return

        if not self.config.get('telegram.notify_on_failure', True):
            return

        profile_text = f" <i>(profile: {profile})</i>" if profile else ""
        job_text = f"<b>Job:</b> {job_name}\n" if job_name else ""

        message = (
            f"<b>❌ Error</b>{profile_text}\n\n"
            f"{job_text}"
            f"<b>Error:</b> {error_message}\n"
            f"<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.send_message(message)

    def send_status(self, stats: Dict[str, Any], profile: str = None):
        """Send current status summary"""
        profile_text = f" <i>(profile: {profile})</i>" if profile else ""

        message = (
            f"<b>📊 Status Report</b>{profile_text}\n\n"
            f"<b>Groups:</b> {stats.get('total_groups', 0)} "
            f"({stats.get('active_groups', 0)} active)\n"
            f"<b>Templates:</b> {stats.get('texts', 0)}\n"
            f"<b>Jobs:</b> {stats.get('jobs', 0)} "
            f"({stats.get('enabled_jobs', 0)} enabled)\n"
        )

        # Add 7-day stats if available
        if 'success_rate' in stats:
            message += (
                f"\n<b>Last 7 Days:</b>\n"
                f"  • Posts: {stats.get('total_posts', 0)}\n"
                f"  • Success Rate: {stats.get('success_rate', 0):.1f}%"
            )

        message += f"\n\n<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        return self.send_message(message)

    async def test_connection_async(self) -> Dict[str, Any]:
        """Test the Telegram bot connection"""
        if not self.is_configured:
            return {
                'success': False,
                'error': 'Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env'
            }

        try:
            bot = self._get_bot()
            # Get bot info
            bot_info = await bot.get_me()

            # Try to send a test message
            await bot.send_message(
                chat_id=self.chat_id,
                text="✅ <b>Facebook Auto-Poster</b>\n\nTelegram connection test successful!",
                parse_mode="HTML"
            )

            return {
                'success': True,
                'bot_username': bot_info.username,
                'bot_name': bot_info.first_name
            }
        except TelegramError as e:
            return {
                'success': False,
                'error': str(e)
            }

    def test_connection(self) -> Dict[str, Any]:
        """Test the Telegram bot connection (sync wrapper)"""
        try:
            return self._run_async(self.test_connection_async())
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Global notifier instance
_notifier: Optional[TelegramNotifier] = None


def get_notifier() -> TelegramNotifier:
    """Get global Telegram notifier instance"""
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier


def notify_job_start(job_name: str, total_groups: int, profile: str = None):
    """Convenience function for job start notification"""
    get_notifier().notify_job_start(job_name, total_groups, profile)


def notify_job_complete(job_name: str, results: Dict[str, Any], profile: str = None):
    """Convenience function for job complete notification"""
    get_notifier().notify_job_complete(job_name, results, profile)


def notify_error(error_message: str, job_name: str = None, profile: str = None):
    """Convenience function for error notification"""
    get_notifier().notify_error(error_message, job_name, profile)
