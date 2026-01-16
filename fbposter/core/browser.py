"""
Browser management for Facebook automation
Simplified to match the working test script
"""
import time
import pickle
from pathlib import Path
from typing import Optional, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

from ..utils.logger import get_logger
from ..utils.config import get_config

logger = get_logger("browser")


class BrowserError(Exception):
    """Base exception for browser operations"""
    pass


class ElementNotFoundError(BrowserError):
    """Element not found with any selector"""
    pass


class AuthenticationError(BrowserError):
    """Authentication/login error"""
    pass


class Browser:
    """Manages Selenium WebDriver for Facebook automation"""

    def __init__(self, headless: Optional[bool] = None):
        self.config = get_config()
        self.headless = headless if headless is not None else self.config.get('browser.headless', True)
        self.driver: Optional[webdriver.Chrome] = None

    def init_driver(self) -> webdriver.Chrome:
        """Initialize Chrome WebDriver with simple, working options"""
        logger.info(f"Initializing Chrome driver (headless={self.headless})...")

        options = Options()

        if self.headless:
            options.add_argument('--headless=new')

        # Simple Chrome options that work correctly
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')

        # Use persistent profile for login session (profile-aware)
        chrome_profile = self.config.get_chrome_profile_dir()
        chrome_profile.mkdir(parents=True, exist_ok=True)
        logger.info(f"Chrome profile directory: {chrome_profile}")

        # Clean up stale lock files that could prevent profile access
        for stale_file in ['SingletonLock', 'SingletonSocket', 'SingletonCookie']:
            stale_path = chrome_profile / stale_file
            if stale_path.exists():
                try:
                    stale_path.unlink()
                    logger.debug(f"Removed stale lock file: {stale_file}")
                except Exception as e:
                    logger.warning(f"Could not remove {stale_file}: {e}")

        options.add_argument(f'--user-data-dir={chrome_profile}')
        options.add_argument('--profile-directory=Default')

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)

            timeout = self.config.get('facebook.page_load_timeout', 20)
            self.driver.set_page_load_timeout(timeout)

            logger.info("Chrome driver initialized successfully")
            return self.driver

        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            raise BrowserError(f"Failed to initialize browser: {e}")

    def dismiss_popups(self):
        """Dismiss common Facebook popups (Spanish)"""
        popup_xpaths = [
            "//div[@aria-label='Cerrar']",
            "//div[@aria-label='Close']",
            "//span[text()='Cerrar']",
            "//span[text()='Close']",
            "//button[contains(text(), 'No ahora')]",
            "//button[contains(text(), 'Not Now')]",
        ]

        for xpath in popup_xpaths:
            try:
                buttons = self.driver.find_elements(By.XPATH, xpath)
                for btn in buttons:
                    if btn.is_displayed():
                        logger.debug(f"Dismissing popup: {xpath}")
                        btn.click()
                        time.sleep(1)
            except:
                pass

    def navigate_to(self, url: str, wait_time: int = 5):
        """Navigate to URL"""
        try:
            logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            time.sleep(wait_time)
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            raise BrowserError(f"Failed to navigate to {url}: {e}")

    def is_logged_in(self) -> bool:
        """Check if user is logged in to Facebook"""
        try:
            # Check if we're on login page (email input present = not logged in)
            login_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[name='email']")
            if login_inputs and any(inp.is_displayed() for inp in login_inputs):
                logger.warning("User is not logged in (on login page)")
                return False

            logger.info("User appears to be logged in")
            return True
        except Exception as e:
            logger.warning(f"Login check error: {e}")
            return True  # Assume logged in if check fails

    def verify_login(self):
        """Verify login or raise AuthenticationError"""
        if not self.is_logged_in():
            raise AuthenticationError(
                "Not logged in to Facebook. Please log in manually first."
            )

    def wait_for_login(self, timeout: int = 300, check_interval: int = 5) -> bool:
        """Wait for user to login manually, checking periodically

        Args:
            timeout: Maximum seconds to wait (default 5 minutes)
            check_interval: Seconds between login checks

        Returns:
            True if logged in, False if timeout
        """
        logger.info(f"Waiting for Facebook login (timeout: {timeout}s)...")
        logger.info("Please login to Facebook in the browser window.")

        elapsed = 0
        while elapsed < timeout:
            # Check if logged in
            if self.is_logged_in():
                logger.info("Login detected! Session will be saved.")
                return True

            # Wait before next check
            time.sleep(check_interval)
            elapsed += check_interval

            # Log progress every 30 seconds
            if elapsed % 30 == 0:
                logger.info(f"Still waiting for login... ({elapsed}s / {timeout}s)")

        logger.warning(f"Login timeout after {timeout}s")
        return False

    def get_cookies_file(self) -> Path:
        """Get the path to the cookies file for this profile"""
        chrome_profile = self.config.get_chrome_profile_dir()
        return chrome_profile / "facebook_cookies.pkl"

    def save_cookies(self):
        """Save browser cookies to a file for session persistence"""
        try:
            cookies_file = self.get_cookies_file()
            cookies = self.driver.get_cookies()
            with open(cookies_file, 'wb') as f:
                pickle.dump(cookies, f)
            logger.info(f"Saved {len(cookies)} cookies to {cookies_file}")
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")

    def load_cookies(self):
        """Load cookies from file to restore session"""
        try:
            cookies_file = self.get_cookies_file()
            if not cookies_file.exists():
                logger.info("No saved cookies found")
                return False

            # First navigate to Facebook to set the domain
            self.driver.get("https://www.facebook.com")
            time.sleep(2)

            with open(cookies_file, 'rb') as f:
                cookies = pickle.load(f)

            for cookie in cookies:
                try:
                    # Some cookies may have expiry issues, skip those
                    if 'expiry' in cookie:
                        cookie['expiry'] = int(cookie['expiry'])
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.debug(f"Could not add cookie {cookie.get('name')}: {e}")

            logger.info(f"Loaded {len(cookies)} cookies from {cookies_file}")

            # Refresh to apply cookies
            self.driver.refresh()
            time.sleep(3)
            return True

        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return False

    def quit(self):
        """Quit browser gracefully"""
        if self.driver:
            try:
                logger.info("Closing browser...")
                self.driver.quit()
                self.driver = None
            except Exception as e:
                logger.error(f"Error closing browser: {e}")

    def __enter__(self):
        """Context manager entry"""
        self.init_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.quit()
