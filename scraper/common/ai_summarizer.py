"""
Summarizes a job's full description into a short 2-3 sentence blurb.

Tries multiple AI providers in order (Groq -> OpenRouter -> Hugging Face)
rather than retrying one provider through a rate limit. If a provider is
rate-limited or its API key isn't configured, we move straight to the next
one instead of waiting — much faster for a batch backfill run than
sitting through Retry-After delays, and doesn't need per-provider quota
tracking. A provider with no API key set is skipped silently (not an
error) so this works with only Groq configured, or all three.
"""
from typing import Optional, Callable, List, Tuple

import requests

from scraper.common.config import (
    GROQ_API_KEY, GROQ_MODEL, GROQ_API_URL,
    OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_API_URL,
    HF_API_KEY, HF_MODEL, HF_API_URL,
    AI_TIMEOUT_SECONDS, AI_MAX_INPUT_CHARS,
)
from scraper.common.logger import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = (
    "You summarize job descriptions for a job-listing website. Write a "
    "concise 2-3 sentence summary covering: the role, key required skills, "
    "and experience level if mentioned. Plain text only, no markdown, no "
    "preamble like 'Here is a summary'."
)


def _call_groq(description: str) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set")
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": description[:AI_MAX_INPUT_CHARS]},
        ],
        "temperature": 0.3,
        "max_tokens": 200,
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=AI_TIMEOUT_SECONDS)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _call_openrouter(description: str) -> str:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": description[:AI_MAX_INPUT_CHARS]},
        ],
        "temperature": 0.3,
        "max_tokens": 200,
    }
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(OPENROUTER_API_URL, json=payload, headers=headers, timeout=AI_TIMEOUT_SECONDS)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _call_huggingface(description: str) -> str:
    if not HF_API_KEY:
        raise RuntimeError("HF_API_KEY not set")
    prompt = f"{SYSTEM_PROMPT}\n\nJob description:\n{description[:AI_MAX_INPUT_CHARS]}\n\nSummary:"
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 150, "temperature": 0.3}}
    headers = {"Authorization": f"Bearer {HF_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(HF_API_URL, json=payload, headers=headers, timeout=AI_TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()
    # HF inference API can return a list of generations or a dict depending on model/task
    if isinstance(data, list) and data and "generated_text" in data[0]:
        return data[0]["generated_text"].strip()
    raise RuntimeError(f"Unexpected Hugging Face response shape: {data}")


# Ordered fallback chain — name kept alongside the function purely for logging.
PROVIDERS: List[Tuple[str, Callable[[str], str]]] = [
    ("groq", _call_groq),
    ("openrouter", _call_openrouter),
    ("huggingface", _call_huggingface),
]

# Sticky cursor: once a provider fails (rate limit, missing key, etc), we
# start subsequent calls from the next provider instead of re-trying the
# exhausted one every single job. This resets only when the process
# restarts (e.g. next scheduled backfill run) — within one run, once Groq
# is rate-limited at job 15, jobs 16+ go straight to OpenRouter instead of
# wasting a failing call on Groq each time.
_provider_start_index = 0


def summarize_job_description(description: Optional[str]) -> Optional[str]:
    """Tries providers starting from the current sticky cursor, advancing
    it forward on failure so later calls in the same run skip providers
    already known to be exhausted. Returns None if description is empty,
    no provider is configured, or every remaining provider fails."""
    global _provider_start_index

    if not description or not description.strip():
        return None

    for i in range(_provider_start_index, len(PROVIDERS)):
        name, call_fn = PROVIDERS[i]
        try:
            result = call_fn(description)
            _provider_start_index = i  # stay here for next call — this one's working
            return result
        except RuntimeError as exc:
            # missing API key for this provider — expected/normal, quiet skip
            log.info("Skipping %s: %s", name, exc)
            _provider_start_index = i + 1
            continue
        except Exception as exc:  # noqa: BLE001 — rate limit, network, bad response shape
            log.warning("%s summarization failed, moving to next provider: %s", name, exc)
            _provider_start_index = i + 1
            continue

    log.error("All remaining AI providers failed or unconfigured — no summary produced")
    return None