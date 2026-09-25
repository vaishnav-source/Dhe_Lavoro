"""
Summarizes a job's full description into a short 2-3 sentence blurb.

Tries multiple AI providers in order (Groq -> NVIDIA NIM) rather than
retrying one provider through a rate limit. If a provider is rate-limited
or its API key isn't configured, we move straight to the next one instead
of waiting — much faster for a batch backfill run than sitting through
Retry-After delays, and doesn't need per-provider quota tracking. A
provider with no API key set is skipped silently (not an error).
"""
from typing import Optional, Callable, List, Tuple
import time

import requests

from scraper.common.config import (
    GROQ_API_KEY, GROQ_MODEL, GROQ_API_URL, GROQ_MAX_TOKENS,
    NVIDIA_API_KEY, NVIDIA_MODEL, NVIDIA_API_URL,
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
        "max_tokens": GROQ_MAX_TOKENS,
        # gpt-oss-20b/120b are reasoning models — these two params keep
        # reasoning-token spend low and force the final answer into
        # message.content rather than a separate reasoning field. Other
        # (non-reasoning) Groq models silently ignore unknown params, so
        # this is safe to always send regardless of which model is active.
        "reasoning_effort": "low",
        "include_reasoning": False,
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=AI_TIMEOUT_SECONDS)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"].get("content")
    if not content:
        raise RuntimeError("Groq response had empty/null content")
    return content.strip()


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
        "max_tokens": 400,
    }
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(OPENROUTER_API_URL, json=payload, headers=headers, timeout=AI_TIMEOUT_SECONDS)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"].get("content")
    if not content:
        raise RuntimeError("OpenRouter response had empty/null content")
    return content.strip()


def _call_nvidia(description: str) -> str:
    if not NVIDIA_API_KEY:
        raise RuntimeError("NVIDIA_API_KEY not set")
    payload = {
        "model": NVIDIA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": description[:AI_MAX_INPUT_CHARS]},
        ],
        "temperature": 0.3,
        "max_tokens": 200,
    }
    headers = {"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(NVIDIA_API_URL, json=payload, headers=headers, timeout=AI_TIMEOUT_SECONDS)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"].get("content")
    if not content:
        raise RuntimeError("NVIDIA NIM response had empty/null content")
    return content.strip()


def _call_huggingface(description: str) -> str:
    if not HF_API_KEY:
        raise RuntimeError("HF_API_KEY not set")
    prompt = f"{SYSTEM_PROMPT}\n\nJob description:\n{description[:AI_MAX_INPUT_CHARS]}\n\nSummary:"
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 150, "temperature": 0.3}}
    headers = {"Authorization": f"Bearer {HF_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(HF_API_URL, json=payload, headers=headers, timeout=AI_TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list) and data and "generated_text" in data[0]:
        return data[0]["generated_text"].strip()
    raise RuntimeError(f"Unexpected Hugging Face response shape: {data}")


PROVIDERS: List[Tuple[str, Callable[[str], str]]] = [
    ("groq", _call_groq),
    ("nvidia", _call_nvidia),
    ("openrouter", _call_openrouter),
    ("huggingface", _call_huggingface),
]

_provider_start_index = 0
_last_exhausted_at: Optional[float] = None
COOLDOWN_SECONDS = 60


def summarize_job_description(description: Optional[str]) -> Optional[str]:
    """Tries providers starting from the current sticky cursor, advancing
    it forward on failure so later calls in the same run skip providers
    already known to be exhausted. If every provider is exhausted, the
    cursor auto-resets after COOLDOWN_SECONDS so a long run can recover
    once a rate limit window passes, rather than staying dead until the
    process restarts. Returns None if description is empty, no provider
    is configured, or every remaining provider still fails."""
    global _provider_start_index, _last_exhausted_at

    if not description or not description.strip():
        return None

    if _provider_start_index >= len(PROVIDERS) and _last_exhausted_at is not None:
        if time.time() - _last_exhausted_at >= COOLDOWN_SECONDS:
            log.info("Cooldown elapsed — retrying providers from the top")
            _provider_start_index = 0

    if _provider_start_index >= len(PROVIDERS):
        # Still within the cooldown window — nothing to try this call.
        # Deliberately return here WITHOUT touching _last_exhausted_at:
        # updating it on a no-op call would keep pushing the cooldown
        # deadline forward forever, so it could never actually elapse.
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

    _last_exhausted_at = time.time()
    log.error("All remaining AI providers failed or unconfigured — no summary produced")
    return None