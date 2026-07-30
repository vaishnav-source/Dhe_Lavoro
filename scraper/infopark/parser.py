from dataclasses import dataclass
from typing import List

from bs4 import BeautifulSoup


@dataclass
class InfoparkJob:
    posted_date: str
    job_title: str
    company: str
    closing_date: str
    detail_url: str
    source_job_id: str  # trailing numeric id in detail_url


def _extract_job_id(detail_url: str) -> str:
    # e.g. https://infopark.in/company-jobs/details/70/24892 -> "24892"
    return detail_url.rstrip("/").split("/")[-1]


def parse_job_listing_page(html: str) -> List[InfoparkJob]:
    """Parse one page of https://infopark.in/companies-job?page=N into job rows.

    NOTE: selector is deliberately structural (table row -> cells + a details
    link) rather than tied to a specific CSS class, since the class names
    were not confirmed from raw HTML during discovery. Re-verify against
    live HTML (view-source) before first production run, and add a
    regression test fixture (see tests/) so a future site redesign fails
    loudly instead of silently returning zero jobs.
    """
    soup = BeautifulSoup(html, "html.parser")
    jobs: List[InfoparkJob] = []

    table = soup.find("table")
    if table is None:
        return jobs

    rows = table.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue  # header row or malformed row — skip, don't crash

        link_tag = row.find("a", href=True)
        detail_url = link_tag["href"] if link_tag else ""

        job = InfoparkJob(
            posted_date=cells[0].get_text(strip=True),
            job_title=cells[1].get_text(strip=True),
            company=cells[2].get_text(strip=True),
            closing_date=cells[3].get_text(strip=True),
            detail_url=detail_url,
            source_job_id=_extract_job_id(detail_url) if detail_url else "",
        )

        # Basic sanity validation — skip rows missing essentials rather than
        # writing partial/garbage data into the DB.
        if job.job_title and job.company and job.source_job_id:
            jobs.append(job)

    return jobs
