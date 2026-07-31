from typing import Optional, Dict

from bs4 import BeautifulSoup

from scraper.common.http_client import safe_get
from scraper.common.email_extractor import extract_contact_email
from scraper.common.logger import get_logger

log = get_logger(__name__)


def fetch_job_detail(detail_url: str) -> Dict[str, Optional[str]]:
    """Fetch one Technopark job detail page and pull out description +
    contact email. Unlike the listing/search page, detail pages here are
    plain server-rendered HTML — a normal GET works fine, no Playwright
    needed (confirmed by direct fetch during development). Returns None
    values (not an exception) on failure so one bad page doesn't stop a
    batch run."""
    try:
        resp = safe_get(detail_url)
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to fetch detail page %s: %s", detail_url, exc)
        return {"description": None, "contact_email": None}

    email = extract_contact_email(resp.text)

    soup = BeautifulSoup(resp.text, "html.parser")
    description = soup.get_text(" ", strip=True)[:5000]  # cap length, avoid bloated rows

    return {"description": description, "contact_email": email}