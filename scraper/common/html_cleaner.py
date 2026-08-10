"""
Shared helper to strip site-wide chrome (nav/header/footer/menu) out of a
detail page before extracting the job description text. Without this,
soup.get_text() on the whole page pulls in every site's repeated nav links
and footer boilerplate alongside the actual job content — both Infopark
and Technopark detail pages exhibited this.

Deliberately generic (tag names + common class/id keyword heuristics)
rather than hardcoded to either site's exact markup, so it keeps working
if either site's class names change.
"""
from bs4 import BeautifulSoup

NOISE_TAGS = ["nav", "header", "footer", "script", "style"]
NOISE_CLASS_KEYWORDS = ["nav", "navbar", "menu", "footer", "header", "breadcrumb"]


def extract_main_text(soup: BeautifulSoup, max_length: int = 5000) -> str:
    """Removes nav/header/footer/script/style tags and any element whose
    class or id contains a common chrome keyword, then returns the
    remaining visible text, capped at max_length."""
    for tag_name in NOISE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    for tag in soup.find_all(True):
        attrs = " ".join(tag.get("class", []) + [tag.get("id", "")]).lower()
        if any(keyword in attrs for keyword in NOISE_CLASS_KEYWORDS):
            tag.decompose()

    return soup.get_text(" ", strip=True)[:max_length]