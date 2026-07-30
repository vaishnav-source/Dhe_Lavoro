"""
Single shared Supabase client factory. Every file that needs DB access
should import get_client() from here — never call create_client()
directly elsewhere, so there's exactly one place that knows how the
connection is built (easier to swap provider later, easier to mock in
tests, no scattered credential-handling).
"""
from supabase import create_client, Client

from scraper.common.config import SUPABASE_URL, SUPABASE_KEY

_client: Client | None = None  # cached singleton, one connection per process


def get_client() -> Client:
    global _client
    if _client is not None:
        return _client

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_SERVICE_KEY not set — check your .env file"
        )

    _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def reset_client_cache() -> None:
    """Test-only helper — clears the cached client so tests don't leak
    state between runs."""
    global _client
    _client = None
