# Facebook Auto-Poster

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Selenium](https://img.shields.io/badge/Selenium-4.x-green.svg)](https://www.selenium.dev/)

A production-ready command-line tool for automating posts to Facebook groups. Built with Python, Selenium, and designed for reliability with features like automatic retries, rate limiting, and multi-account profile support.

## Features

- **Headless Browser Automation** - Posts to Facebook groups using Selenium with Chrome
- **Multi-Account Profiles** - Manage separate Facebook accounts with isolated data and login sessions
- **Telegram Notifications** - Get notified on job completion, failures, and status updates
- **Flexible Job System** - Map any text template to any combination of city groups
- **Smart Rate Limiting** - Configurable delays and hourly limits to avoid detection
- **Automatic Retries** - Exponential backoff for transient failures
- **systemd Integration** - Native Linux scheduling with timers
- **SQLite Logging** - Complete post history with success/failure tracking
- **City-Based Organization** - Organize groups by city for targeted campaigns
- **Template Placeholders** - Use `{city}` in templates for dynamic content

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Guide](#usage-guide)
  - [Managing Groups](#managing-groups)
  - [Managing Text Templates](#managing-text-templates)
  - [Managing Jobs](#managing-jobs)
  - [Running Jobs](#running-jobs)
  - [Using Profiles](#using-profiles)
- [Telegram Notifications](#telegram-notifications)
- [Scheduling with systemd](#scheduling-with-systemd)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)
- [License](#license)

## Installation

### Prerequisites

- Python 3.8 or higher
- Google Chrome browser
- Linux environment (tested on Ubuntu 20.04+)

### Install from Source

```bash
# Clone the repository
git clone https://github.com/yourusername/facebook-autoposter.git
cd facebook-autoposter

# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate

# Install the package
pip install -e .

# Verify installation
fbposter --help
```

### Configuration

1. Copy the example configuration files:
```bash
cp config/config.example.yaml config/config.yaml
cp config/.env.example config/.env
```

2. Edit the `.env` file with your credentials:
```bash
# config/.env
VIVAS_API_KEY=your_api_key_here
FACEBOOK_USER_ID=your.facebook.username
```

## Quick Start

```bash
# Check system status
fbposter status

# Add a Facebook group
fbposter groups add --city "Frankfurt" --url "https://www.facebook.com/groups/123456789"

# Create a text template
fbposter texts add

# Create a posting job
fbposter jobs create

# Run the job (with visible browser for first-time login)
fbposter run <job-id> --no-headless

# After logging in, run headless
fbposter run <job-id>
```

## Usage Guide

### Managing Groups

Groups are Facebook groups organized by city where posts will be published.

```bash
# List all groups
fbposter groups list

# List groups for a specific city
fbposter groups list --city Frankfurt

# Add a new group
fbposter groups add --city Frankfurt --url "https://www.facebook.com/groups/123456789"

# Add with a custom name
fbposter groups add --city Frankfurt --url "https://www.facebook.com/groups/123456789" --name "Frankfurt Jobs"

# Remove a group
fbposter groups remove <group-id>

# Disable/enable a group (disabled groups won't receive posts)
fbposter groups disable <group-id>
fbposter groups enable <group-id>
```

### Managing Text Templates

Text templates are the messages that get posted to groups. Use `{city}` as a placeholder.

```bash
# List all templates
fbposter texts list

# View a template
fbposter texts show <text-id>

# Create a new template (interactive)
fbposter texts add

# Edit a template
fbposter texts edit <text-id>

# Delete a template
fbposter texts remove <text-id>
```

**Example template:**
```
We're looking for tour guides in {city}!

Do you love sharing history and culture?
Join our team at Viva's Tour.

Contact: info@vivastour.com
```

### Managing Jobs

Jobs define which text template gets posted to which cities.

```bash
# List all jobs
fbposter jobs list

# Create a new job (interactive wizard)
fbposter jobs create

# Show job details
fbposter jobs show <job-id>

# Toggle job enabled/disabled
fbposter jobs toggle <job-id>

# Remove a job
fbposter jobs remove <job-id>
```

### Running Jobs

```bash
# Run a job
fbposter run <job-id>

# Run with visible browser (for debugging or first-time login)
fbposter run <job-id> --no-headless

# Dry run (simulate without posting)
fbposter run <job-id> --dry-run
```

### Using Profiles

Profiles allow you to manage multiple Facebook accounts with completely separate data.

```bash
# List available profiles
fbposter profiles list

# Create a new empty profile
fbposter profiles create english

# Create a profile from existing data
fbposter profiles init spanish --from-default

# Use a profile with any command
fbposter --profile spanish status
fbposter -p english groups list
fbposter --profile spanish run <job-id>

# Show profile details
fbposter profiles show spanish

# Copy a profile
fbposter profiles copy spanish spanish-backup

# Delete a profile
fbposter profiles delete english
```

Each profile has its own:
- Groups, texts, and jobs
- Chrome profile (login session)
- Posting logs

## Telegram Notifications

Get notified on Telegram when jobs complete, fail, or encounter errors.

### Setup

1. **Create a bot** - Message [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`, and copy the token

2. **Get your Chat ID** - Message [@userinfobot](https://t.me/userinfobot) to get your chat ID

3. **Configure** - Add to `config/.env`:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

4. **Enable** - Add to `config/config.yaml`:
```yaml
telegram:
  enabled: true
  notify_on_success: true
  notify_on_failure: true
  notify_on_start: false
```

5. **Start the bot** - Message your bot on Telegram (press Start)

6. **Test** - Run:
```bash
fbposter telegram test
```

### Telegram Commands

```bash
# Test bot connection
fbposter telegram test

# Send status report to Telegram
fbposter telegram status

# Show configuration info
fbposter telegram info
```

### What You'll Receive

- **Job Completion** - Success/failure counts, success rate, error summaries
- **Errors** - Authentication failures, critical errors
- **Status Reports** - On-demand system status via `fbposter telegram status`

## Scheduling with systemd

### Create a Timer

1. Create a timer file:
```bash
sudo nano /etc/systemd/system/fbposter@morning.timer
```

2. Add configuration:
```ini
[Unit]
Description=Facebook Poster - Morning Job

[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

3. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable fbposter@morning.timer
sudo systemctl start fbposter@morning.timer
```

### Common Schedules

| Schedule | OnCalendar Value |
|----------|------------------|
| Daily at 8am | `*-*-* 08:00:00` |
| Daily at 8pm | `*-*-* 20:00:00` |
| Twice daily | `*-*-* 08,20:00:00` |
| Every 6 hours | `*-*-* 00,06,12,18:00:00` |
| Weekdays at 9am | `Mon..Fri *-*-* 09:00:00` |

### View Timer Status

```bash
systemctl list-timers fbposter*
journalctl -u fbposter@morning --since today
```

## Configuration

### config/config.yaml

```yaml
browser:
  headless: true
  window_size: "1920x1080"

facebook:
  login_timeout: 30
  page_load_timeout: 20
  post_delay_min: 8      # Minimum seconds between posts
  post_delay_max: 15     # Maximum seconds between posts
  max_posts_per_hour: 20 # Rate limiting

logging:
  level: "INFO"
  file: "data/logs/fbposter.log"
  max_bytes: 10485760    # 10MB
  backup_count: 5
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `VIVAS_API_KEY` | API key for webhook notifications |
| `FACEBOOK_USER_ID` | Facebook username for verification |

## Troubleshooting

### "Element not found: Escribe algo"

The posting button wasn't found. Possible causes:
- Facebook account isn't a member of the group
- Group is private or restricted
- Run with `--no-headless` to debug

### "Authentication error"

Facebook login session expired:
1. Run with `--no-headless`: `fbposter run <job-id> --no-headless`
2. Log in to Facebook when prompted
3. Close browser and run normally

### Posts Not Appearing

- Group may require admin approval (check pending posts)
- Post may have been flagged by Facebook
- Check rate limiting settings

### Chrome Won't Start

```bash
# Kill stuck Chrome processes
pkill -9 chrome

# Try again
fbposter run <job-id>
```

## Project Structure

```
facebook-autoposter/
├── fbposter/
│   ├── cli/           # CLI commands
│   │   ├── main.py    # Entry point
│   │   ├── groups.py  # Group management
│   │   ├── texts.py   # Text templates
│   │   ├── jobs.py    # Job management
│   │   └── profiles.py # Profile management
│   ├── core/
│   │   ├── browser.py # Selenium automation
│   │   └── poster.py  # Facebook posting logic
│   ├── data/
│   │   ├── models.py  # Data models
│   │   └── storage.py # JSON/SQLite storage
│   └── utils/
│       ├── config.py  # Configuration
│       └── logger.py  # Logging
├── config/
│   ├── config.yaml        # Main configuration
│   ├── config.example.yaml
│   └── .env.example
├── data/                  # Default data directory
├── profiles/              # Multi-account profiles
├── systemd/               # systemd service templates
├── setup.py
└── README.md
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `fbposter status` | Show system status and statistics |
| `fbposter groups list` | List all groups |
| `fbposter groups add` | Add a new group |
| `fbposter texts list` | List text templates |
| `fbposter texts add` | Create a new template |
| `fbposter jobs list` | List all jobs |
| `fbposter jobs create` | Create a new job |
| `fbposter run <job-id>` | Run a posting job |
| `fbposter logs` | View recent posting logs |
| `fbposter profiles list` | List available profiles |
| `fbposter -p <name> <cmd>` | Run command with specific profile |
| `fbposter telegram test` | Test Telegram bot connection |
| `fbposter telegram status` | Send status to Telegram |

## License

MIT License - see [LICENSE](LICENSE) for details.

## Disclaimer

This tool is for authorized automation only. Ensure compliance with Facebook's Terms of Service. The author is not responsible for account restrictions or violations.

## Acknowledgments

This project was developed with the assistance of [Claude Code](https://claude.ai/claude-code), Anthropic's AI-powered development tool. Claude Code helped accelerate development by providing code suggestions, debugging assistance, and documentation support - enabling faster iteration while I maintained full creative and architectural control over the project.

---

**Built with Python, Selenium, and Click**
