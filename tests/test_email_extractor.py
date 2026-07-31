from pathlib import Path

from scraper.common.email_extractor import extract_contact_email

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_prefers_mailto_link_over_plain_text():
    html = load("detail_page_with_mailto.html")
    assert extract_contact_email(html) == "hr@somecompany.com"


def test_prefers_labeled_contact_email_field():
    html = load("detail_page_labeled_field.html")
    assert extract_contact_email(html) == "careers@techversantinfotech.com"


def test_falls_back_to_plain_text_email():
    html = load("detail_page_plain_text_email.html")
    assert extract_contact_email(html) == "careers@anothercompany.co.in"


def test_ignores_generic_park_domain_email():
    html = load("detail_page_noise_only.html")
    assert extract_contact_email(html) is None


def test_no_email_present_returns_none():
    assert extract_contact_email("<html><body>No contact here.</body></html>") is None
