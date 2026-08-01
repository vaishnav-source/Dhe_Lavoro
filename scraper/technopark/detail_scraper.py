from typing import Optional, Dict

from bs4 import BeautifulSoup

from scraper.common.http_client import safe_get
from scraper.common.email_extractor import extract_contact_email
from scraper.common.config import TECHNOPARK_LANDING_URL
from scraper.common.logger import get_logger

log = get_logger(__name__)


def fetch_job_detail(detail_url: str) -> Dict[str, Optional[str]]:
    """Fetch one Technopark job detail page and pull out description +
    contact email. Passes a Referer pointing back to the job-search page —
    without it, requests to this route were getting 404'd (an anti-bot
    check independent of robots.txt, which does permit this path)."""
    try:
        resp = safe_get(detail_url, headers={"Referer": TECHNOPARK_LANDING_URL})
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to fetch detail page %s: %s", detail_url, exc)
        return {"description": None, "contact_email": None}

    email = extract_contact_email(resp.text)

    soup = BeautifulSoup(resp.text, "html.parser")
    description = soup.get_text(" ", strip=True)[:5000]  # cap length, avoid bloated rows

    return {"description": description, "contact_email": email}