"""
Configuration management for Facebook Auto-Poster
Supports multiple profiles for different Facebook accounts/campaigns
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv


# Global profile setting
_current_profile: Optional[str] = None


def set_profile(profile_name: Optional[str]):
    """Set the active profile globally"""
    global _current_profile
    _current_profile = profile_name


def get_current_profile() -> Optional[str]:
    """Get the currently active profile"""
    return _current_profile


def get_profiles_dir() -> Path:
    """Get the base profiles directory"""
    package_dir = Path(__file__).parent.parent.parent
    return package_dir / "profiles"


def get_profile_dir(profile_name: str) -> Path:
    """Get a specific profile's directory"""
    return get_profiles_dir() / profile_name


def list_profiles() -> list:
    """List all available profiles"""
    profiles_dir = get_profiles_dir()
    if not profiles_dir.exists():
        return []
    return [d.name for d in profiles_dir.iterdir() if d.is_dir()]


class Config:
    """Application configuration manager"""

    def __init__(self, config_file: str = "config/config.yaml", profile: str = None):
        self.config_file = Path(config_file)
        self.profile = profile or get_current_profile()
        self.config = self._load_config()
        self._load_env()

    def _load_env(self):
        """Load environment variables from .env file"""
        env_file = Path("config/.env")
        if env_file.exists():
            load_dotenv(env_file)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_file.exists():
            return self._default_config()

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config or {}
        except Exception as e:
            print(f"Error loading config: {e}")
            return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Default configuration"""
        return {
            'browser': {
                'headless': True,
                'window_size': '1920x1080',
                'user_agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                'chrome_binary': '/usr/bin/google-chrome',
            },
            'facebook': {
                'login_timeout': 30,
                'page_load_timeout': 20,
                'post_delay_min': 8,
                'post_delay_max': 15,
                'max_posts_per_hour': 20,
            },
            'logging': {
                'level': 'INFO',
                'file': 'data/logs/fbposter.log',
                'max_bytes': 10485760,  # 10MB
                'backup_count': 5,
            },
            'api': {
                'webhook_url': 'https://automation.vivastours.com/webhook/fb_logs',
                'webhook_enabled': True,
                'webhook_timeout': 10,
            },
            'data': {
                'groups_file': 'data/groups.json',
                'texts_file': 'data/texts.json',
                'jobs_file': 'data/jobs.json',
                'db_file': 'data/logs/posts_history.db',
                'backup_enabled': True,
                'backup_count': 7,
            },
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key"""
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def get_env(self, key: str, default: str = "") -> str:
        """Get environment variable"""
        return os.getenv(key, default)

    def get_data_dir(self) -> Path:
        """Get the data directory (profile-aware)"""
        if self.profile:
            return get_profile_dir(self.profile)
        # Default: use main data directory
        package_dir = Path(__file__).parent.parent.parent
        return package_dir / "data"

    def get_chrome_profile_dir(self) -> Path:
        """Get Chrome profile directory (profile-aware)"""
        if self.profile:
            return get_profile_dir(self.profile) / "chrome-profile"
        # Default: use main chrome-profile directory
        package_dir = Path(__file__).parent.parent.parent
        return package_dir / "chrome-profile"

    def get_logs_dir(self) -> Path:
        """Get logs directory (profile-aware)"""
        if self.profile:
            return get_profile_dir(self.profile) / "logs"
        # Default: use main logs directory
        package_dir = Path(__file__).parent.parent.parent
        return package_dir / "data" / "logs"

    def save_example_config(self):
        """Save example configuration file"""
        example_path = self.config_file.parent / "config.example.yaml"
        example_path.parent.mkdir(parents=True, exist_ok=True)

        with open(example_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._default_config(), f, default_flow_style=False, sort_keys=False)

    def save_example_env(self):
        """Save example .env file"""
        env_example = self.config_file.parent / ".env.example"
        env_example.parent.mkdir(parents=True, exist_ok=True)

        with open(env_example, 'w', encoding='utf-8') as f:
            f.write("""# Facebook Auto-Poster Environment Variables
# Copy this file to .env and fill in your actual values

# API credentials
VIVAS_API_KEY=your_api_key_here

# Facebook user ID for login verification
FACEBOOK_USER_ID=your.facebook.username

# Optional: Chrome profile path for persistent login
# CHROME_PROFILE_PATH=/workspace/fbposter/chrome-profile
""")

# Global config instance
_config = None


def get_config() -> Config:
    """Get global configuration instance (profile-aware)"""
    global _config
    if _config is None:
        _config = Config()
    # If profile changed, recreate config
    elif _config.profile != get_current_profile():
        _config = Config()
    return _config


def reset_config():
    """Reset global config instance (call after profile change)"""
    global _config
    _config = None
