from unittest.mock import MagicMock

import requests

import scraper.common.ai_summarizer as ai_summarizer
from scraper.common.ai_summarizer import summarize_job_description


def reset_cursor(monkeypatch):
    """Every test starts the sticky provider cursor at 0 — otherwise test
    order could leak state between tests (a prior test advancing the
    cursor would make a later test skip a provider it expects to hit)."""
    monkeypatch.setattr(ai_summarizer, "_provider_start_index", 0)
    monkeypatch.setattr(ai_summarizer, "_last_exhausted_at", None)


def test_empty_description_returns_none_without_calling_any_provider(monkeypatch):
    reset_cursor(monkeypatch)
    calls = []
    monkeypatch.setattr(ai_summarizer, "PROVIDERS", [("groq", lambda d: calls.append(d))])
    assert summarize_job_description("") is None
    assert summarize_job_description(None) is None
    assert summarize_job_description("   ") is None
    assert calls == []


def test_first_provider_success_short_circuits_rest(monkeypatch):
    reset_cursor(monkeypatch)
    calls = []

    def groq_ok(desc):
        calls.append("groq")
        return "Groq summary"

    def openrouter_should_not_be_called(desc):
        calls.append("openrouter")
        return "should not happen"

    monkeypatch.setattr(ai_summarizer, "PROVIDERS", [
        ("groq", groq_ok),
        ("openrouter", openrouter_should_not_be_called),
    ])

    result = summarize_job_description("Some description")

    assert result == "Groq summary"
    assert calls == ["groq"]


def test_falls_back_to_next_provider_on_rate_limit(monkeypatch):
    reset_cursor(monkeypatch)

    def groq_rate_limited(desc):
        raise requests.HTTPError("429 Too Many Requests")

    def openrouter_ok(desc):
        return "OpenRouter summary"

    monkeypatch.setattr(ai_summarizer, "PROVIDERS", [
        ("groq", groq_rate_limited),
        ("openrouter", openrouter_ok),
    ])

    result = summarize_job_description("Some description")

    assert result == "OpenRouter summary"


def test_missing_api_key_skips_to_next_provider(monkeypatch):
    reset_cursor(monkeypatch)

    def groq_no_key(desc):
        raise RuntimeError("GROQ_API_KEY not set")

    def hf_ok(desc):
        return "HF summary"

    monkeypatch.setattr(ai_summarizer, "PROVIDERS", [
        ("groq", groq_no_key),
        ("huggingface", hf_ok),
    ])

    result = summarize_job_description("Some description")

    assert result == "HF summary"


def test_all_providers_fail_returns_none(monkeypatch):
    reset_cursor(monkeypatch)

    def always_fails(desc):
        raise requests.RequestException("network down")

    monkeypatch.setattr(ai_summarizer, "PROVIDERS", [
        ("groq", always_fails),
        ("openrouter", always_fails),
        ("huggingface", always_fails),
    ])

    result = summarize_job_description("Some description")

    assert result is None


def test_sticky_cursor_skips_exhausted_provider_on_later_calls(monkeypatch):
    """Core behavior the person asked for: once Groq fails once (e.g. job
    15 hits a rate limit), job 16 onwards should go straight to the next
    provider — not retry Groq every single time."""
    reset_cursor(monkeypatch)

    groq_call_count = {"n": 0}

    def groq_rate_limited(desc):
        groq_call_count["n"] += 1
        raise requests.HTTPError("429 Too Many Requests")

    def openrouter_ok(desc):
        return f"OpenRouter summary for: {desc}"

    monkeypatch.setattr(ai_summarizer, "PROVIDERS", [
        ("groq", groq_rate_limited),
        ("openrouter", openrouter_ok),
    ])

    # job 15 — groq fails, falls back to openrouter, cursor advances
    result_15 = summarize_job_description("job 15 description")
    assert result_15 == "OpenRouter summary for: job 15 description"
    assert groq_call_count["n"] == 1

    # job 16 — should go straight to openrouter, groq not called again
    result_16 = summarize_job_description("job 16 description")
    assert result_16 == "OpenRouter summary for: job 16 description"
    assert groq_call_count["n"] == 1  # unchanged — groq was skipped this time


def test_cooldown_resets_cursor_after_all_exhausted(monkeypatch):
    reset_cursor(monkeypatch)

    call_log = []

    def groq_fails_then_succeeds(desc):
        call_log.append("groq")
        if len(call_log) == 1:
            raise requests.HTTPError("429 Too Many Requests")
        return "Groq summary after cooldown"

    monkeypatch.setattr(ai_summarizer, "PROVIDERS", [("groq", groq_fails_then_succeeds)])
    monkeypatch.setattr(ai_summarizer, "COOLDOWN_SECONDS", 0)  # instant cooldown for the test

    fake_now = {"t": 1000.0}
    monkeypatch.setattr(ai_summarizer.time, "time", lambda: fake_now["t"])

    # first call: groq fails, cursor exhausted (index 1, len(PROVIDERS)=1)
    result1 = ai_summarizer.summarize_job_description("desc 1")
    assert result1 is None

    # advance fake clock past the (zeroed) cooldown, then call again
    fake_now["t"] += 1
    result2 = ai_summarizer.summarize_job_description("desc 2")
    assert result2 == "Groq summary after cooldown"
    assert call_log == ["groq", "groq"]


def test_call_nvidia_parses_response_shape(monkeypatch):
    monkeypatch.setattr(ai_summarizer, "NVIDIA_API_KEY", "fake-key")

    fake_resp = MagicMock()
    fake_resp.raise_for_status = lambda: None
    fake_resp.json = lambda: {"choices": [{"message": {"content": "  NVIDIA summary.  "}}]}
    monkeypatch.setattr(requests, "post", lambda *a, **k: fake_resp)

    result = ai_summarizer._call_nvidia("Some job description")

    assert result == "NVIDIA summary."


def test_call_nvidia_raises_on_null_content(monkeypatch):
    monkeypatch.setattr(ai_summarizer, "NVIDIA_API_KEY", "fake-key")

    fake_resp = MagicMock()
    fake_resp.raise_for_status = lambda: None
    fake_resp.json = lambda: {"choices": [{"message": {"content": None}}]}
    monkeypatch.setattr(requests, "post", lambda *a, **k: fake_resp)

    try:
        ai_summarizer._call_nvidia("Some description")
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass


def test_call_nvidia_missing_key_raises(monkeypatch):
    monkeypatch.setattr(ai_summarizer, "NVIDIA_API_KEY", "")

    try:
        ai_summarizer._call_nvidia("Some description")
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass


def test_call_groq_raises_on_null_content(monkeypatch):
    monkeypatch.setattr(ai_summarizer, "GROQ_API_KEY", "fake-key")

    fake_resp = MagicMock()
    fake_resp.raise_for_status = lambda: None
    fake_resp.json = lambda: {"choices": [{"message": {"content": None}}]}
    monkeypatch.setattr(requests, "post", lambda *a, **k: fake_resp)

    try:
        ai_summarizer._call_groq("Some description")
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass


def test_call_openrouter_raises_on_null_content(monkeypatch):
    monkeypatch.setattr(ai_summarizer, "OPENROUTER_API_KEY", "fake-key")

    fake_resp = MagicMock()
    fake_resp.raise_for_status = lambda: None
    fake_resp.json = lambda: {"choices": [{"message": {"content": None}}]}
    monkeypatch.setattr(requests, "post", lambda *a, **k: fake_resp)

    try:
        ai_summarizer._call_openrouter("Some description")
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass


def test_call_groq_parses_response_shape(monkeypatch):
    monkeypatch.setattr(ai_summarizer, "GROQ_API_KEY", "fake-key")

    fake_resp = MagicMock()
    fake_resp.raise_for_status = lambda: None
    fake_resp.json = lambda: {"choices": [{"message": {"content": "  A summary.  "}}]}
    monkeypatch.setattr(requests, "post", lambda *a, **k: fake_resp)

    result = ai_summarizer._call_groq("Some job description")

    assert result == "A summary."


def test_call_huggingface_parses_list_response_shape(monkeypatch):
    monkeypatch.setattr(ai_summarizer, "HF_API_KEY", "fake-key")

    fake_resp = MagicMock()
    fake_resp.raise_for_status = lambda: None
    fake_resp.json = lambda: [{"generated_text": "  HF generated summary.  "}]
    monkeypatch.setattr(requests, "post", lambda *a, **k: fake_resp)

    result = ai_summarizer._call_huggingface("Some job description")

    assert result == "HF generated summary."


def test_call_huggingface_unexpected_shape_raises(monkeypatch):
    monkeypatch.setattr(ai_summarizer, "HF_API_KEY", "fake-key")

    fake_resp = MagicMock()
    fake_resp.raise_for_status = lambda: None
    fake_resp.json = lambda: {"error": "model loading"}
    monkeypatch.setattr(requests, "post", lambda *a, **k: fake_resp)

    try:
        ai_summarizer._call_huggingface("Some job description")
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass