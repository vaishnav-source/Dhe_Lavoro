from scraper.common.db_writer import upsert_jobs, mark_stale_jobs_expired


class FakeExecuteResult:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    """Chainable fake mimicking just enough of supabase-py's fluent query
    builder for upsert_jobs() and mark_stale_jobs_expired()."""

    def __init__(self, recorder):
        self.recorder = recorder
        self._mode = None  # "select" | "update" | "upsert"
        self._update_ids = None

    def upsert(self, rows, on_conflict=None):
        self.recorder["upserted_rows"].append(rows)
        self.recorder["on_conflict"] = on_conflict
        self._mode = "upsert"
        return self

    def select(self, cols):
        self._mode = "select"
        return self

    def update(self, values):
        self.recorder.setdefault("update_calls", []).append(values)
        self._mode = "update"
        return self

    def eq(self, col, val):
        self.recorder.setdefault("eq_filters", []).append((col, val))
        return self

    def in_(self, col, values):
        self._update_ids = values
        self.recorder.setdefault("in_calls", []).append((col, values))
        return self

    def is_(self, col, val):
        self.recorder.setdefault("is_filters", []).append((col, val))
        return self

    def limit(self, n):
        self.recorder["limit"] = n
        return self

    def execute(self):
        if self._mode == "select":
            return FakeExecuteResult(data=self.recorder.get("active_rows", []))
        if self._mode == "update":
            return FakeExecuteResult(data=[{"id": i} for i in (self._update_ids or [])] or self.recorder.get("update_result", []))
        if self._mode == "upsert":
            return FakeExecuteResult(data=self.recorder["upserted_rows"][-1])
        return FakeExecuteResult(data=[])


class FakeClient:
    def __init__(self, active_rows=None):
        self.recorder = {"upserted_rows": [], "active_rows": active_rows or []}

    def table(self, name):
        self.recorder["table_name"] = name
        return FakeQuery(self.recorder)


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
    assert len(client.recorder["upserted_rows"]) == 3


def test_mark_stale_jobs_refuses_empty_fingerprint_list():
    client = FakeClient()
    count = mark_stale_jobs_expired("infopark", [], client=client)
    assert count == 0
    assert "update_calls" not in client.recorder


def test_mark_stale_jobs_expires_only_missing_ones():
    active_rows = [
        {"id": 1, "fingerprint": "fp1"},
        {"id": 2, "fingerprint": "fp2"},
        {"id": 3, "fingerprint": "fp3"},
    ]
    client = FakeClient(active_rows=active_rows)

    count = mark_stale_jobs_expired("infopark", ["fp1", "fp3"], client=client)

    assert count == 1
    assert client.recorder["update_calls"] == [{"status": "expired"}]
    assert client.recorder["in_calls"] == [("id", [2])]


def test_mark_stale_jobs_no_stale_rows_skips_update():
    active_rows = [{"id": 1, "fingerprint": "fp1"}]
    client = FakeClient(active_rows=active_rows)

    count = mark_stale_jobs_expired("infopark", ["fp1"], client=client)

    assert count == 0
    assert "update_calls" not in client.recorder


def test_get_jobs_missing_detail_returns_active_rows():
    from scraper.common.db_writer import get_jobs_missing_detail

    active_rows = [{"id": 1, "fingerprint": "fp1", "detail_url": "https://infopark.in/x"}]
    client = FakeClient(active_rows=active_rows)

    jobs = get_jobs_missing_detail("infopark", client=client)

    assert jobs == active_rows
    assert ("contact_email", "null") in client.recorder["is_filters"]


def test_update_job_detail_returns_true_when_row_matched():
    from scraper.common.db_writer import update_job_detail

    client = FakeClient()
    client.recorder["update_result"] = [{"id": 1}]

    updated = update_job_detail("fp1", "some description", "hr@company.com", client=client)

    assert updated is True
    assert client.recorder["update_calls"] == [
        {"description": "some description", "contact_email": "hr@company.com"}
    ]


def test_mark_job_expired_returns_true_when_row_matched():
    from scraper.common.db_writer import mark_job_expired

    client = FakeClient()
    client.recorder["update_result"] = [{"id": 1}]

    result = mark_job_expired("fp1", client=client)

    assert result is True
    assert client.recorder["update_calls"] == [{"status": "expired"}]


def test_mark_job_expired_returns_false_when_no_row_matched():
    from scraper.common.db_writer import mark_job_expired

    client = FakeClient()
    client.recorder["update_result"] = []

    result = mark_job_expired("fp-missing", client=client)

    assert result is False