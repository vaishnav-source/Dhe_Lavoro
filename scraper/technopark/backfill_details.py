"""
Backfills description + contact_email + AI short_description for Technopark
jobs already in the DB that don't have them yet. Same scoping logic as
scraper/infopark/backfill_details.py — only touches jobs missing detail
info, safe to re-run repeatedly.

Usage: python -m scraper.technopark.backfill_details
"""
import sys

from scraper.common.db_writer import get_jobs_missing_detail, update_job_detail, mark_job_expired
from scraper.common.rate_limiter import polite_delay
from scraper.common.logger import get_logger
from scraper.common.ai_summarizer import summarize_job_description
from scraper.common.experience_extractor import extract_experience
from scraper.technopark.detail_scraper import fetch_job_detail

log = get_logger(__name__)

SOURCE_NAME = "technopark"


def run_backfill(limit: int = 500) -> dict:
    jobs = get_jobs_missing_detail(SOURCE_NAME, limit=limit)
    log.info("Found %s %s jobs missing detail info", len(jobs), SOURCE_NAME)

    updated = 0
    expired = 0
    skipped_no_url = 0

    for job in jobs:
        detail_url = job.get("detail_url")
        if not detail_url:
            skipped_no_url += 1
            continue

        detail = fetch_job_detail(detail_url)

        if detail.get("not_found"):
            # posting no longer exists on the live site — stop retrying it
            # on every future backfill run
            mark_job_expired(fingerprint=job["fingerprint"])
            expired += 1
            polite_delay()
            continue

        short_description = summarize_job_description(detail["description"])
        experience_min, experience_max = extract_experience(detail["description"])
        update_job_detail(
            fingerprint=job["fingerprint"],
            description=detail["description"],
            contact_email=detail["contact_email"],
            short_description=short_description,
            experience_min=experience_min,
            experience_max=experience_max,
        )
        updated += 1
        polite_delay()

    stats = {"found": len(jobs), "updated": updated, "expired": expired, "skipped_no_url": skipped_no_url}
    log.info("Backfill complete: %s", stats)
    return stats


if __name__ == "__main__":
    result = run_backfill()
    if result["updated"] == 0 and result["expired"] == 0 and result["found"] > 0:
        sys.exit(1)