from unittest.mock import MagicMock

import requests

import scraper.infopark.detail_scraper as detail_scraper


def test_fetch_job_detail_extracts_email_and_description(monkeypatch):
    fake_resp = MagicMock()
    fake_resp.text = (
        '<html><body><p>Job desc here.</p>'
        '<a href="mailto:hr@company.com">Apply</a></body></html>'
    )
    monkeypatch.setattr(detail_scraper, "safe_get", lambda url: fake_resp)

    result = detail_scraper.fetch_job_detail("https://infopark.in/company-jobs/details/1/2")

    assert result["contact_email"] == "hr@company.com"
    assert "Job desc here" in result["description"]
    assert result["not_found"] is False


def test_fetch_job_detail_handles_fetch_failure_gracefully(monkeypatch):
    def broken_get(url):
        raise ConnectionError("timeout")

    monkeypatch.setattr(detail_scraper, "safe_get", broken_get)

    result = detail_scraper.fetch_job_detail("https://infopark.in/company-jobs/details/1/2")

    assert result == {"description": None, "contact_email": None, "not_found": False}


def test_fetch_job_detail_caps_description_length(monkeypatch):
    fake_resp = MagicMock()
    fake_resp.text = "<html><body>" + ("word " * 2000) + "</body></html>"
    monkeypatch.setattr(detail_scraper, "safe_get", lambda url: fake_resp)

    result = detail_scraper.fetch_job_detail("https://infopark.in/company-jobs/details/1/2")

    assert len(result["description"]) <= 5000


def test_fetch_job_detail_404_sets_not_found_flag(monkeypatch):
    fake_response = MagicMock()
    fake_response.status_code = 404

    def raises_404(url):
        error = requests.HTTPError("404 Client Error: Not Found")
        error.response = fake_response
        raise error

    monkeypatch.setattr(detail_scraper, "safe_get", raises_404)

    result = detail_scraper.fetch_job_detail("https://infopark.in/company-jobs/details/1/999")

    assert result == {"description": None, "contact_email": None, "not_found": True}


def test_fetch_job_detail_non_404_http_error_not_marked_not_found(monkeypatch):
    fake_response = MagicMock()
    fake_response.status_code = 500

    def raises_500(url):
        error = requests.HTTPError("500 Server Error")
        error.response = fake_response
        raise error

    monkeypatch.setattr(detail_scraper, "safe_get", raises_500)

    result = detail_scraper.fetch_job_detail("https://infopark.in/company-jobs/details/1/2")

    assert result["not_found"] is False