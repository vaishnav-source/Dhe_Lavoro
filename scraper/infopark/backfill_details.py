"""
Backfills description + contact_email for Infopark jobs already in the DB
that don't have them yet. Deliberately a separate pass from the listing
scraper (scraper.py) rather than fetching detail pages inline during
pagination — listing scrape is cheap (24 requests total), but detail pages
are one request PER JOB (480+), so this only touches jobs that actually
still need it, and is safe to re-run repeatedly (already-filled jobs are
skipped by the DB query itself).

Usage: python -m scraper.infopark.backfill_details
"""
import sys

from scraper.common.db_writer import get_jobs_missing_detail, update_job_detail
from scraper.common.rate_limiter import polite_delay
from scraper.common.logger import get_logger
from scraper.common.ai_summarizer import summarize_job_description
from scraper.infopark.detail_scraper import fetch_job_detail

log = get_logger(__name__)

SOURCE_NAME = "infopark"


def run_backfill(limit: int = 500) -> dict:
    jobs = get_jobs_missing_detail(SOURCE_NAME, limit=limit)
    log.info("Found %s %s jobs missing detail info", len(jobs), SOURCE_NAME)

    updated = 0
    skipped_no_url = 0

    for job in jobs:
        detail_url = job.get("detail_url")
        if not detail_url:
            skipped_no_url += 1
            continue

        detail = fetch_job_detail(detail_url)
        short_description = summarize_job_description(detail["description"])
        update_job_detail(
            fingerprint=job["fingerprint"],
            description=detail["description"],
            contact_email=detail["contact_email"],
            short_description=short_description,
        )
        updated += 1
        polite_delay()

    stats = {"found": len(jobs), "updated": updated, "skipped_no_url": skipped_no_url}
    log.info("Backfill complete: %s", stats)
    return stats


if __name__ == "__main__":
    result = run_backfill()
    if result["updated"] == 0 and result["found"] > 0:
        sys.exit(1)
