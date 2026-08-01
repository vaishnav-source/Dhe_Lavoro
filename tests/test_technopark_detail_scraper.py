from unittest.mock import MagicMock

import scraper.technopark.detail_scraper as detail_scraper


def test_fetch_job_detail_extracts_email_and_description(monkeypatch):
    fake_resp = MagicMock()
    fake_resp.text = (
        '<html><body><p>Contact Email: '
        '<a href="mailto:hiring@company.com">hiring@company.com</a></p>'
        '<p>Job desc content here.</p></body></html>'
    )
    monkeypatch.setattr(detail_scraper, "safe_get", lambda url, **kwargs: fake_resp)

    result = detail_scraper.fetch_job_detail("https://technopark.in/job-details/1?job=X")

    assert result["contact_email"] == "hiring@company.com"
    assert "Job desc content here" in result["description"]


def test_fetch_job_detail_passes_referer_header(monkeypatch):
    captured = {}

    fake_resp = MagicMock()
    fake_resp.text = "<html><body>No contact info.</body></html>"

    def fake_safe_get(url, **kwargs):
        captured.update(kwargs)
        return fake_resp

    monkeypatch.setattr(detail_scraper, "safe_get", fake_safe_get)

    detail_scraper.fetch_job_detail("https://technopark.in/job-details/1?job=X")

    assert "headers" in captured
    assert "Referer" in captured["headers"]


def test_fetch_job_detail_handles_fetch_failure_gracefully(monkeypatch):
    def broken_get(url, **kwargs):
        raise ConnectionError("timeout")

    monkeypatch.setattr(detail_scraper, "safe_get", broken_get)

    result = detail_scraper.fetch_job_detail("https://technopark.in/job-details/1?job=X")

    assert result == {"description": None, "contact_email": None}