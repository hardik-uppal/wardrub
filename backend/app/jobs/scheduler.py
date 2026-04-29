"""APScheduler setup for background jobs."""

import asyncio
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.logging_config import get_logger

logger = get_logger("scheduler")

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def setup_scheduler(
    daily_looks_hour: int = 6,
    daily_looks_minute: int = 0,
    timezone: str = "UTC"
) -> AsyncIOScheduler:
    """
    Set up the APScheduler with all background jobs.
    
    Args:
        daily_looks_hour: Hour to run daily looks generation (0-23)
        daily_looks_minute: Minute to run daily looks generation (0-59)
        timezone: Timezone for scheduling
    
    Returns:
        Configured AsyncIOScheduler
    """
    scheduler = get_scheduler()
    
    # Import job functions here to avoid circular imports
    # from app.jobs.daily_looks_generator import run_daily_looks_job
    
    # Remove existing jobs (for reloading)
    scheduler.remove_all_jobs()
    
    # Daily looks generation job - DISABLED (only runs for default_user, not all users)
    # TODO: Re-enable once updated to run for all active users
    # scheduler.add_job(
    #     run_daily_looks_job,
    #     trigger=CronTrigger(
    #         hour=daily_looks_hour,
    #         minute=daily_looks_minute,
    #         timezone=timezone
    #     ),
    #     id="daily_looks_job",
    #     name="Generate Daily Outfit Looks",
    #     replace_existing=True,
    #     max_instances=1,  # Prevent overlapping runs
    #     coalesce=True     # If missed, only run once
    # )
    
    logger.info(
        f"Scheduler configured: daily looks job at {daily_looks_hour:02d}:{daily_looks_minute:02d} {timezone}"
    )
    
    return scheduler


def start_scheduler():
    """Start the scheduler if not already running."""
    scheduler = get_scheduler()
    
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")
        
        # Log all scheduled jobs
        jobs = scheduler.get_jobs()
        for job in jobs:
            logger.info(f"  - {job.name}: {job.trigger}")
    else:
        logger.info("Scheduler already running")


def stop_scheduler():
    """Stop the scheduler gracefully."""
    global _scheduler
    
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")
    
    _scheduler = None


async def trigger_job_now(job_id: str) -> bool:
    """
    Trigger a scheduled job to run immediately.
    
    Args:
        job_id: The job ID to trigger
    
    Returns:
        True if job was triggered, False if not found
    """
    scheduler = get_scheduler()
    job = scheduler.get_job(job_id)
    
    if job:
        job.modify(next_run_time=None)  # Reset next run time
        scheduler.modify_job(job_id, next_run_time=asyncio.get_event_loop().time())
        logger.info(f"Triggered job {job_id} to run immediately")
        return True
    else:
        logger.warning(f"Job {job_id} not found")
        return False


def get_job_status() -> dict:
    """
    Get status of all scheduled jobs.
    
    Returns:
        Dictionary with job statuses
    """
    scheduler = get_scheduler()
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    return {
        "running": scheduler.running,
        "jobs": jobs
    }

