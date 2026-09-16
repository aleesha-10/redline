import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import settings
from .db import purge_expired

logger = logging.getLogger("redline.ttl_worker")

scheduler = AsyncIOScheduler()


async def run_purge_job():
    purged = await purge_expired(settings.TTL_SECONDS)
    if purged:
        logger.info("TTL purge: removed %d expired raw_clauses rows", purged)


def start_scheduler():
    # Runs hourly; adjust to taste. Static-freshness data doesn't need to
    # refresh, but request logs still need lifecycle management per the
    # storage/lifecycle requirement.
    scheduler.add_job(run_purge_job, "interval", hours=1, id="ttl_purge")
    scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
