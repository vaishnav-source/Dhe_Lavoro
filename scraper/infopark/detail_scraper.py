from typing import Optional, Dict

import requests
from bs4 import BeautifulSoup

from scraper.common.http_client import safe_get
from scraper.common.email_extractor import extract_contact_email
from scraper.common.html_cleaner import extract_main_text
from scraper.common.logger import get_logger

log = get_logger(__name__)


def fetch_job_detail(detail_url: str) -> Dict[str, Optional[str]]:
    """Fetch one Infopark job detail page and pull out what the listing
    page doesn't have: full description text and a contact email if one
    is present.

    Returns a dict with an extra 'not_found' flag: True specifically when
    the server returned 404 — this means the job posting itself was
    removed from the live site (closing date passed, filled, pulled early),
    not a fetch failure. The caller uses this to mark the job 'expired'
    in the DB instead of leaving it forever stuck in the 'still missing
    detail info' queue, which would otherwise re-attempt the same dead
    URL on every future backfill run (same pattern as Technopark's
    detail_scraper.py)."""
    try:
        resp = safe_get(detail_url)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status == 404:
            log.info("Job posting no longer exists (404), will mark expired: %s", detail_url)
            return {"description": None, "contact_email": None, "not_found": True}
        log.warning("Failed to fetch detail page %s: %s", detail_url, exc)
        return {"description": None, "contact_email": None, "not_found": False}
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to fetch detail page %s: %s", detail_url, exc)
        return {"description": None, "contact_email": None, "not_found": False}

    email = extract_contact_email(resp.text)

    # Description: strip nav/header/footer chrome before extracting text —
    # otherwise every job's description gets the same repeated site
    # boilerplate (menu links, footer tagline) mixed in.
    soup = BeautifulSoup(resp.text, "html.parser")
    description = extract_main_text(soup)

    return {"description": description, "contact_email": email, "not_found": False}