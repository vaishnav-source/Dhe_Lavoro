"""
Writes normalized job dicts (from infopark/scraper.py or technopark/scraper.py)
into Supabase's `jobs` table.

Schema assumed (create this table in Supabase SQL editor first):

    create table jobs (
        id bigint generated always as identity primary key,
        fingerprint text unique not null,   -- from common/dedup.py
        source text not null,
        source_job_id text not null,
        job_title text not null,
        company text not null,
        posted_date text,
        closing_date text,
        detail_url text,
        status text not null default 'active',   -- 'active' | 'expired'
        last_seen_at timestamptz not null default now(),
        created_at timestamptz not null default now()
    );

Upsert is keyed on `fingerprint` (unique constraint) — re-scraping the same
job updates last_seen_at/closing_date instead of creating a duplicate row.
"""
from typing import List, Dict, Any

from supabase import Client

from scraper.common.db import get_client
from scraper.common.logger import get_logger

log = get_logger(__name__)

BATCH_SIZE = 200  # keep individual requests small/predictable


def _chunk(items: List[Dict[str, Any]], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def upsert_jobs(jobs: List[Dict[str, Any]], client: Client | None = None) -> int:
    """Upsert normalized job dicts. Returns count of rows written.
    Batches requests so one large scrape run doesn't send a single giant
    payload (easier to retry a failed batch without resending everything)."""
    if not jobs:
        log.info("No jobs to write — skipping")
        return 0

    db = client or get_client()
    written = 0

    for batch in _chunk(jobs, BATCH_SIZE):
        rows = [
            {
                "fingerprint": job["fingerprint"],
                "source": job["source"],
                "source_job_id": job["source_job_id"],
                "job_title": job["job_title"],
                "company": job["company"],
                "posted_date": job.get("posted_date"),
                "closing_date": job.get("closing_date"),
                "detail_url": job.get("detail_url"),
                "status": "active",
            }
            for job in batch
        ]

        try:
            db.table("jobs").upsert(rows, on_conflict="fingerprint").execute()
            written += len(rows)
        except Exception as exc:  # noqa: BLE001
            log.error("Batch upsert failed (%s rows): %s", len(rows), exc)
            # continue with remaining batches rather than aborting the whole run
            continue

    log.info("Upserted %s/%s jobs", written, len(jobs))
    return written


def mark_stale_jobs_expired(source: str, seen_fingerprints: List[str], client: Client | None = None) -> int:
    """After a full scrape run for a source, mark any job still 'active' in
    the DB for that source but NOT present in this run's results as
    'expired' — covers listings the park removed before their stated
    deadline (see PRD data-lifecycle note)."""
    db = client or get_client()

    if not seen_fingerprints:
        log.warning("No fingerprints passed for %s — refusing to mark-all-expired as a safety guard", source)
        return 0

    result = (
        db.table("jobs")
        .update({"status": "expired"})
        .eq("source", source)
        .eq("status", "active")
        .not_.in_("fingerprint", seen_fingerprints)
        .execute()
    )
    count = len(result.data) if getattr(result, "data", None) else 0
    log.info("Marked %s stale %s jobs as expired", count, source)
    return count
