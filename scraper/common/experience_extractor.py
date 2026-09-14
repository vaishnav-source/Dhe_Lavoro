"""
Regex-based experience-range extraction from job description text.

Cheap, free, no extra API call — covers the vast majority of postings we've
seen, which state years pretty explicitly ("5+ years", "2-4 years",
"0-2 years experience", "3yrs exp"). Misses unusual phrasing, but that's an
acceptable trade-off for v1: if the regex miss-rate turns out to be high in
practice, upgrade to piggybacking on the AI summarizer call instead of
trying to special-case every edge case upfront.
"""
import re
from typing import Optional, Tuple

# Tried in order from most to least specific, so a plain range never gets
# mis-read by a looser single-number pattern.

_RANGE_RE = re.compile(
    r"(\d{1,2})\s*(?:-|to|–)\s*(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)

_PLUS_RE = re.compile(
    r"(\d{1,2})\s*\+\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)

_MIN_PHRASE_RE = re.compile(
    r"(?:minimum(?:\s+of)?|at\s+least)\s*(\d{1,2})\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)

_SINGLE_RE = re.compile(
    r"(\d{1,2})\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp)\b",
    re.IGNORECASE,
)

_FRESHER_RE = re.compile(
    r"\b(?:freshers?|entry[\s-]?level|no\s+experience\s+required)\b",
    re.IGNORECASE,
)


def extract_experience(text: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """Best-effort (experience_min, experience_max) in years from a job
    description. Returns (None, None) when nothing matches — an
    unextracted job just won't show up in an experience-filtered search,
    it isn't hidden or broken otherwise.

    Match priority:
      1. Explicit range   "2-4 years", "2 to 5 yrs"     -> (2, 4)
      2. Open-ended       "5+ years"                     -> (5, None)
      3. Minimum phrase   "minimum 3 years", "at least 2 years" -> (2, None)
      4. Single number    "3 years experience", "2yrs exp"      -> (3, 3)
      5. Fresher keywords "freshers can apply", "entry level"   -> (0, 0)

    Only the first match found is used — descriptions occasionally mention
    unrelated numbers-with-"years" (e.g. "founded in 2015"), so we stop at
    the first real hit rather than scanning for a supposedly better one.
    """
    if not text:
        return None, None

    m = _RANGE_RE.search(text)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        if lo > hi:
            lo, hi = hi, lo
        return lo, hi

    m = _PLUS_RE.search(text)
    if m:
        return int(m.group(1)), None

    m = _MIN_PHRASE_RE.search(text)
    if m:
        return int(m.group(1)), None

    m = _SINGLE_RE.search(text)
    if m:
        val = int(m.group(1))
        return val, val

    if _FRESHER_RE.search(text):
        return 0, 0

    return None, None