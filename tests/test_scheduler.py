import scraper.scheduler as scheduler


def fake_job(source, i):
    return {
        "source": source,
        "source_job_id": str(i),
        "fingerprint": f"{source}-{i}",
        "job_title": f"Job {i}",
        "company": "Co",
    }


def test_run_source_happy_path(monkeypatch):
    jobs = [fake_job("infopark", 1), fake_job("infopark", 2)]

    monkeypatch.setattr(scheduler, "upsert_jobs", lambda j: len(j))
    monkeypatch.setattr(scheduler, "mark_stale_jobs_expired", lambda src, fps: 1)

    stats = scheduler.run_source("infopark", lambda: jobs)

    assert stats == {"scraped": 2, "written": 2, "expired": 1, "failed": False}


def test_run_source_isolates_scraper_failure(monkeypatch):
    def broken_scraper():
        raise RuntimeError("site changed layout")

    monkeypatch.setattr(scheduler, "upsert_jobs", lambda j: 0)
    monkeypatch.setattr(scheduler, "mark_stale_jobs_expired", lambda src, fps: 0)

    stats = scheduler.run_source("technopark", broken_scraper)

    assert stats["failed"] is True
    assert stats["scraped"] == 0


def test_run_once_calls_every_configured_source(monkeypatch):
    calls = []

    def fake_run_source(name, fn):
        calls.append(name)
        return {"scraped": 0, "written": 0, "expired": 0, "failed": False}

    monkeypatch.setattr(scheduler, "run_source", fake_run_source)

    results = scheduler.run_once()

    assert calls == [name for name, _ in scheduler.SOURCES]
    assert set(results.keys()) == {name for name, _ in scheduler.SOURCES}


def test_run_source_upsert_failure_is_isolated(monkeypatch):
    jobs = [fake_job("infopark", 1)]

    def broken_upsert(j):
        raise ConnectionError("db unreachable")

    monkeypatch.setattr(scheduler, "upsert_jobs", broken_upsert)
    monkeypatch.setattr(scheduler, "mark_stale_jobs_expired", lambda src, fps: 0)

    stats = scheduler.run_source("infopark", lambda: jobs)

    assert stats["failed"] is True
    assert stats["scraped"] == 1  # scrape succeeded before the db call broke
