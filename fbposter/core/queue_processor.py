"""
Queue processor for running jobs sequentially.
This module processes the job queue one job at a time.
"""

import subprocess
import time
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fbposter.data.storage import LogStore
from fbposter.utils.config import Config


def get_log_store(profile: str = None) -> LogStore:
    """Get the log store for the given profile"""
    config = Config(profile=profile)
    db_path = config.get_logs_dir() / "posts_history.db"
    return LogStore(db_path)


def process_queue(profile: str = None):
    """
    Process the job queue sequentially.
    Runs until all queued jobs are completed.
    """
    log_store = get_log_store(profile)

    # Log to file for debugging
    import datetime
    log_file = os.path.join(os.path.dirname(log_store.db_path), "queue_processor.log")
    def log(msg):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {msg}"
        print(line)
        with open(log_file, "a") as f:
            f.write(line + "\n")

    log(f"Starting queue processing for profile: {profile or 'default'}")

    # Clean up any stale "running" jobs from previous crashed processors
    # If we're starting fresh, any "running" queue items are orphaned
    stale_count = log_store.reset_stale_running_jobs()
    if stale_count > 0:
        log(f"Reset {stale_count} stale running job(s) from previous run")

    while True:
        # Check if a job is already running
        if log_store.is_queue_running():
            log("A job is already running, waiting...")
            time.sleep(5)
            continue

        # Get next job in queue
        next_job = log_store.get_next_queued_job()

        if not next_job:
            log("Queue is empty, exiting.")
            break

        queue_id = next_job['id']
        job_id = next_job['job_id']
        job_name = next_job['job_name']
        job_profile = next_job['profile']

        log(f"Starting job: {job_name} ({job_id})")

        # Mark as running
        log_store.start_queue_job(queue_id)

        # Build the command
        cmd = ["fbposter"]
        if job_profile:
            cmd.extend(["--profile", job_profile])
        cmd.extend(["run", job_id, "--no-headless"])

        log(f"Running command: {' '.join(cmd)}")

        try:
            # Run the job and wait for it to complete
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                log(f"Job completed successfully: {job_name}")
                log_store.complete_queue_job(queue_id)
            else:
                error_msg = result.stderr[:200] if result.stderr else "Unknown error"
                log(f"Job failed: {job_name} - {error_msg}")
                log_store.complete_queue_job(queue_id, error_msg)

        except Exception as e:
            error_msg = str(e)[:200]
            log(f"Error running job: {job_name} - {error_msg}")
            log_store.complete_queue_job(queue_id, error_msg)

        # Small delay between jobs
        time.sleep(2)

    # Clean up completed jobs from queue
    log_store.clear_completed_queue()
    log("Queue processing complete.")


def main():
    """Main entry point for CLI usage"""
    import argparse

    parser = argparse.ArgumentParser(description="Process the job queue")
    parser.add_argument("--profile", "-p", help="Profile to use")
    args = parser.parse_args()

    process_queue(args.profile)


if __name__ == "__main__":
    main()
