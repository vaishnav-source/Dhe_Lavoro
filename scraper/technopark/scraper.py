from typing import List, Dict, Any, Set, Optional
from urllib.parse import urlparse, parse_qs

from playwright.sync_api import sync_playwright, Response

from scraper.common.config import TECHNOPARK_LANDING_URL, TECHNOPARK_MAX_PAGES
from scraper.common.rate_limiter import polite_delay
from scraper.common.dedup import make_job_fingerprint
from scraper.common.logger import get_logger
from scraper.technopark.parser import parse_paginated_jobs, TechnoparkJob

log = get_logger(__name__)

SOURCE_NAME = "technopark"
PAGINATED_URL_MARKER = "paginated-jobs"


class TechnoparkScrapeError(Exception):
    """Raised when the browser-based scrape makes zero progress at all —
    e.g. the site blocked headless Chromium too, or the page layout changed
    so scrolling no longer triggers new loads. Worth failing loudly rather
    than silently returning an empty list."""


def _page_number_from_url(url: str) -> Optional[int]:
    try:
        qs = parse_qs(urlparse(url).query)
        return int(qs.get("page", [None])[0])
    except (TypeError, ValueError):
        return None


def scrape_all_pages(max_pages: int = TECHNOPARK_MAX_PAGES, headless: bool = True) -> List[dict]:
    """Uses a real headless browser rather than raw HTTP requests.

    Reason: Technopark's paginated-jobs endpoint returns 404 for a plain
    requests-based call even when headers, cookies, and the XSRF token all
    match what a real browser sends — this points to a TLS/JS-fingerprint
    based anti-bot check (common with Cloudflare-style protection) that
    only a genuine browser engine passes. Playwright drives real Chromium
    and simply listens for the page's own XHR responses as it scrolls,
    rather than trying to replicate the API call by hand.
    """
    seen_pages: Set[int] = set()
    raw_payloads_by_page: Dict[int, Any] = {}

    def handle_response(response: Response) -> None:
        if PAGINATED_URL_MARKER not in response.url:
            return
        page_num = _page_number_from_url(response.url)
        if page_num is None or page_num in seen_pages:
            return
        if response.status != 200:
            log.warning("Technopark page %s responded with status %s", page_num, response.status)
            return
        try:
            payload = response.json()
        except Exception as exc:  # noqa: BLE001
            log.warning("Technopark page %s: response not JSON (%s)", page_num, exc)
            return
        seen_pages.add(page_num)
        raw_payloads_by_page[page_num] = payload

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.on("response", handle_response)

        page.goto(TECHNOPARK_LANDING_URL, wait_until="networkidle")

        stagnant_scrolls = 0
        max_stagnant_scrolls = 3  # stop once a few scrolls in a row load nothing new

        while len(seen_pages) < max_pages and stagnant_scrolls < max_stagnant_scrolls:
            pages_before = len(seen_pages)

            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(1500)  # let the XHR fire and resolve

            if len(seen_pages) == pages_before:
                stagnant_scrolls += 1
            else:
                stagnant_scrolls = 0

            polite_delay()

        browser.close()

    if not seen_pages:
        raise TechnoparkScrapeError(
            "No paginated-jobs responses captured — headless Chromium may be "
            "blocked too, or the endpoint/marker changed. Re-check DevTools."
        )

    all_jobs: List[TechnoparkJob] = []
    for page_num in sorted(raw_payloads_by_page):
        page_jobs = parse_paginated_jobs(raw_payloads_by_page[page_num])
        log.info("Page %s: %s jobs parsed", page_num, len(page_jobs))
        all_jobs.extend(page_jobs)

    normalized = [
        {
            "source": SOURCE_NAME,
            "source_job_id": job.source_job_id,
            "fingerprint": make_job_fingerprint(SOURCE_NAME, job.source_job_id),
            "job_title": job.job_title,
            "company": job.company_name,
            "posted_date": job.posted_date,
            "closing_date": job.closing_date,
            "detail_url": job.detail_url,
        }
        for job in all_jobs
    ]

    log.info(
        "Technopark scrape complete: %s total jobs across %s pages",
        len(normalized), len(seen_pages),
    )
    return normalized


if __name__ == "__main__":
    jobs = scrape_all_pages()
    print(f"Scraped {len(jobs)} jobs")