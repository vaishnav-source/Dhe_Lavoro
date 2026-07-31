import scraper.technopark.backfill_details as backfill


def test_run_backfill_skips_jobs_without_detail_url(monkeypatch):
    jobs = [
        {"id": 1, "fingerprint": "fp1", "detail_url": None},
        {"id": 2, "fingerprint": "fp2", "detail_url": "https://technopark.in/job-details/2?job=X"},
    ]
    monkeypatch.setattr(backfill, "get_jobs_missing_detail", lambda source, limit=500: jobs)
    monkeypatch.setattr(
        backfill, "fetch_job_detail",
        lambda url: {"description": "desc", "contact_email": "a@b.com"},
    )
    monkeypatch.setattr(backfill, "summarize_job_description", lambda desc: "short summary")
    update_calls = []
    monkeypatch.setattr(
        backfill, "update_job_detail",
        lambda fingerprint, description, contact_email, short_description=None: update_calls.append(fingerprint),
    )
    monkeypatch.setattr(backfill, "polite_delay", lambda: None)

    stats = backfill.run_backfill()

    assert stats["found"] == 2
    assert stats["updated"] == 1
    assert stats["skipped_no_url"] == 1
    assert update_calls == ["fp2"]


def test_run_backfill_with_no_jobs_found(monkeypatch):
    monkeypatch.setattr(backfill, "get_jobs_missing_detail", lambda source, limit=500: [])
    monkeypatch.setattr(backfill, "polite_delay", lambda: None)

    stats = backfill.run_backfill()

    assert stats == {"found": 0, "updated": 0, "skipped_no_url": 0}