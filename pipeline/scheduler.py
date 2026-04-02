"""
pipeline/scheduler.py
Always-on heartbeat of the CSX AI Intelligence Engine.
Fires run_pipeline.py every Monday at 7AM UTC automatically.

WHY APScheduler over system cron?
- Runs entirely inside Docker = fully sandboxed
- Logs appear in docker logs = easy monitoring  
- Cross-platform = same on Windows Docker and Linux servers
- Recovers missed runs via misfire_grace_time
"""

import sys
import logging
import subprocess
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SCHEDULER] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)


def run_pipeline():
    """
    Called by the scheduler every Monday at 7AM UTC.
    WHY subprocess? If the pipeline crashes, the scheduler stays alive
    and retries next week. Fault isolation is a professional pattern.
    """
    log.info("=" * 55)
    log.info("SCHEDULED PIPELINE RUN STARTING")
    log.info(f"Timestamp: {datetime.utcnow().isoformat()}Z")
    log.info("=" * 55)

    result = subprocess.run(
        [sys.executable, "/app/pipeline/run_pipeline.py"],
        capture_output=False    # Stream logs live to docker logs
    )

    if result.returncode == 0:
        log.info("PIPELINE COMPLETED SUCCESSFULLY")
    else:
        log.error(f"PIPELINE FAILED with exit code {result.returncode}")


def main():
    scheduler = BlockingScheduler(timezone="UTC")

    # WHY Monday 7AM UTC?
    # Your CSX Lead arrives Monday morning with the digest already waiting.
    # UTC avoids daylight saving time confusion across time zones.
    scheduler.add_job(
        run_pipeline,
        trigger=CronTrigger(day_of_week="mon", hour=7, minute=0),
        id="weekly_intel_digest",
        name="CSX Weekly AI Intelligence Digest",
        # WHY misfire_grace_time=3600?
        # If Docker was down at exactly 7AM, the job still runs
        # within 1 hour of the scheduled time when Docker recovers.
        misfire_grace_time=3600
    )

    log.info("CSX AI Intelligence Engine — Scheduler online")
    log.info("Pipeline scheduled: Every Monday at 07:00 UTC")
    log.info("Running pipeline NOW for immediate smoke test...")
    log.info("")

    # Run once immediately on startup so you can verify the full
    # pipeline works right now without waiting until Monday
    run_pipeline()

    log.info("Smoke test complete. Handing over to weekly schedule.")
    log.info("Container will stay alive and fire automatically each Monday.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped cleanly.")


if __name__ == "__main__":
    main()
