"""
Orchestrates a full scrape-and-store cycle across all active sources.

Usage:
  - Cron (recommended for simplicity): add a crontab entry that runs
      python -m scraper.scheduler
    every few hours, e.g.:
      0 */4 * * *  cd /path/to/job-aggregator && /path/to/venv/bin/python -m scraper.scheduler >> logs/scheduler.log 2>&1

  - Or run continuously via APScheduler (see run_forever() below) if you'd
    rather have one long-running process instead of relying on system cron.
"""
import sys
import time
from typing import Callable, List, Dict, Any

from scraper.common.logger import get_logger
from scraper.common.db_writer import upsert_jobs, mark_stale_jobs_expired
from scraper.infopark.scraper import scrape_all_pages as scrape_infopark
from scraper.technopark.scraper import scrape_all_pages as scrape_technopark

log = get_logger(__name__)

# Each entry: (source_name, scrape_function). Add Cyberpark here in Phase 2
# without touching the run loop below.
SOURCES: List[tuple[str, Callable[[], List[Dict[str, Any]]]]] = [
    ("infopark", scrape_infopark),
    ("technopark", scrape_technopark),
]


def run_source(source_name: str, scrape_fn: Callable[[], List[Dict[str, Any]]]) -> Dict[str, int]:
    """Scrape one source end-to-end: fetch -> upsert -> expire stale rows.
    A failure here is caught and logged, not raised, so one broken source
    (e.g. site redesign) never prevents the others from running."""
    log.info("=== Starting scrape: %s ===", source_name)
    stats = {"scraped": 0, "written": 0, "expired": 0, "failed": False}

    try:
        jobs = scrape_fn()
        stats["scraped"] = len(jobs)

        written = upsert_jobs(jobs)
        stats["written"] = written

        fingerprints = [job["fingerprint"] for job in jobs]
        expired = mark_stale_jobs_expired(source_name, fingerprints)
        stats["expired"] = expired

    except Exception as exc:  # noqa: BLE001 — isolate per-source failures
        log.error("Source %s failed entirely: %s", source_name, exc)
        stats["failed"] = True

    log.info(
        "=== Finished %s: scraped=%s written=%s expired=%s failed=%s ===",
        source_name, stats["scraped"], stats["written"], stats["expired"], stats["failed"],
    )
    return stats


def run_once() -> Dict[str, Dict[str, int]]:
    """Run every configured source once, sequentially. Returns per-source
    stats so a caller (or a monitoring/alerting layer later) can inspect
    results without re-parsing logs."""
    results = {}
    for source_name, scrape_fn in SOURCES:
        results[source_name] = run_source(source_name, scrape_fn)
    return results


def run_forever(interval_seconds: int = 4 * 60 * 60) -> None:
    """Optional alternative to cron — loops run_once() forever with a fixed
    sleep interval. Only use this if you specifically want one long-lived
    process (e.g. a small VM/container) instead of relying on system cron."""
    log.info("Starting scheduler loop, interval=%ss", interval_seconds)
    while True:
        run_once()
        time.sleep(interval_seconds)


if __name__ == "__main__":
    if "--forever" in sys.argv:
        run_forever()
    else:
        results = run_once()
        # non-zero exit if every source failed, so cron/monitoring can flag it
        if all(r["failed"] for r in results.values()):
            sys.exit(1)
