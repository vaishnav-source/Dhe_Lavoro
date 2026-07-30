from pathlib import Path

from scraper.infopark.parser import parse_job_listing_page

FIXTURE = Path(__file__).parent / "fixtures" / "infopark_sample.html"


def load_fixture() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def test_parses_expected_number_of_valid_jobs():
    jobs = parse_job_listing_page(load_fixture())
    # 2 valid rows + 1 malformed row that must be skipped, not crash
    assert len(jobs) == 2


def test_fields_extracted_correctly():
    jobs = parse_job_listing_page(load_fixture())
    first = jobs[0]
    assert first.job_title == "Full-Stack Developer"
    assert first.company == "Difinity Digital"
    assert first.posted_date == "29-07-2026"
    assert first.closing_date == "15 Aug 2026"
    assert first.source_job_id == "24887"


def test_empty_html_returns_empty_list():
    assert parse_job_listing_page("<html><body>no table here</body></html>") == []


def test_malformed_row_does_not_crash_or_appear():
    jobs = parse_job_listing_page(load_fixture())
    titles = [j.job_title for j in jobs]
    assert "Malformed row with too few cells" not in titles
