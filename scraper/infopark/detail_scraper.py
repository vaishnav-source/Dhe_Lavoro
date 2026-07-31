from typing import Optional, Dict

from scraper.common.http_client import safe_get
from scraper.common.email_extractor import extract_contact_email
from scraper.common.logger import get_logger

log = get_logger(__name__)


def fetch_job_detail(detail_url: str) -> Dict[str, Optional[str]]:
    """Fetch one Infopark job detail page and pull out what the listing
    page doesn't have: full description text and a contact email if one
    is present. Returns None values (not an exception) on failure so a
    single bad detail page doesn't stop a batch run — caller decides
    whether to retry later."""
    try:
        resp = safe_get(detail_url)
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to fetch detail page %s: %s", detail_url, exc)
        return {"description": None, "contact_email": None}

    email = extract_contact_email(resp.text)

    # Description: take the page's visible text as a simple first pass.
    # Good enough for search/keyword use; can be tightened to a specific
    # container once the live page's real class names are confirmed.
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(resp.text, "html.parser")
    description = soup.get_text(" ", strip=True)[:5000]  # cap length, avoid bloated rows

    return {"description": description, "contact_email": email}
