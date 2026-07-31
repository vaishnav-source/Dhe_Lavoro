from dataclasses import dataclass
from typing import List, Any
from urllib.parse import quote

from scraper.common.config import TECHNOPARK_DETAIL_URL_TEMPLATE


@dataclass
class TechnoparkJob:
    source_job_id: str
    job_listing_id: str
    job_title: str
    posted_date: str
    closing_date: str
    company_id: str
    company_name: str
    detail_url: str


def _extract_job_list(payload: Any) -> list:
    """Handle both possible response shapes seen from this Laravel-style API:
    a bare JSON array, or an object wrapping the array under a 'data' key
    (standard Laravel paginate() shape). Anything else -> empty list, so a
    future API-shape change fails a test loudly instead of crashing silently
    downstream."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "jobs", "results"):
            if key in payload and isinstance(payload[key], list):
                return payload[key]
    return []


def parse_paginated_jobs(payload: Any) -> List[TechnoparkJob]:
    raw_jobs = _extract_job_list(payload)
    jobs: List[TechnoparkJob] = []

    for item in raw_jobs:
        if not isinstance(item, dict):
            continue

        company = item.get("company") or {}
        job_id = item.get("id")
        job_title = item.get("job_title")
        company_name = company.get("company")

        # Skip anything missing the essentials rather than storing garbage.
        if job_id is None or not job_title or not company_name:
            continue

        job_id_str = str(job_id)
        detail_url = TECHNOPARK_DETAIL_URL_TEMPLATE.format(
            job_id=job_id_str, title=quote(job_title)
        )

        jobs.append(
            TechnoparkJob(
                source_job_id=job_id_str,
                job_listing_id=str(item.get("job_listing_id", "")),
                job_title=job_title,
                posted_date=item.get("posted_date", ""),
                closing_date=item.get("closing_date", ""),
                company_id=str(item.get("company_id", "")),
                company_name=company_name,
                detail_url=detail_url,
            )
        )

    return jobs