from urllib.parse import unquote
from typing import List

import requests

from scraper.common.config import (
    TECHNOPARK_LANDING_URL,
    TECHNOPARK_PAGINATED_URL,
    TECHNOPARK_MAX_PAGES,
)
from scraper.common.http_client import safe_get
from scraper.common.rate_limiter import polite_delay
from scraper.common.dedup import make_job_fingerprint
from scraper.common.logger import get_logger
from scraper.technopark.parser import parse_paginated_jobs, TechnoparkJob

log = get_logger(__name__)

SOURCE_NAME = "technopark"


class SessionInitError(Exception):
    """Raised when the XSRF-TOKEN cookie isn't found after landing-page
    load — means the site changed its auth pattern and this scraper needs
    updating, not a transient failure worth retrying blindly."""


def _init_session() -> requests.Session:
    """Load the job-search landing page once to obtain the session cookie
    and XSRF token, mirroring what a real browser does before the site's
    own JS calls the paginated-jobs API."""
    session = requests.Session()
    safe_get(TECHNOPARK_LANDING_URL, session=session)

    xsrf_cookie = session.cookies.get("XSRF-TOKEN")
    if not xsrf_cookie:
        raise SessionInitError("XSRF-TOKEN cookie not found after landing page load")

    # Laravel sends this cookie URL-encoded; the header needs the decoded value.
    # Also mirror the other headers a real browser sends for this AJAX call —
    # without these the route appears to 404 (likely an anti-bot check that
    # silently 404s non-XHR-looking requests instead of returning 403).
    session.headers.update({
        "X-XSRF-TOKEN": unquote(xsrf_cookie),
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/plain, */*",
        "Referer": TECHNOPARK_LANDING_URL,
    })
    return session


def scrape_all_pages(max_pages: int = TECHNOPARK_MAX_PAGES) -> List[dict]:
    session = _init_session()
    all_jobs: List[TechnoparkJob] = []

    for page in range(1, max_pages + 1):
        params = {"page": page, "search": "", "type": "Job"}
        try:
            resp = safe_get(TECHNOPARK_PAGINATED_URL, session=session, params=params)
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to fetch Technopark page %s: %s", page, exc)
            continue

        try:
            payload = resp.json()
        except ValueError:
            log.warning("Page %s: response was not valid JSON — stopping", page)
            break

        page_jobs = parse_paginated_jobs(payload)
        if not page_jobs:
            log.info("Page %s returned 0 jobs — stopping pagination", page)
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
            "company": job.company_name,
            "posted_date": job.posted_date,
            "closing_date": job.closing_date,
        }
        for job in all_jobs
    ]

    log.info("Technopark scrape complete: %s total jobs", len(normalized))
    return normalized


if __name__ == "__main__":
    jobs = scrape_all_pages()
    print(f"Scraped {len(jobs)} jobs")