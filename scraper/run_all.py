"""
Single entrypoint that runs the entire pipeline in order: scrape -> detail
backfill -> summary backfill -> cleanup.

Job listings don't change hour to hour, so the default interval here is
days, not hours — run once today, then automatically again ~3 days later,
indefinitely, without needing cron/Task Scheduler set up separately.

Each step is isolated — if one throws, it's logged and the pipeline moves
on to the next step rather than aborting the whole run (same philosophy
as scheduler.py's per-source isolation).

Usage:
  python -m scraper.run_all                      # run once, then exit
  python -m scraper.run_all --forever             # run now, then every 3 days, forever
  python -m scraper.run_all --forever --interval-days 4   # custom interval

Leave this running in a terminal (or as a background/service process) for
--forever mode — closing the terminal stops it, same as any other script.
"""
import sys
import time
import argparse

from scraper.common.logger import get_logger
from scraper import scheduler
from scraper.infopark import backfill_details as infopark_backfill_details
from scraper.technopark import backfill_details as technopark_backfill_details
from scraper.infopark import backfill_summaries as infopark_backfill_summaries
from scraper.technopark import backfill_summaries as technopark_backfill_summaries
from scraper import cleanup_expired

log = get_logger(__name__)

# Each step: (name, callable). Order matters — detail backfill needs rows
# from the scrape step, summaries need descriptions from detail backfill,
# cleanup should run last so it only removes truly-stale data.
STEPS = [
    ("scrape_and_upsert", scheduler.run_once),
    ("infopark_backfill_details", infopark_backfill_details.run_backfill),
    ("technopark_backfill_details", technopark_backfill_details.run_backfill),
    ("infopark_backfill_summaries", infopark_backfill_summaries.run_summary_backfill),
    ("technopark_backfill_summaries", technopark_backfill_summaries.run_summary_backfill),
    ("cleanup_expired", lambda: cleanup_expired.run_cleanup(days=1)),
]

DEFAULT_INTERVAL_DAYS = 3


def run_all() -> dict:
    results = {}
    for name, step_fn in STEPS:
        log.info("=== Starting step: %s ===", name)
        try:
            results[name] = step_fn()
            log.info("=== Finished step: %s -> %s ===", name, results[name])
        except Exception as exc:  # noqa: BLE001 — isolate step failures
            log.error("Step %s failed entirely: %s", name, exc)
            results[name] = {"failed": True, "error": str(exc)}
    return results


def run_forever(interval_days: float = DEFAULT_INTERVAL_DAYS) -> None:
    """Runs run_all() immediately, then sleeps interval_days and repeats,
    forever. Keeps the process alive in a terminal/background job instead
    of relying on external scheduling (cron, Task Scheduler)."""
    interval_seconds = interval_days * 24 * 60 * 60
    log.info("Starting run_all loop, interval=%s day(s)", interval_days)
    while True:
        run_all()
        log.info("Sleeping %s day(s) until next run", interval_days)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--forever", action="store_true", help="run now, then repeat automatically")
    parser.add_argument("--interval-days", type=float, default=DEFAULT_INTERVAL_DAYS, help="days between runs in --forever mode")
    args = parser.parse_args()

    if args.forever:
        run_forever(interval_days=args.interval_days)
    else:
        outcome = run_all()
        if all(isinstance(r, dict) and r.get("failed") for r in outcome.values()):
            sys.exit(1)