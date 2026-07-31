import re
from typing import Optional

from bs4 import BeautifulSoup

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# Generic park/portal addresses we don't want mistaken for a company's own
# apply-contact — extend this list as more noise addresses turn up.
GENERIC_NOISE_DOMAINS = {"infopark.in", "technopark.in", "cyberparks.in"}


def _is_probably_noise(email: str) -> bool:
    domain = email.split("@")[-1].lower()
    return domain in GENERIC_NOISE_DOMAINS


LABELED_EMAIL_REGEX = re.compile(
    r"contact\s*email\s*:?\s*([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
    re.IGNORECASE,
)


def extract_contact_email(html: str) -> Optional[str]:
    """Best-effort extraction of a job's apply-contact email from a detail
    page, in priority order:
      1. An explicit 'Contact Email: x@y.com' labeled field (seen on
         Technopark detail pages) — most reliable, purpose-built signal.
      2. A mailto: link.
      3. A plain-text email match anywhere in the visible text.
    Returns None if nothing found or if the only candidate looks like the
    park's own generic contact address rather than the company's."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    labeled_match = LABELED_EMAIL_REGEX.search(text)
    if labeled_match:
        candidate = labeled_match.group(1)
        if not _is_probably_noise(candidate):
            return candidate

    for link in soup.find_all("a", href=True):
        if link["href"].lower().startswith("mailto:"):
            candidate = link["href"].split(":", 1)[1].split("?")[0].strip()
            if candidate and not _is_probably_noise(candidate):
                return candidate

    matches = EMAIL_REGEX.findall(text)
    for candidate in matches:
        if not _is_probably_noise(candidate):
            return candidate

    return None
