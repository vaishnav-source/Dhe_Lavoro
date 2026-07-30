import json
from pathlib import Path

from scraper.technopark.parser import parse_paginated_jobs

FIXTURES = Path(__file__).parent / "fixtures"


def load_json(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_parses_bare_array_shape():
    payload = load_json("technopark_sample_array.json")
    jobs = parse_paginated_jobs(payload)
    # 3rd fixture entry has no company name -> must be skipped
    assert len(jobs) == 2


def test_fields_extracted_correctly():
    payload = load_json("technopark_sample_array.json")
    jobs = parse_paginated_jobs(payload)
    first = jobs[0]
    assert first.job_title == "Senior QA Engineer (Manual + Automation)"
    assert first.company_name == "Way Dot Com (P) Ltd"
    assert first.source_job_id == "31800"
    assert first.closing_date == "2026-07-30"


def test_parses_data_wrapped_shape():
    payload = load_json("technopark_sample_wrapped.json")
    jobs = parse_paginated_jobs(payload)
    assert len(jobs) == 1
    assert jobs[0].company_name == "Some Tech LLP"


def test_missing_company_field_is_skipped():
    payload = load_json("technopark_sample_array.json")
    jobs = parse_paginated_jobs(payload)
    titles = [j.job_title for j in jobs]
    assert "Missing company field job" not in titles


def test_unrecognized_shape_returns_empty_list():
    assert parse_paginated_jobs({"unexpected": "shape"}) == []
    assert parse_paginated_jobs("not even a dict or list") == []
