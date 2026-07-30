import pytest

from scraper.common.http_client import safe_get, safe_post, DisallowedHostError


def test_refuses_non_allowlisted_host_get():
    with pytest.raises(DisallowedHostError):
        safe_get("https://evil-example.com/steal-data")


def test_refuses_non_allowlisted_host_post():
    with pytest.raises(DisallowedHostError):
        safe_post("https://evil-example.com/steal-data")


def test_allows_infopark_host(monkeypatch):
    # confirm allow-listed host passes the guard (mock the actual network
    # call so this test doesn't hit the real internet)
    import requests

    class FakeResp:
        status_code = 200
        text = "<html></html>"

        def raise_for_status(self):
            pass

    def fake_get(url, headers=None, timeout=None, **kwargs):
        return FakeResp()

    monkeypatch.setattr(requests, "get", fake_get)
    # should not raise DisallowedHostError
    safe_get("https://infopark.in/companies-job")


def test_refuses_lookalike_host():
    # guards against domain confusion, e.g. "infopark.in.evil.com"
    with pytest.raises(DisallowedHostError):
        safe_get("https://infopark.in.evil.com/companies-job")
