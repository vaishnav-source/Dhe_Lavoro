from scraper.common.db_writer import upsert_jobs, mark_stale_jobs_expired


class FakeExecuteResult:
    def __init__(self, data):
        self.data = data


class FakeTableQuery:
    """Chainable fake mimicking supabase-py's fluent query builder just
    enough for our two functions under test."""

    def __init__(self, recorder):
        self.recorder = recorder
        self._filters = {}

    def upsert(self, rows, on_conflict=None):
        self.recorder["upserted_rows"].append(rows)
        self.recorder["on_conflict"] = on_conflict
        return self

    def update(self, values):
        self.recorder["updated_values"] = values
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def not_(self):
        return self

    def in_(self, col, values):
        self._filters[f"not_in_{col}"] = values
        return self

    def execute(self):
        self.recorder["executed_filters"] = self._filters
        return FakeExecuteResult(data=[{"id": 1}, {"id": 2}])


class FakeNotProxy:
    def __init__(self, query):
        self.query = query

    def in_(self, col, values):
        self.query._filters[f"not_in_{col}"] = values
        return self.query


class FakeTableQueryWithNot(FakeTableQuery):
    @property
    def not_(self):
        return FakeNotProxy(self)


class FakeClient:
    def __init__(self):
        self.recorder = {"upserted_rows": []}

    def table(self, name):
        self.recorder["table_name"] = name
        return FakeTableQueryWithNot(self.recorder)


def make_job(source, source_job_id, fingerprint):
    return {
        "source": source,
        "source_job_id": source_job_id,
        "fingerprint": fingerprint,
        "job_title": f"Job {source_job_id}",
        "company": "Some Company",
        "posted_date": "2026-07-29",
        "closing_date": "2026-08-05",
        "detail_url": f"https://{source}.in/job/{source_job_id}",
    }


def test_upsert_jobs_empty_list_writes_nothing():
    client = FakeClient()
    written = upsert_jobs([], client=client)
    assert written == 0
    assert client.recorder["upserted_rows"] == []


def test_upsert_jobs_writes_expected_row_count():
    client = FakeClient()
    jobs = [make_job("infopark", str(i), f"fp{i}") for i in range(3)]
    written = upsert_jobs(jobs, client=client)
    assert written == 3
    assert len(client.recorder["upserted_rows"][0]) == 3
    assert client.recorder["on_conflict"] == "fingerprint"


def test_upsert_jobs_batches_large_input(monkeypatch):
    import scraper.common.db_writer as db_writer

    monkeypatch.setattr(db_writer, "BATCH_SIZE", 2)
    client = FakeClient()
    jobs = [make_job("infopark", str(i), f"fp{i}") for i in range(5)]
    written = upsert_jobs(jobs, client=client)
    assert written == 5
    # 5 jobs at batch size 2 -> 3 separate upsert calls
    assert len(client.recorder["upserted_rows"]) == 3


def test_mark_stale_jobs_refuses_empty_fingerprint_list():
    client = FakeClient()
    count = mark_stale_jobs_expired("infopark", [], client=client)
    assert count == 0
    # must not have executed any update — safety guard against
    # accidentally expiring every active row for a source
    assert "updated_values" not in client.recorder


def test_mark_stale_jobs_executes_with_correct_filters():
    client = FakeClient()
    count = mark_stale_jobs_expired("infopark", ["fp1", "fp2"], client=client)
    assert count == 2
    assert client.recorder["updated_values"] == {"status": "expired"}
