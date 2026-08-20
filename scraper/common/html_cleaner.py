"""
Shared helper to strip site-wide chrome (nav/header/footer/menu/breadcrumb)
out of a detail page before extracting the job description text. Without
this, soup.get_text() on the whole page pulls in every site's repeated nav
links and footer boilerplate alongside the actual job content.

Deliberately generic (tag names + class/id keyword heuristics + anchor
text/href patterns) rather than hardcoded to either site's exact markup,
so it keeps working if either site's class names change slightly.
"""
import re

from bs4 import BeautifulSoup

NOISE_TAGS = ["nav", "header", "footer", "script", "style"]

# Keyword substrings checked against each element's combined class+id
# (lowercased). Covers both full words ("footer") and abbreviated site-
# specific classes seen in practice ("ftr-blue", "cpy-text" on Infopark).
NOISE_CLASS_KEYWORDS = [
    "nav", "navbar", "menu", "footer", "ftr", "header",
    "breadcrumb", "cpy", "copyright",
]

# Anchor links back to a site's own job-listing index (breadcrumb-style
# "< All Jobs" links) aren't wrapped in a <nav> tag on Technopark, so they
# survive the tag/class sweep above — caught separately by text + href.
BREADCRUMB_LINK_TEXTS = {"all jobs", "< all jobs"}
BREADCRUMB_HREF_SUBSTRINGS = ["/job-search", "/companies-job"]

# Tags treated as separate "blocks" when rebuilding readable text — each
# becomes its own line, instead of every tag's text being run together
# with a single space (which is what produced one giant unreadable
# run-on paragraph mixing company info, requirements, and skills).
BLOCK_TAGS = ["p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "blockquote"]


def _is_breadcrumb_link(a_tag) -> bool:
    text = a_tag.get_text(strip=True).lower()
    href = (a_tag.get("href") or "").lower()
    if text in BREADCRUMB_LINK_TEXTS:
        return True
    if any(sub in href for sub in BREADCRUMB_HREF_SUBSTRINGS) and len(text) < 30:
        # short link text + points at the listing index page — a nav
        # link, not a legitimate long sentence that happens to link there
        return True
    return False


def extract_main_text(soup: BeautifulSoup, max_length: int = 5000) -> str:
    """Removes nav/header/footer/script/style tags, any element whose
    class or id contains a chrome keyword, and breadcrumb-style "back to
    listing" links. Then rebuilds the remaining text block-by-block (one
    paragraph/list-item/heading per line) instead of flattening the whole
    page into a single space-joined run-on string — Infopark and
    Technopark use different markup, but both structure real content into
    paragraphs/list items, so this reads properly on either without
    hardcoding either site's exact layout. Capped at max_length."""
    for tag_name in NOISE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    to_remove = []
    for tag in soup.find_all(True):
        attrs = " ".join(tag.get("class", []) + [tag.get("id", "")]).lower()
        if any(keyword in attrs for keyword in NOISE_CLASS_KEYWORDS):
            to_remove.append(tag)
    for tag in to_remove:
        if tag.parent is not None:  # already removed as a child of an earlier match
            tag.decompose()

    for a_tag in soup.find_all("a"):
        if _is_breadcrumb_link(a_tag):
            a_tag.decompose()

    for br in soup.find_all("br"):
        br.replace_with("\n")

    blocks = soup.find_all(BLOCK_TAGS)
    if blocks:
        lines = []
        for block in blocks:
            text = block.get_text(" ", strip=True)
            if not text:
                continue
            prefix = "• " if block.name == "li" else ""
            lines.append(prefix + text)
        result = "\n\n".join(lines)
    else:
        # no block tags found at all (unusual, but don't return nothing) —
        # fall back to the old flat extraction
        result = soup.get_text(" ", strip=True)

    result = re.sub(r"\n{3,}", "\n\n", result).strip()
    return result[:max_length]