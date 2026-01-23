# Facebook Auto-Poster

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Selenium](https://img.shields.io/badge/Selenium-4.x-orange.svg)](https://www.selenium.dev/)

A production-grade automation platform for managing Facebook group posts at scale. Built with Python, Selenium, and FastAPI, featuring a modern web dashboard, job queue system, multi-account support, and real-time Telegram notifications.

> **Portfolio Project** - This project demonstrates expertise in browser automation, async job processing, web application development, and building robust CLI tools with Python.

---

## Key Highlights

| Feature | Description |
|---------|-------------|
| **Web Dashboard** | Modern responsive UI built with FastAPI + Tailwind CSS |
| **Job Queue System** | Sequential job processing with real-time status tracking |
| **Multi-Account Profiles** | Complete data isolation per Facebook account |
| **Multi-Language Support** | Target groups by city AND language (e.g., Paris-ES, Paris-EN) |
| **Telegram Integration** | Real-time notifications for job completions and errors |
| **Process Management** | Kill running jobs, reset stuck queues, PID tracking |
| **Session Persistence** | Chrome profile management for maintaining login sessions |
| **Fault Tolerance** | Automatic retries, graceful error handling, orphan job cleanup |

---

## Tech Stack

- **Backend**: Python 3.8+, FastAPI, SQLite
- **Automation**: Selenium WebDriver, Chrome/Chromium
- **Frontend**: Jinja2 Templates, Tailwind CSS
- **Notifications**: Telegram Bot API (python-telegram-bot)
- **CLI**: Click framework
- **Scheduling**: systemd timers (Linux)

---

## Features

### Core Automation
- **Headless Browser Automation** - Posts to Facebook groups using Selenium with Chrome
- **Smart Rate Limiting** - Configurable delays and hourly limits to avoid detection
- **Automatic Retries** - Exponential backoff for transient failures
- **Template Placeholders** - Use `{city}` in templates for dynamic content

### Multi-Account & Organization
- **Multi-Account Profiles** - Manage separate Facebook accounts with isolated data and login sessions
- **City-Based Organization** - Organize groups by city for targeted campaigns
- **Language Tags** - Distinguish groups in different languages for the same city (e.g., "Paris-es" vs "Paris-en")

### Job Management
- **Flexible Job System** - Map any text template to any combination of city/language groups
- **Job Queue** - Queue multiple jobs to run sequentially with real-time progress tracking
- **Kill Running Jobs** - Stop jobs mid-execution with process-level control
- **Reset Stuck Jobs** - Recover from crashed/orphaned job states

### Monitoring & Notifications
- **Telegram Notifications** - Get notified on job completion, failures, and status updates
- **SQLite Logging** - Complete post history with success/failure tracking
- **Web Dashboard** - Visual management interface with authentication

### Infrastructure
- **systemd Integration** - Native Linux scheduling with timers
- **Session Management** - Chrome profile persistence for maintaining Facebook login
- **Post-Publish Navigation** - Automatic modal dismissal after posting (language-agnostic)

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Web Dashboard](#web-dashboard)
- [Usage Guide](#usage-guide)
  - [Managing Groups](#managing-groups)
  - [Managing Text Templates](#managing-text-templates)
  - [Managing Jobs](#managing-jobs)
  - [Running Jobs](#running-jobs)
  - [Using Profiles](#using-profiles)
- [Job Queue System](#job-queue-system)
- [Telegram Notifications](#telegram-notifications)
- [Scheduling with systemd](#scheduling-with-systemd)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)
- [License](#license)

---

## Installation

### Prerequisites

- Python 3.8 or higher
- Google Chrome browser
- Linux environment (tested on Ubuntu 20.04+)

### Install from Source

```bash
# Clone the repository
git clone https://github.com/yassbarona/facebook-autoposter.git
cd facebook-autoposter

# Create virtual environment (recommended)
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
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

---

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

---

## Web Dashboard

A modern web interface for managing your Facebook Auto-Poster. Built with FastAPI and Tailwind CSS.

### Starting the Dashboard

```bash
# Start the dashboard
fbposter web start

# Start on a specific port
fbposter web start --port 8080
```

### Access

1. Start the server: `fbposter web start`
2. Open in browser: `http://localhost:8000`
3. Login with password (default: `admin`)

### Dashboard Features

| Page | Features |
|------|----------|
| **Dashboard** | Overview stats, city breakdown, recent activity |
| **Groups** | Add/remove groups, enable/disable, filter by city, set language tags |
| **Texts** | Create and manage post templates |
| **Jobs** | Create jobs, select multiple jobs, run queue |
| **Logs** | View job runs, kill running jobs, reset stuck jobs, see queue status |
| **Profiles** | Manage accounts, set FB username, login/logout sessions |

### Multi-Job Queue

From the Jobs page:
1. Check multiple jobs using the checkboxes
2. Click "Run Selected (N)"
3. Jobs are added to a queue and run sequentially
4. Monitor progress in the Logs page

### Configuration

```bash
# config/.env
DASHBOARD_PASSWORD=your_secure_password
DASHBOARD_SECRET_KEY=your_random_secret_key
```

---

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

# Disable/enable a group
fbposter groups disable <group-id>
fbposter groups enable <group-id>
```

#### Language Tags (Web Dashboard)

When adding groups via the web dashboard, you can assign a language tag (es, en, de, fr, pt, it) to distinguish groups in different languages for the same city:

- Groups in Paris with Spanish content → "Paris" + language "es" → appears as "Paris-es"
- Groups in Paris with English content → "Paris" + language "en" → appears as "Paris-en"

When creating jobs, you can select specific city-language combinations to target.

### Managing Text Templates

Text templates are the messages that get posted to groups. Use `{city}` as a placeholder.

```bash
# List all templates
fbposter texts list

# View a template
fbposter texts show <text-id>

# Create a new template (interactive)
fbposter texts add

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

# Use a profile with any command
fbposter --profile spanish status
fbposter -p english groups list

# Delete a profile
fbposter profiles delete english
```

Each profile has its own:
- Groups, texts, and jobs
- Chrome profile (login session)
- Posting logs
- Facebook username (for post-publish navigation)

---

## Job Queue System

The job queue allows running multiple jobs sequentially, with real-time tracking.

### How It Works

1. **Add to Queue**: Select jobs from the web dashboard and click "Run Selected"
2. **Sequential Processing**: Jobs run one at a time to avoid conflicts
3. **Status Tracking**: Monitor progress in the Logs page (queued → running → completed/failed)
4. **Fault Tolerance**: Stuck jobs are automatically detected and can be reset

### Queue Management (Web Dashboard)

| Action | Description |
|--------|-------------|
| **Run Selected** | Add checked jobs to queue |
| **Kill Job** | Stop a running job immediately |
| **Reset Stuck Jobs** | Clear jobs stuck in "running" state |
| **Clear Queue** | Remove all queued jobs |

### Automatic Cleanup

The queue processor automatically:
- Resets jobs stuck in "running" state for >30 minutes
- Cleans up orphaned job runs from crashed processes
- Tracks process PIDs for reliable job termination

---

## Telegram Notifications

Get notified on Telegram when jobs complete, fail, or encounter errors.

### Setup

1. **Create a bot** - Message [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`, and copy the token

2. **Get your Chat ID** - Message [@userinfobot](https://t.me/userinfobot) to get your chat ID (or use a group chat ID for team notifications)

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

5. **Test** - Run:
```bash
fbposter telegram test
```

### Notification Types

| Event | Description |
|-------|-------------|
| **Job Complete** | Success/failure counts, success rate, error summaries |
| **Critical Error** | Authentication failures, login errors, job crashes |
| **Status Report** | On-demand system status via `fbposter telegram status` |

---

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
| Twice daily | `*-*-* 08,20:00:00` |
| Every 6 hours | `*-*-* 00,06,12,18:00:00` |
| Weekdays at 9am | `Mon..Fri *-*-* 09:00:00` |

---

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

telegram:
  enabled: true
  notify_on_success: true
  notify_on_failure: true
  notify_on_start: false

logging:
  level: "INFO"
  file: "data/logs/fbposter.log"
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `VIVAS_API_KEY` | API key for webhook notifications |
| `FACEBOOK_USER_ID` | Facebook username for verification |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Telegram chat/group ID for notifications |
| `DASHBOARD_PASSWORD` | Web dashboard login password |
| `DASHBOARD_SECRET_KEY` | Session encryption key |

---

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

### Jobs Stuck in Queue

Use the "Reset Stuck Jobs" button in the Logs page, or wait for automatic cleanup (30 min timeout).

### Chrome Won't Start

```bash
# Kill stuck Chrome processes
pkill -9 chrome

# Try again
fbposter run <job-id>
```

---

## Project Structure

```
facebook-autoposter/
├── fbposter/
│   ├── cli/                    # CLI commands (Click)
│   │   ├── main.py             # Entry point
│   │   ├── groups.py           # Group management
│   │   ├── texts.py            # Text templates
│   │   ├── jobs.py             # Job management
│   │   ├── profiles.py         # Profile management
│   │   ├── telegram.py         # Telegram commands
│   │   └── web.py              # Web dashboard commands
│   ├── core/
│   │   ├── browser.py          # Selenium automation
│   │   ├── poster.py           # Facebook posting logic
│   │   └── queue_processor.py  # Job queue processing
│   ├── data/
│   │   ├── models.py           # Data models (Group, Text, Job)
│   │   └── storage.py          # JSON/SQLite storage layer
│   ├── utils/
│   │   ├── config.py           # Configuration management
│   │   ├── telegram.py         # Telegram notifications
│   │   └── logger.py           # Logging utilities
│   └── web/
│       ├── app.py              # FastAPI application
│       └── templates/          # Jinja2 HTML templates
├── config/
│   ├── config.yaml             # Main configuration
│   └── .env                    # Environment variables
├── profiles/                   # Multi-account profile data
├── systemd/                    # systemd service templates
├── setup.py                    # Package installation
└── README.md
```

---

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
| `fbposter web start` | Start the web dashboard |

---

## License

MIT License - see [LICENSE](LICENSE) for details.

## Disclaimer

This tool is for authorized automation only. Ensure compliance with Facebook's Terms of Service. The author is not responsible for account restrictions or violations.

---

## Author

**Yass Barona**
Full-Stack Developer

- GitHub: [@yassbarona](https://github.com/yassbarona)

---

## Acknowledgments

This project was developed with the assistance of [Claude Code](https://claude.ai/claude-code), Anthropic's AI-powered development tool.

---

*Built with Python, FastAPI, Selenium, and Tailwind CSS*
