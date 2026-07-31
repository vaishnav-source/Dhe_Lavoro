"""
Summarizes a job's full description into a short 2-3 sentence blurb using
Groq's chat completions API (OpenAI-compatible format).

Kept deliberately separate from scraper/common/http_client.py — that
module's host allow-list is scoped to the job-source sites we scrape
(Infopark/Technopark), not third-party APIs, so this file makes its own
minimal, directly-targeted request rather than reusing it.
"""
from typing import Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from scraper.common.config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_API_URL,
    GROQ_TIMEOUT_SECONDS,
    GROQ_MAX_INPUT_CHARS,
)
from scraper.common.logger import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = (
    "You summarize job descriptions for a job-listing website. Write a "
    "concise 2-3 sentence summary covering: the role, key required skills, "
    "and experience level if mentioned. Plain text only, no markdown, no "
    "preamble like 'Here is a summary'."
)


class SummarizationError(Exception):
    """Raised only for genuinely unexpected API responses (e.g. missing
    API key configured at all) — transient failures are retried instead,
    and a fully-exhausted retry just returns None to the caller."""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(requests.RequestException),
    reraise=True,
)
def _call_groq(description: str) -> str:
    if not GROQ_API_KEY:
        raise SummarizationError("GROQ_API_KEY not set — check your .env file")

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": description[:GROQ_MAX_INPUT_CHARS]},
        ],
        "temperature": 0.3,
        "max_tokens": 200,
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}

    resp = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=GROQ_TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def summarize_job_description(description: Optional[str]) -> Optional[str]:
    """Returns a short summary, or None if description is empty/missing or
    summarization fails after retries — caller should treat None as
    'no summary available yet', not as an error to propagate."""
    if not description or not description.strip():
        return None

    try:
        return _call_groq(description)
    except SummarizationError as exc:
        log.error("Summarization misconfigured: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 — network/API failures, don't crash the batch
        log.warning("Summarization failed after retries: %s", exc)
        return None
