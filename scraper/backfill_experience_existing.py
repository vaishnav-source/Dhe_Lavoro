"""
One-off migration: backfills experience_min/experience_max for jobs that
already have a `description` (i.e. already went through backfill_details.py
at some point) but never got experience extracted from it.

Why this is needed: backfill_details.py only processes jobs where
`description IS NULL` (get_jobs_missing_detail). Any job scraped/backfilled
BEFORE the experience feature existed already has a description, so it's
invisible to that backfill forever — its experience_min/max just stay NULL,
and GET /api/jobs?exp_min=&exp_max= silently excludes it.

No network requests needed — this re-runs the (free, local) regex extractor
against description text that's already sitting in the DB.

Safe to re-run: only touches rows where experience_min IS NULL, and only
writes a value when the regex actually finds a match.

Usage:
    python -m scraper.backfill_experience_existing            # both sources
    python -m scraper.backfill_experience_existing infopark   # one source
"""
import sys

from scraper.common.db import get_client
from scraper.common.db_writer import update_job_detail
from scraper.common.experience_extractor import extract_experience
from scraper.common.logger import get_logger

log = get_logger(__name__)

SOURCES = ["infopark", "technopark"]

# One-shot fetch rather than offset-paginated: matched rows drop out of the
# `experience_min IS NULL` filter as we update them, so an incrementing
# offset would skip rows that shift into an earlier page mid-run. A single
# generous limit sidesteps that; bump it if a source has more active jobs
# than this.
FETCH_LIMIT = 10000


def backfill_source(source: str) -> dict:
    db = get_client()

    rows = (
        db.table("jobs")
        .select("id, fingerprint, description, contact_email")
        .eq("source", source)
        .eq("status", "active")
        .not_.is_("description", "null")
        .is_("experience_min", "null")
        .limit(FETCH_LIMIT)
        .execute()
    ).data or []

    log.info("Found %s %s jobs with description but no experience_min", len(rows), source)

    updated = 0
    no_match = 0

    for job in rows:
        exp_min, exp_max = extract_experience(job["description"])
        if exp_min is None:
            no_match += 1
            continue

        update_job_detail(
            fingerprint=job["fingerprint"],
            description=job["description"],       # unchanged, re-passed as-is
            contact_email=job.get("contact_email"),  # unchanged, re-passed as-is
            experience_min=exp_min,
            experience_max=exp_max,
            client=db,
        )
        updated += 1

    stats = {"source": source, "found": len(rows), "updated": updated, "no_match": no_match}
    log.info("Experience backfill complete: %s", stats)
    return stats


if __name__ == "__main__":
    targets = [sys.argv[1]] if len(sys.argv) > 1 else SOURCES
    results = [backfill_source(src) for src in targets]
    for r in results:
        print(r)