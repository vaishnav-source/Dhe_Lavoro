import pytest
import requests

from scraper.technopark.scraper import _init_session, SessionInitError


class FakeResp:
    status_code = 200
    text = "<html></html>"

    def raise_for_status(self):
        pass


def test_missing_xsrf_cookie_raises(monkeypatch):
    def fake_get(url, headers=None, timeout=None, **kwargs):
        return FakeResp()  # no cookies set on the session

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests.Session, "get", lambda self, *a, **k: FakeResp())

    with pytest.raises(SessionInitError):
        _init_session()


def test_xsrf_cookie_decoded_into_header(monkeypatch):
    def fake_session_get(self, *args, **kwargs):
        # simulate the server setting a URL-encoded XSRF-TOKEN cookie
        self.cookies.set("XSRF-TOKEN", "abc%3Ddef")
        return FakeResp()

    monkeypatch.setattr(requests.Session, "get", fake_session_get)

    session = _init_session()
    assert session.headers["X-XSRF-TOKEN"] == "abc=def"
