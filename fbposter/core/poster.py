"""
Facebook posting logic with retry mechanism and rate limiting
Uses the exact working code pattern from the original script
"""
import time
import random
import requests
from datetime import datetime
from typing import Optional, Dict
from selenium.webdriver.common.by import By
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from ..data.models import Group, Text, Job, PostLog
from ..data.storage import LogStore
from ..utils.logger import get_logger
from ..utils.config import get_config
from .browser import Browser, BrowserError, ElementNotFoundError, AuthenticationError

logger = get_logger("poster")


class RateLimiter:
    """Manage posting rate to avoid spam detection"""

    def __init__(self):
        self.config = get_config()
        self.last_post_time = None
        self.posts_this_hour = 0
        self.hour_start_time = datetime.now()

    def wait_if_needed(self):
        """Wait if rate limit is reached"""
        max_per_hour = self.config.get('facebook.max_posts_per_hour', 20)
        now = datetime.now()

        # Reset hourly counter
        if (now - self.hour_start_time).seconds >= 3600:
            self.posts_this_hour = 0
            self.hour_start_time = now

        if self.posts_this_hour >= max_per_hour:
            wait_time = 3600 - (now - self.hour_start_time).seconds
            logger.warning(f"Hourly rate limit reached. Waiting {wait_time}s...")
            time.sleep(wait_time)
            self.posts_this_hour = 0
            self.hour_start_time = datetime.now()

        # Wait between posts
        if self.last_post_time:
            min_delay = self.config.get('facebook.post_delay_min', 8)
            max_delay = self.config.get('facebook.post_delay_max', 15)
            delay = random.randint(min_delay, max_delay)

            elapsed = (datetime.now() - self.last_post_time).seconds
            if elapsed < delay:
                wait_time = delay - elapsed
                logger.info(f"Rate limiting: waiting {wait_time}s before next post")
                time.sleep(wait_time)

        self.last_post_time = datetime.now()
        self.posts_this_hour += 1


class FacebookPoster:
    """Main Facebook posting functionality using exact working code"""

    def __init__(self, browser: Browser, log_store: Optional[LogStore] = None):
        self.browser = browser
        self.config = get_config()
        self.log_store = log_store or LogStore()
        self.rate_limiter = RateLimiter()

    def _js_click(self, element):
        """JavaScript click fallback when regular click is blocked"""
        self.browser.driver.execute_script("arguments[0].click();", element)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((BrowserError, ElementNotFoundError)),
        reraise=True
    )
    def post_to_group(
        self,
        group: Group,
        text: Text,
        job_id: Optional[str] = None
    ) -> bool:
        """Post content to a Facebook group using exact working code"""
        start_time = datetime.now()
        retry_count = 0
        driver = self.browser.driver

        try:
            logger.info(f"Posting to group: {group.city} - {group.url}")

            # Rate limiting
            self.rate_limiter.wait_if_needed()

            # Navigate to group
            driver.get(group.url)
            time.sleep(8)  # Wait for full page load

            # Dismiss any popups
            self.browser.dismiss_popups()
            time.sleep(2)

            # Format text with city placeholder
            formatted_text = text.format(city=group.city)
            if text.image_url:
                formatted_text += f"\n{text.image_url}"

            # === EXACT WORKING CODE ===

            # 1. Find "Escribe algo..."
            logger.debug("Finding 'Escribe algo...'")
            post_box = driver.find_element(By.XPATH, "//span[contains(text(), 'Escribe algo')]")

            # 2. Click it (with JS fallback)
            logger.debug("Clicking post box")
            try:
                post_box.click()
            except Exception:
                logger.debug("Using JS click for post box")
                self._js_click(post_box)
            time.sleep(5)

            # 3. Type text using active element
            logger.debug("Typing text")
            active_box = driver.switch_to.active_element
            active_box.send_keys(formatted_text)
            time.sleep(5)

            # 4. Find and click "Publicar"
            logger.debug("Clicking Publicar")
            post_button = driver.find_element(By.XPATH, "//div[@aria-label='Publicar']")
            try:
                post_button.click()
            except Exception:
                logger.debug("Using JS click for Publicar")
                self._js_click(post_button)
            time.sleep(5)

            # === END EXACT WORKING CODE ===

            # Success
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.info(f"Successfully posted to {group.url}")

            # Log success
            self._log_post(
                job_id=job_id or "",
                text_id=text.id,
                group=group,
                status="success",
                duration_ms=duration_ms,
                retry_count=retry_count
            )

            # Send webhook notification
            self._send_webhook(group, text, "success")

            return True

        except AuthenticationError as e:
            logger.error(f"Authentication error: {e}")
            self._log_post(
                job_id=job_id or "",
                text_id=text.id,
                group=group,
                status="failed",
                error_message=f"Authentication error: {str(e)}",
                retry_count=retry_count
            )
            raise

        except Exception as e:
            logger.error(f"Error posting to {group.url}: {e}")
            self._log_post(
                job_id=job_id or "",
                text_id=text.id,
                group=group,
                status="failed",
                error_message=str(e),
                retry_count=retry_count
            )
            return False

    def _log_post(
        self,
        job_id: str,
        text_id: str,
        group: Group,
        status: str,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        retry_count: int = 0
    ):
        """Log posting attempt to database"""
        log = PostLog(
            job_id=job_id,
            text_id=text_id,
            group_id=group.id,
            group_url=group.url,
            city=group.city,
            status=status,
            error_message=error_message,
            duration_ms=duration_ms,
            retry_count=retry_count
        )
        self.log_store.add_log(log)

    def _send_webhook(self, group: Group, text: Text, status: str):
        """Send notification to external webhook"""
        if not self.config.get('api.webhook_enabled', True):
            return

        webhook_url = self.config.get('api.webhook_url')
        if not webhook_url:
            return

        try:
            api_key = self.config.get_env('VIVAS_API_KEY', '')
            user_name = self.config.get_env('FACEBOOK_USER_ID', 'System')

            payload = {
                "date": datetime.now().isoformat(),
                "name": user_name,
                "city": group.city,
                "group": group.url,
                "log": f"{'Successfully' if status == 'success' else 'Failed to'} posted to {group.url}"
            }

            headers = {"api_key": api_key}
            timeout = self.config.get('api.webhook_timeout', 10)

            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=timeout
            )

            if response.status_code == 200:
                logger.debug("Webhook notification sent")
            else:
                logger.warning(f"Webhook returned status {response.status_code}")

        except requests.exceptions.Timeout:
            logger.warning("Webhook request timed out")
        except Exception as e:
            logger.warning(f"Failed to send webhook: {e}")


def run_job(job: Job, browser: Browser, data_store, dry_run: bool = False) -> Dict:
    """Execute a posting job"""
    logger.info(f"Running job: {job.name}")

    # Get text template
    text = data_store.get_text(job.text_id)
    if not text:
        logger.error(f"Text template not found: {job.text_id}")
        return {"success": False, "error": "Text template not found"}

    # Get groups for this job
    groups = data_store.get_groups_for_job(job)
    if not groups:
        logger.error(f"No groups found for job: {job.name}")
        return {"success": False, "error": "No groups found"}

    logger.info(f"Found {len(groups)} groups to post to")

    # Verify login
    browser.navigate_to("https://www.facebook.com")
    browser.verify_login()

    # Post to each group
    poster = FacebookPoster(browser)
    results = {
        "total": len(groups),
        "successful": 0,
        "failed": 0,
        "skipped": 0,
        "errors": []
    }

    for i, group in enumerate(groups, 1):
        logger.info(f"Processing group {i}/{len(groups)}: {group.city}")

        if dry_run:
            logger.info(f"[DRY RUN] Would post to: {group.url}")
            results["skipped"] += 1
            continue

        try:
            success = poster.post_to_group(group, text, job_id=job.id)
            if success:
                results["successful"] += 1
                group.last_posted = datetime.now()
                data_store.save_groups(data_store.load_groups())
            else:
                results["failed"] += 1

        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            results["errors"].append(f"Authentication error: {e}")
            break

        except Exception as e:
            logger.error(f"Failed to post to {group.url}: {e}")
            results["failed"] += 1
            results["errors"].append(f"{group.url}: {str(e)}")

    # Update job last run time
    job.last_run = datetime.now()
    data_store.update_job(job)

    logger.info(f"Job completed: {results['successful']} successful, {results['failed']} failed")
    return results
