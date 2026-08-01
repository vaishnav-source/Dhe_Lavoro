from unittest.mock import MagicMock

import requests

import scraper.common.ai_summarizer as ai_summarizer
from scraper.common.ai_summarizer import summarize_job_description


def test_empty_description_returns_none_without_calling_api(monkeypatch):
    called = []
    monkeypatch.setattr(ai_summarizer, "_call_groq", lambda desc: called.append(desc))
    assert summarize_job_description("") is None
    assert summarize_job_description(None) is None
    assert summarize_job_description("   ") is None
    assert called == []


def test_successful_summary_returned(monkeypatch):
    monkeypatch.setattr(ai_summarizer, "_call_groq", lambda desc: "A short summary.")
    result = summarize_job_description("Some long job description text.")
    assert result == "A short summary."


def test_missing_api_key_returns_none(monkeypatch):
    monkeypatch.setattr(ai_summarizer, "GROQ_API_KEY", "")

    result = summarize_job_description("Some description")

    assert result is None


def test_api_failure_after_retries_returns_none(monkeypatch):
    monkeypatch.setattr(ai_summarizer, "GROQ_API_KEY", "fake-key")

    def broken_post(*args, **kwargs):
        raise requests.RequestException("network down")

    monkeypatch.setattr(requests, "post", broken_post)

    result = summarize_job_description("Some description")

    assert result is None


def test_successful_api_call_parses_response(monkeypatch):
    monkeypatch.setattr(ai_summarizer, "GROQ_API_KEY", "fake-key")

    fake_resp = MagicMock()
    fake_resp.raise_for_status = lambda: None
    fake_resp.json = lambda: {
        "choices": [{"message": {"content": "  Concise role summary.  "}}]
    }
    monkeypatch.setattr(requests, "post", lambda *a, **k: fake_resp)

    result = summarize_job_description("Full job description text here.")

    assert result == "Concise role summary."


def test_rate_limit_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(ai_summarizer, "GROQ_API_KEY", "fake-key")
    monkeypatch.setattr(ai_summarizer.time, "sleep", lambda s: None)  # skip real waiting in tests

    rate_limited_resp = MagicMock()
    rate_limited_resp.status_code = 429
    rate_limited_resp.headers = {"Retry-After": "2"}

    success_resp = MagicMock()
    success_resp.status_code = 200
    success_resp.raise_for_status = lambda: None
    success_resp.json = lambda: {"choices": [{"message": {"content": "Summary after retry."}}]}

    responses = [rate_limited_resp, success_resp]
    monkeypatch.setattr(requests, "post", lambda *a, **k: responses.pop(0))

    result = summarize_job_description("Some description")

    assert result == "Summary after retry."


def test_rate_limit_exhausted_returns_none(monkeypatch):
    monkeypatch.setattr(ai_summarizer, "GROQ_API_KEY", "fake-key")
    monkeypatch.setattr(ai_summarizer.time, "sleep", lambda s: None)

    always_rate_limited = MagicMock()
    always_rate_limited.status_code = 429
    always_rate_limited.headers = {}  # no Retry-After -> falls back to default backoff

    monkeypatch.setattr(requests, "post", lambda *a, **k: always_rate_limited)

    result = summarize_job_description("Some description")

    assert result is None