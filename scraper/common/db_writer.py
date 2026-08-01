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
        description text,                    -- filled in by detail-page backfill
        contact_email text,                  -- filled in by detail-page backfill
        short_description text,              -- AI-generated summary (Groq), filled in by backfill
        status text not null default 'active',   -- 'active' | 'expired'
        last_seen_at timestamptz not null default now(),
        created_at timestamptz not null default now()
    );

Upsert is keyed on `fingerprint` (unique constraint) — re-scraping the same
job updates last_seen_at/closing_date instead of creating a duplicate row.

If you already created the `jobs` table before description/contact_email
existed, run this migration instead of recreating the table:

    alter table jobs add column if not exists description text;
    alter table jobs add column if not exists contact_email text;
    alter table jobs add column if not exists short_description text;
"""
from typing import List, Dict, Any, Optional

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

    Dedupes by fingerprint first — Postgres rejects an upsert batch that
    would touch the same conflict-target row twice in one statement
    ('ON CONFLICT DO UPDATE command cannot affect row a second time'),
    which happens if a source's scrape captures the same job twice in one
    run (e.g. Technopark's infinite-scroll re-showing a job across two
    page snapshots if the underlying listing shifted mid-scrape). Last
    occurrence in the input wins.

    Also batches requests so one large scrape run doesn't send a single
    giant payload (easier to retry a failed batch without resending
    everything)."""
    if not jobs:
        log.info("No jobs to write — skipping")
        return 0

    deduped = list({job["fingerprint"]: job for job in jobs}.values())
    if len(deduped) < len(jobs):
        log.warning("Deduped %s duplicate-fingerprint rows before upsert", len(jobs) - len(deduped))

    db = client or get_client()
    written = 0

    for batch in _chunk(deduped, BATCH_SIZE):
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

    log.info("Upserted %s/%s jobs (%s duplicates removed)", written, len(deduped), len(jobs) - len(deduped))
    return written


def mark_job_expired(fingerprint: str, client: Client | None = None) -> bool:
    """Mark one job expired by fingerprint — used when a detail-page fetch
    returns a genuine 404 (posting removed from the live site), so the
    backfill process stops retrying a dead URL on every future run."""
    db = client or get_client()
    result = (
        db.table("jobs")
        .update({"status": "expired"})
        .eq("fingerprint", fingerprint)
        .execute()
    )
    return bool(result.data)


def get_jobs_missing_detail(source: str, limit: int = 500, client: Client | None = None) -> List[Dict[str, Any]]:
    """Return active jobs for a source that don't have a contact_email yet
    — these are the ones worth spending a detail-page fetch on. Capped
    with a limit so one call can't accidentally try to pull an unbounded
    number of rows into memory."""
    db = client or get_client()
    result = (
        db.table("jobs")
        .select("id, fingerprint, detail_url")
        .eq("source", source)
        .eq("status", "active")
        .is_("contact_email", "null")
        .limit(limit)
        .execute()
    )
    return result.data or []


def update_job_detail(
    fingerprint: str,
    description: Optional[str],
    contact_email: Optional[str],
    short_description: Optional[str] = None,
    client: Client | None = None,
) -> bool:
    """Update one job row with detail-page results (and, if provided, an
    AI-generated short summary). Returns True if a row was actually
    updated (lets the caller distinguish 'nothing found on the page' from
    'the fingerprint didn't match any row')."""
    db = client or get_client()
    values = {"description": description, "contact_email": contact_email}
    if short_description is not None:
        values["short_description"] = short_description

    result = (
        db.table("jobs")
        .update(values)
        .eq("fingerprint", fingerprint)
        .execute()
    )
    return bool(result.data)


def mark_stale_jobs_expired(source: str, seen_fingerprints: List[str], client: Client | None = None) -> int:
    """After a full scrape run for a source, mark any job still 'active' in
    the DB for that source but NOT present in this run's results as
    'expired' — covers listings the park removed before their stated
    deadline (see PRD data-lifecycle note).

    Implementation note: this deliberately does NOT send a giant `NOT IN
    (...)` filter with hundreds of fingerprints in one request — PostgREST
    rejects overly long query strings built that way (seen in practice:
    a 480-item NOT IN caused a 400 "JSON could not be generated" error).
    Instead it fetches the currently-active rows for this source, computes
    the stale set in Python, and only sends the (usually much smaller)
    list of ids that actually need updating — chunked as an extra safety
    margin in case that list is itself large.
    """
    db = client or get_client()

    if not seen_fingerprints:
        log.warning("No fingerprints passed for %s — refusing to mark-all-expired as a safety guard", source)
        return 0

    seen_set = set(seen_fingerprints)

    active_rows = (
        db.table("jobs")
        .select("id, fingerprint")
        .eq("source", source)
        .eq("status", "active")
        .execute()
    ).data or []

    stale_ids = [row["id"] for row in active_rows if row["fingerprint"] not in seen_set]

    if not stale_ids:
        log.info("No stale %s jobs to expire", source)
        return 0

    updated = 0
    for batch in _chunk([{"id": i} for i in stale_ids], BATCH_SIZE):
        batch_ids = [row["id"] for row in batch]
        result = (
            db.table("jobs")
            .update({"status": "expired"})
            .in_("id", batch_ids)
            .execute()
        )
        updated += len(result.data) if getattr(result, "data", None) else len(batch_ids)

    log.info("Marked %s stale %s jobs as expired", updated, source)
    return updated