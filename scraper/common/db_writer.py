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
        short_description text,              -- AI-generated summary, filled in by backfill
        experience_min int,                  -- years, regex-extracted from description
        experience_max int,                  -- years, null means open-ended (e.g. "5+ years")
        status text not null default 'active',   -- 'active' | 'expired'
        expired_at timestamptz,              -- set the moment status flips to 'expired'
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
    alter table jobs add column if not exists expired_at timestamptz;
    alter table jobs add column if not exists experience_min int;
    alter table jobs add column if not exists experience_max int;
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta

from supabase import Client

from scraper.common.db import get_client
from scraper.common.logger import get_logger

log = get_logger(__name__)

BATCH_SIZE = 200  # keep individual requests small/predictable


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _chunk(items: List[Dict[str, Any]], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def upsert_jobs(jobs: List[Dict[str, Any]], client: Client | None = None) -> int:
    """Upsert normalized job dicts. Returns count of rows written.

    Dedupes by fingerprint first — Postgres rejects an upsert batch that
    would touch the same conflict-target row twice in one statement
    ('ON CONFLICT DO UPDATE command cannot affect row a second time'),
    which happens if a source's scrape captures the same job twice in one
    run. Last occurrence in the input wins.

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
        .update({"status": "expired", "expired_at": _now_iso()})
        .eq("fingerprint", fingerprint)
        .execute()
    )
    return bool(result.data)


def get_jobs_missing_summary(source: str, limit: int = 500, client: Client | None = None) -> List[Dict[str, Any]]:
    """Return active jobs for a source that already have a description but
    no short_description yet."""
    db = client or get_client()
    result = (
        db.table("jobs")
        .select("id, fingerprint, description, contact_email")
        .eq("source", source)
        .eq("status", "active")
        .not_.is_("description", "null")
        .is_("short_description", "null")
        .limit(limit)
        .execute()
    )
    return result.data or []


def get_jobs_missing_detail(source: str, limit: int = 500, client: Client | None = None) -> List[Dict[str, Any]]:
    """Return active jobs for a source that haven't had their detail page
    fetched yet. Filters on description IS NULL rather than contact_email
    IS NULL — description only stays null if the detail page was never
    successfully fetched at all; contact_email can legitimately stay null
    even after a successful fetch."""
    db = client or get_client()
    result = (
        db.table("jobs")
        .select("id, fingerprint, detail_url")
        .eq("source", source)
        .eq("status", "active")
        .is_("description", "null")
        .limit(limit)
        .execute()
    )
    return result.data or []


def update_job_detail(
    fingerprint: str,
    description: Optional[str],
    contact_email: Optional[str],
    short_description: Optional[str] = None,
    experience_min: Optional[int] = None,
    experience_max: Optional[int] = None,
    client: Client | None = None,
) -> bool:
    """Update one job row with detail-page results (and, if provided, an
    AI-generated short summary and/or a regex-extracted experience range).

    Same pattern as short_description: experience_min/experience_max are
    only written when the caller passes a non-None value. A description
    the extractor found nothing in just leaves the columns at their
    default null rather than us writing an explicit null over them."""
    db = client or get_client()
    values = {"description": description, "contact_email": contact_email}
    if short_description is not None:
        values["short_description"] = short_description
    if experience_min is not None:
        values["experience_min"] = experience_min
    if experience_max is not None:
        values["experience_max"] = experience_max

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
    'expired'."""
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
            .update({"status": "expired", "expired_at": _now_iso()})
            .in_("id", batch_ids)
            .execute()
        )
        updated += len(result.data) if getattr(result, "data", None) else len(batch_ids)

    log.info("Marked %s stale %s jobs as expired", updated, source)
    return updated


def delete_expired_jobs(older_than_days: int = 1, client: Client | None = None) -> int:
    """Permanently deletes jobs that have been 'expired' for more than
    older_than_days. NOTE: this is a hard delete — data is gone."""
    db = client or get_client()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()

    rows = (
        db.table("jobs")
        .select("id")
        .eq("status", "expired")
        .lt("expired_at", cutoff)
        .execute()
    ).data or []

    if not rows:
        log.info("No expired jobs older than %s day(s) to delete", older_than_days)
        return 0

    ids = [row["id"] for row in rows]
    deleted = 0
    for batch in _chunk([{"id": i} for i in ids], BATCH_SIZE):
        batch_ids = [row["id"] for row in batch]
        result = db.table("jobs").delete().in_("id", batch_ids).execute()
        deleted += len(result.data) if getattr(result, "data", None) else len(batch_ids)

    log.info("Deleted %s expired jobs older than %s day(s)", deleted, older_than_days)
    return deleted


def reset_descriptions_for_reformat(source: str, client: Client | None = None) -> int:
    """Nulls out `description` for every active job of a source, WITHOUT
    touching contact_email or short_description. Used one-time after an
    improvement to the description-extraction logic (see
    scraper/common/html_cleaner.py) — resetting description makes those
    rows reappear in get_jobs_missing_detail()'s queue, so the next
    backfill_details run re-fetches them with the fixed extraction.

    short_description is deliberately left alone: it's an AI-generated
    semantic summary of the content, not a rendering of its raw
    formatting, so it's still valid even though the raw description text
    it was based on was messier. Re-running the (rate-limited, slower)
    summary backfill isn't needed just to fix layout."""
    db = client or get_client()

    rows = (
        db.table("jobs")
        .select("id, fingerprint")
        .eq("source", source)
        .eq("status", "active")
        .not_.is_("description", "null")
        .execute()
    ).data or []

    if not rows:
        log.info("No %s jobs with a description to reset", source)
        return 0

    reset_count = 0
    for batch in _chunk(rows, BATCH_SIZE):
        ids = [row["id"] for row in batch]
        db.table("jobs").update({"description": None}).in_("id", ids).execute()
        reset_count += len(ids)

    log.info("Reset description for %s %s jobs — will re-fetch on next backfill run", reset_count, source)
    return reset_count