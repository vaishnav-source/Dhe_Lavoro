import pytest

import scraper.common.db as db


def test_get_client_raises_without_config(monkeypatch):
    monkeypatch.setattr(db, "SUPABASE_URL", "")
    monkeypatch.setattr(db, "SUPABASE_KEY", "")
    db.reset_client_cache()

    with pytest.raises(RuntimeError):
        db.get_client()


def test_get_client_returns_cached_instance(monkeypatch):
    db.reset_client_cache()
    monkeypatch.setattr(db, "SUPABASE_URL", "https://fake.supabase.co")
    monkeypatch.setattr(db, "SUPABASE_KEY", "fake-key")

    calls = []

    def fake_create_client(url, key):
        calls.append((url, key))
        return object()

    monkeypatch.setattr(db, "create_client", fake_create_client)

    first = db.get_client()
    second = db.get_client()

    assert first is second  # cached, not recreated
    assert len(calls) == 1  # create_client only called once
    db.reset_client_cache()
