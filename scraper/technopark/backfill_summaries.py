"""
Backfills only the AI short_description for Technopark jobs that already
have a description + contact_email stored but no summary yet. Same logic
as scraper/infopark/backfill_summaries.py — no re-fetching detail pages.

Usage: python -m scraper.technopark.backfill_summaries
"""
import sys
import time

from scraper.common.db_writer import get_jobs_missing_summary, update_job_detail
from scraper.common.ai_summarizer import summarize_job_description
from scraper.common.logger import get_logger

log = get_logger(__name__)

SOURCE_NAME = "technopark"

# 5s spacing keeps us safely under Groq's 20,000 TPM free-tier limit
# (measured, not just its 30 RPM cap) even with the reduced input size.
CALL_DELAY_SECONDS = 5


def run_summary_backfill(limit: int = 500) -> dict:
    jobs = get_jobs_missing_summary(SOURCE_NAME, limit=limit)
    log.info("Found %s %s jobs missing a summary", len(jobs), SOURCE_NAME)

    updated = 0
    for job in jobs:
        short_description = summarize_job_description(job.get("description"))
        if short_description is None:
            time.sleep(CALL_DELAY_SECONDS)
            continue
        update_job_detail(
            fingerprint=job["fingerprint"],
            description=job.get("description"),
            contact_email=job.get("contact_email"),
            short_description=short_description,
        )
        updated += 1
        time.sleep(CALL_DELAY_SECONDS)

    stats = {"found": len(jobs), "updated": updated}
    log.info("Summary backfill complete: %s", stats)
    return stats


if __name__ == "__main__":
    result = run_summary_backfill()
    if result["updated"] == 0 and result["found"] > 0:
        sys.exit(1)