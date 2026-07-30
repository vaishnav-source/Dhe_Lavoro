from typing import List

from scraper.common.config import INFOPARK_BASE_URL, INFOPARK_MAX_PAGES
from scraper.common.http_client import safe_get
from scraper.common.rate_limiter import polite_delay
from scraper.common.dedup import make_job_fingerprint
from scraper.common.logger import get_logger
from scraper.infopark.parser import parse_job_listing_page, InfoparkJob

log = get_logger(__name__)

SOURCE_NAME = "infopark"


def scrape_all_pages(max_pages: int = INFOPARK_MAX_PAGES) -> List[dict]:
    """Scrape every Infopark job-listing page and return normalized dicts
    ready for DB upsert (fingerprint included for dedup)."""
    all_jobs: List[InfoparkJob] = []

    for page in range(1, max_pages + 1):
        url = f"{INFOPARK_BASE_URL}?page={page}"
        try:
            resp = safe_get(url)
        except Exception as exc:  # noqa: BLE001 — log and continue, one bad
            # page should never abort the whole run
            log.warning("Failed to fetch page %s: %s", page, exc)
            continue

        page_jobs = parse_job_listing_page(resp.text)
        if not page_jobs:
            log.info("Page %s returned 0 jobs — stopping pagination early", page)
            break

        all_jobs.extend(page_jobs)
        log.info("Page %s: %s jobs parsed", page, len(page_jobs))

        polite_delay()

    normalized = [
        {
            "source": SOURCE_NAME,
            "source_job_id": job.source_job_id,
            "fingerprint": make_job_fingerprint(SOURCE_NAME, job.source_job_id),
            "job_title": job.job_title,
            "company": job.company,
            "posted_date": job.posted_date,
            "closing_date": job.closing_date,
            "detail_url": job.detail_url,
        }
        for job in all_jobs
    ]

    log.info("Infopark scrape complete: %s total jobs", len(normalized))
    return normalized


if __name__ == "__main__":
    jobs = scrape_all_pages()
    print(f"Scraped {len(jobs)} jobs")
