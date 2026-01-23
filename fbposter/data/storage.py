"""
Data storage layer for Facebook Auto-Poster
Handles JSON file operations and SQLite database for logs
Supports profile-based data isolation
"""
import json
import sqlite3
import os
import shutil
from typing import List, Optional, Dict
from pathlib import Path
from datetime import datetime

from .models import Group, Text, Job, PostLog
from ..utils.config import get_config


class DataStore:
    """Manages persistent storage of groups, texts, and jobs"""

    def __init__(self, data_dir: str = None, profile: str = None):
        if data_dir is None:
            # Use config to get profile-aware data directory
            config = get_config()
            data_dir = config.get_data_dir()
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.groups_file = self.data_dir / "groups.json"
        self.texts_file = self.data_dir / "texts.json"
        self.jobs_file = self.data_dir / "jobs.json"

        # Ensure files exist
        for file in [self.groups_file, self.texts_file, self.jobs_file]:
            if not file.exists():
                self._write_json(file, [])

    def _write_json(self, file_path: Path, data: any, backup: bool = True):
        """Atomic write with optional backup"""
        if backup and file_path.exists():
            backup_path = file_path.with_suffix('.json.backup')
            shutil.copy2(file_path, backup_path)

        # Write to temp file first
        temp_path = file_path.with_suffix('.json.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Atomic rename
        temp_path.replace(file_path)

    def _read_json(self, file_path: Path) -> any:
        """Read JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    # Groups management
    def load_groups(self) -> List[Group]:
        """Load all groups"""
        data = self._read_json(self.groups_file)
        return [Group.from_dict(g) for g in data]

    def save_groups(self, groups: List[Group]):
        """Save all groups"""
        data = [g.to_dict() for g in groups]
        self._write_json(self.groups_file, data)

    def add_group(self, group: Group):
        """Add a new group"""
        groups = self.load_groups()
        groups.append(group)
        self.save_groups(groups)

    def remove_group(self, group_id: str) -> bool:
        """Remove a group by ID"""
        groups = self.load_groups()
        filtered = [g for g in groups if g.id != group_id]
        if len(filtered) < len(groups):
            self.save_groups(filtered)
            return True
        return False

    def get_group(self, group_id: str) -> Optional[Group]:
        """Get a group by ID (supports partial ID matching)"""
        groups = self.load_groups()
        # Try exact match first
        for g in groups:
            if g.id == group_id:
                return g
        # Try partial match if no exact match
        matches = [g for g in groups if g.id.startswith(group_id)]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            # Multiple matches - return None to signal ambiguity
            return None
        return None

    def get_groups_for_job(self, job: Job) -> List[Group]:
        """Get groups matching job filters"""
        all_groups = self.load_groups()
        filters = job.group_filters

        # Filter by city_keys (city-language combinations like "Paris-es", "Frankfurt")
        city_keys = filters.get('cities', [])
        if city_keys:
            all_groups = [g for g in all_groups if g.city_key in city_keys]

        # Filter by active status
        if filters.get('active_only', True):
            all_groups = [g for g in all_groups if g.active]

        return all_groups

    # Texts management
    def load_texts(self) -> List[Text]:
        """Load all text templates"""
        data = self._read_json(self.texts_file)
        return [Text.from_dict(t) for t in data]

    def save_texts(self, texts: List[Text]):
        """Save all text templates"""
        data = [t.to_dict() for t in texts]
        self._write_json(self.texts_file, data)

    def add_text(self, text: Text):
        """Add a new text template"""
        texts = self.load_texts()
        texts.append(text)
        self.save_texts(texts)

    def remove_text(self, text_id: str) -> bool:
        """Remove a text template by ID"""
        texts = self.load_texts()
        filtered = [t for t in texts if t.id != text_id]
        if len(filtered) < len(texts):
            self.save_texts(filtered)
            return True
        return False

    def get_text(self, text_id: str) -> Optional[Text]:
        """Get a text template by ID (supports partial ID matching)"""
        texts = self.load_texts()
        # Try exact match first
        for t in texts:
            if t.id == text_id:
                return t
        # Try partial match if no exact match
        matches = [t for t in texts if t.id.startswith(text_id)]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            # Multiple matches - return None to signal ambiguity
            return None
        return None

    # Jobs management
    def load_jobs(self) -> List[Job]:
        """Load all jobs"""
        data = self._read_json(self.jobs_file)
        return [Job.from_dict(j) for j in data]

    def save_jobs(self, jobs: List[Job]):
        """Save all jobs"""
        data = [j.to_dict() for j in jobs]
        self._write_json(self.jobs_file, data)

    def add_job(self, job: Job):
        """Add a new job"""
        jobs = self.load_jobs()
        jobs.append(job)
        self.save_jobs(jobs)

    def remove_job(self, job_id: str) -> bool:
        """Remove a job by ID"""
        jobs = self.load_jobs()
        filtered = [j for j in jobs if j.id != job_id]
        if len(filtered) < len(jobs):
            self.save_jobs(filtered)
            return True
        return False

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID (supports partial ID matching)"""
        jobs = self.load_jobs()
        # Try exact match first
        for j in jobs:
            if j.id == job_id:
                return j
        # Try partial match if no exact match
        matches = [j for j in jobs if j.id.startswith(job_id)]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            # Multiple matches - return None to signal ambiguity
            return None
        return None

    def update_job(self, job: Job):
        """Update an existing job"""
        jobs = self.load_jobs()
        for i, j in enumerate(jobs):
            if j.id == job.id:
                jobs[i] = job
                self.save_jobs(jobs)
                return True
        return False


class LogStore:
    """Manages SQLite database for posting logs"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use config to get profile-aware logs directory
            config = get_config()
            logs_dir = config.get_logs_dir()
            logs_dir.mkdir(parents=True, exist_ok=True)
            db_path = logs_dir / "posts_history.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS post_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                job_id TEXT,
                text_id TEXT,
                group_id TEXT,
                group_url TEXT,
                city TEXT,
                status TEXT,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                duration_ms INTEGER
            )
        ''')

        # Create indexes for common queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON post_log(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_id ON post_log(job_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON post_log(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_city ON post_log(city)')

        # Job runs table for tracking running/completed jobs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                job_name TEXT,
                profile TEXT,
                status TEXT DEFAULT 'running',
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                total_groups INTEGER DEFAULT 0,
                successful INTEGER DEFAULT 0,
                failed INTEGER DEFAULT 0,
                error_message TEXT,
                pid INTEGER
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_runs_status ON job_runs(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_runs_started ON job_runs(started_at)')

        # Add pid column if it doesn't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE job_runs ADD COLUMN pid INTEGER')
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Job queue table for tracking queued jobs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                job_name TEXT,
                profile TEXT,
                status TEXT DEFAULT 'queued',
                position INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                started_at DATETIME,
                completed_at DATETIME,
                error_message TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_queue_status ON job_queue(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_queue_position ON job_queue(position)')

        conn.commit()
        conn.close()

    def add_log(self, log: PostLog):
        """Add a post log entry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO post_log
            (timestamp, job_id, text_id, group_id, group_url, city, status, error_message, retry_count, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            log.timestamp.isoformat(),
            log.job_id,
            log.text_id,
            log.group_id,
            log.group_url,
            log.city,
            log.status,
            log.error_message,
            log.retry_count,
            log.duration_ms
        ))

        conn.commit()
        conn.close()

    def get_recent_logs(self, limit: int = 100) -> List[Dict]:
        """Get recent log entries"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM post_log
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_logs_by_job(self, job_id: str, limit: int = 100) -> List[Dict]:
        """Get logs for a specific job"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM post_log
            WHERE job_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (job_id, limit))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_success_rate(self, days: int = 7) -> Dict:
        """Calculate success rate for last N days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped
            FROM post_log
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
        ''', (days,))

        row = cursor.fetchone()
        conn.close()

        total, successful, failed, skipped = row
        return {
            'total': total or 0,
            'successful': successful or 0,
            'failed': failed or 0,
            'skipped': skipped or 0,
            'success_rate': (successful / total * 100) if total > 0 else 0
        }

    def start_job_run(self, job_id: str, job_name: str, profile: str = None, total_groups: int = 0) -> int:
        """Record the start of a job run, returns the run ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO job_runs (job_id, job_name, profile, status, total_groups)
            VALUES (?, ?, ?, 'running', ?)
        ''', (job_id, job_name, profile, total_groups))

        run_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return run_id

    def complete_job_run(self, run_id: int, successful: int, failed: int, error_message: str = None):
        """Mark a job run as completed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        status = 'completed' if error_message is None else 'failed'
        cursor.execute('''
            UPDATE job_runs
            SET status = ?, completed_at = CURRENT_TIMESTAMP,
                successful = ?, failed = ?, error_message = ?
            WHERE id = ?
        ''', (status, successful, failed, error_message, run_id))

        conn.commit()
        conn.close()

    def get_recent_job_runs(self, limit: int = 20) -> List[Dict]:
        """Get recent job runs"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM job_runs
            ORDER BY started_at DESC
            LIMIT ?
        ''', (limit,))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_running_jobs(self) -> List[Dict]:
        """Get currently running jobs"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM job_runs
            WHERE status = 'running'
            ORDER BY started_at DESC
        ''')

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def update_job_run_pid(self, run_id: int, pid: int):
        """Update the PID of a running job"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE job_runs SET pid = ? WHERE id = ?
        ''', (pid, run_id))

        conn.commit()
        conn.close()

    def update_job_run_groups(self, run_id: int, total_groups: int):
        """Update the total groups count for a job run"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE job_runs SET total_groups = ? WHERE id = ?
        ''', (total_groups, run_id))

        conn.commit()
        conn.close()

    def get_job_run(self, run_id: int) -> Dict:
        """Get a specific job run by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM job_runs WHERE id = ?', (run_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def kill_job_run(self, run_id: int):
        """Mark a job run as killed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE job_runs
            SET status = 'killed', completed_at = CURRENT_TIMESTAMP, error_message = 'Killed by user'
            WHERE id = ?
        ''', (run_id,))

        conn.commit()
        conn.close()

    # ============== Job Queue Methods ==============

    def add_to_queue(self, job_id: str, job_name: str, profile: str = None) -> int:
        """Add a job to the queue, returns the queue entry ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get the next position in queue
        cursor.execute('SELECT COALESCE(MAX(position), 0) + 1 FROM job_queue WHERE status IN ("queued", "running")')
        position = cursor.fetchone()[0]

        cursor.execute('''
            INSERT INTO job_queue (job_id, job_name, profile, status, position)
            VALUES (?, ?, ?, 'queued', ?)
        ''', (job_id, job_name, profile, position))

        queue_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return queue_id

    def get_queue(self) -> List[Dict]:
        """Get all queued and running jobs in the queue"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM job_queue
            WHERE status IN ('queued', 'running')
            ORDER BY position ASC
        ''')

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_next_queued_job(self) -> Dict:
        """Get the next job in queue that's waiting to run"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM job_queue
            WHERE status = 'queued'
            ORDER BY position ASC
            LIMIT 1
        ''')

        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def is_queue_running(self) -> bool:
        """Check if any job in the queue is currently running"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM job_queue WHERE status = "running"')
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def start_queue_job(self, queue_id: int):
        """Mark a queued job as running"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE job_queue
            SET status = 'running', started_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (queue_id,))

        conn.commit()
        conn.close()

    def complete_queue_job(self, queue_id: int, error_message: str = None):
        """Mark a queued job as completed or failed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        status = 'failed' if error_message else 'completed'
        cursor.execute('''
            UPDATE job_queue
            SET status = ?, completed_at = CURRENT_TIMESTAMP, error_message = ?
            WHERE id = ?
        ''', (status, error_message, queue_id))

        conn.commit()
        conn.close()

    def clear_completed_queue(self):
        """Remove completed/failed jobs from queue"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM job_queue WHERE status IN ("completed", "failed")')

        conn.commit()
        conn.close()

    def clear_all_queue(self):
        """Clear the entire queue (use with caution)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM job_queue')

        conn.commit()
        conn.close()

    def reset_stale_running_jobs(self, timeout_minutes: int = 30) -> int:
        """Reset queue jobs that have been 'running' for too long.

        This is called when the queue processor starts to clean up orphaned
        jobs from previous crashed/killed processors.

        Args:
            timeout_minutes: Jobs running longer than this are considered stale

        Returns the number of jobs that were reset.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Mark stale running jobs as failed (they were interrupted or hung)
        # Only reset jobs that have been running for longer than the timeout
        cursor.execute('''
            UPDATE job_queue
            SET status = 'failed',
                completed_at = CURRENT_TIMESTAMP,
                error_message = 'Timed out or interrupted'
            WHERE status = 'running'
            AND started_at < datetime('now', '-' || ? || ' minutes')
        ''', (timeout_minutes,))

        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected
