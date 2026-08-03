import scraper.technopark.backfill_summaries as backfill


def test_summarizes_and_updates_jobs_missing_summary(monkeypatch):
    jobs = [
        {"id": 1, "fingerprint": "fp1", "description": "desc1", "contact_email": "a@b.com"},
    ]
    monkeypatch.setattr(backfill, "get_jobs_missing_summary", lambda source, limit=500: jobs)
    monkeypatch.setattr(backfill, "summarize_job_description", lambda desc: f"summary of {desc}")

    update_calls = []
    monkeypatch.setattr(
        backfill, "update_job_detail",
        lambda fingerprint, description, contact_email, short_description: update_calls.append(
            (fingerprint, short_description)
        ),
    )

    stats = backfill.run_summary_backfill()

    assert stats == {"found": 1, "updated": 1}
    assert update_calls == [("fp1", "summary of desc1")]


def test_skips_jobs_where_summarizer_still_returns_none(monkeypatch):
    jobs = [{"id": 1, "fingerprint": "fp1", "description": "desc1", "contact_email": "a@b.com"}]
    monkeypatch.setattr(backfill, "get_jobs_missing_summary", lambda source, limit=500: jobs)
    monkeypatch.setattr(backfill, "summarize_job_description", lambda desc: None)

    update_calls = []
    monkeypatch.setattr(
        backfill, "update_job_detail",
        lambda **kwargs: update_calls.append(kwargs),
    )

    stats = backfill.run_summary_backfill()

    assert stats == {"found": 1, "updated": 0}
    assert update_calls == []


def test_no_jobs_found(monkeypatch):
    monkeypatch.setattr(backfill, "get_jobs_missing_summary", lambda source, limit=500: [])

    stats = backfill.run_summary_backfill()

    assert stats == {"found": 0, "updated": 0}