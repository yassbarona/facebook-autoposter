# systemd Service Templates

## Installation

Copy the service and timer files to the systemd directory:

```bash
sudo cp systemd/fbposter@.service /etc/systemd/system/
sudo cp systemd/fbposter@.timer /etc/systemd/system/
sudo systemctl daemon-reload
```

## Usage

### Enable a job timer

Replace `<job-id>` with your actual job ID from `fbposter jobs list`:

```bash
# Enable timer (starts on boot)
sudo systemctl enable fbposter@<job-id>.timer

# Start timer immediately
sudo systemctl start fbposter@<job-id>.timer

# Check timer status
systemctl list-timers fbposter*
```

### View logs

```bash
# Follow job logs in real-time
journalctl -u fbposter@<job-id> -f

# View recent logs
journalctl -u fbposter@<job-id> -n 50
```

### Manual run

```bash
# Run job manually
sudo systemctl start fbposter@<job-id>.service
```

### Disable timer

```bash
sudo systemctl stop fbposter@<job-id>.timer
sudo systemctl disable fbposter@<job-id>.timer
```

## Customizing Schedule

Edit `/etc/systemd/system/fbposter@<job-id>.timer` and modify the `OnCalendar` line:

```ini
# Daily at 08:00
OnCalendar=*-*-* 08:00:00

# Daily at 08:00 and 20:00
OnCalendar=*-*-* 08:00:00
OnCalendar=*-*-* 20:00:00

# Every 6 hours
OnCalendar=*-*-* 00/6:00:00

# Monday-Friday at 09:00
OnCalendar=Mon-Fri *-*-* 09:00:00
```

After editing, reload systemd:

```bash
sudo systemctl daemon-reload
sudo systemctl restart fbposter@<job-id>.timer
```
