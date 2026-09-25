"""
Deletes jobs that have been 'expired' for more than 1 day.

This is a hard delete — permanent, no undo. Run this manually or on a
schedule (e.g. daily cron) once you're comfortable with the tradeoff:
deleted jobs disappear from any user's application history too, and the
trend/history value discussed in the PRD is lost for those rows. Rows
stay in the DB indefinitely until this is run — nothing deletes them
automatically otherwise.

Usage: python -m scraper.cleanup_expired [--days N]
"""

import argparse

from scraper.common.db_writer import delete_expired_jobs
from scraper.common.logger import get_logger

log = get_logger(__name__)


def run_cleanup(days: int = 1) -> int:
    deleted = delete_expired_jobs(older_than_days=days)
    log.info("Cleanup complete: deleted %s jobs expired more than %s day(s) ago", deleted, days)
    return deleted


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=1, help="delete jobs expired longer than this many days ago")
    args = parser.parse_args()
    run_cleanup(days=args.days)