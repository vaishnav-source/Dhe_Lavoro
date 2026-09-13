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
# (lowercased). Covers abbreviated site-specific classes seen in practice
# ("ftr-blue", "cpy-text" on Infopark).
#
# Deliberately NOT "header"/"footer" here even though they're common site-
# chrome class names: genuine <header>/<footer> HTML tags are already
# stripped above via NOISE_TAGS regardless of class, so this keyword list
# only needs to catch chrome that ISN'T wrapped in the real semantic tag.
# Infopark wraps a job's entire actual content (experience, requirements,
# skills) in a content div named "job-header" — a broad "header" substring
# match here silently deleted that whole block on ~97% of infopark
# postings, since it doesn't require the match to BE a header, just to
# contain the substring anywhere in its class name.
NOISE_CLASS_KEYWORDS = [
    "nav", "navbar", "menu", "ftr",
    "breadcrumb", "cpy", "copyright",
]

# Anchor links back to a site's own job-listing index (breadcrumb-style
# "< All Jobs" links) aren't wrapped in a <nav> tag on Technopark, so they
# survive the tag/class sweep above — caught separately by text + href.
BREADCRUMB_LINK_TEXTS = {"all jobs", "< all jobs"}
BREADCRUMB_HREF_SUBSTRINGS = ["/job-search", "/companies-job"]

# Tags treated as block boundaries when rebuilding readable text — each
# gets its own line, instead of every tag's text being run together with
# a single space (which is what produced one giant unreadable run-on
# paragraph mixing company info, requirements, and skills).
#
# "div" is included even though it's not a semantic content tag: Infopark
# puts a job's entire real body (requirements, responsibilities,
# experience) as raw text nodes separated by plain <br> tags directly
# inside a <div> — none of it wrapped in <p>/<li> at all. Only treating
# p/li/headings as blocks made that text completely invisible to
# extraction (found via inspecting a live page's DOM — only the <h4>
# job-title heading survived, everything else vanished). Technopark
# wraps its content in proper <p>/<li> tags, so this addition is a no-op
# there — same output as before.
BLOCK_TAGS = ["p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "blockquote", "div"]


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

    # Insert a boundary marker as a SIBLING immediately before each block
    # tag, then do exactly one get_text() call over the whole remaining
    # tree at the end. This (rather than calling get_text() separately on
    # each matched block, which was the old approach) is what makes adding
    # "div" to BLOCK_TAGS safe: nested divs would otherwise have their
    # content extracted once for the outer div's own get_text() and AGAIN
    # for each inner div/p/li matched separately, duplicating everything.
    # A single get_text() on the root visits every text node exactly once
    # by definition, in true document order, so real <p>/<li> content and
    # raw text-plus-<br> content sitting in a bare <div> both come out
    # correctly interleaved with no duplication either way.
    for tag in soup.find_all(BLOCK_TAGS):
        marker = "\n• " if tag.name == "li" else "\n\n"
        tag.insert_before(marker)

    result = soup.get_text("", strip=False)
    lines = [ln.strip() for ln in result.split("\n")]
    result = "\n\n".join(ln for ln in lines if ln)

    result = re.sub(r"\n{3,}", "\n\n", result).strip()
    return result[:max_length]