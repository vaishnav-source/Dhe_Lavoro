from urllib.parse import urlparse

import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from scraper.common.config import (
    ALLOWED_HOSTS,
    REQUEST_TIMEOUT_SECONDS,
    USER_AGENT,
    MAX_RETRIES,
    RETRY_BACKOFF_SECONDS,
)
from scraper.common.logger import get_logger

log = get_logger(__name__)


class DisallowedHostError(Exception):
    """Raised when a scraper tries to fetch a host not on the allow-list.
    This is a deliberate guard rail — scrapers must only ever hit the exact
    sources this project is scoped to, never arbitrary/derived URLs."""


def _assert_allowed(url: str) -> None:
    host = urlparse(url).hostname or ""
    # allow subdomains of an allowed host, but nothing else
    if not any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS):
        raise DisallowedHostError(f"Refusing to fetch non-allow-listed host: {host}")


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=RETRY_BACKOFF_SECONDS, min=1, max=30),
    retry=retry_if_exception_type(requests.RequestException),
    reraise=True,
)
def safe_get(url: str, session: requests.Session | None = None, **kwargs) -> requests.Response:
    """GET with: host allow-list check, timeout, standard UA, retry w/
    exponential backoff on network errors. Raises on non-2xx after retries."""
    _assert_allowed(url)
    client = session or requests
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", USER_AGENT)
    resp = client.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)
    resp.raise_for_status()
    return resp


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=RETRY_BACKOFF_SECONDS, min=1, max=30),
    retry=retry_if_exception_type(requests.RequestException),
    reraise=True,
)
def safe_post(url: str, session: requests.Session | None = None, **kwargs) -> requests.Response:
    _assert_allowed(url)
    client = session or requests
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", USER_AGENT)
    resp = client.post(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)
    resp.raise_for_status()
    return resp
