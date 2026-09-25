
import backend.routes.jobs as jobs_module
from backend.app import create_app


class FakeResult:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class FakeQuery:
    """Chainable fake mimicking supabase-py's query builder for the exact
    chains backend/routes/jobs.py uses. Records into a per-call dict
    (rather than one shared dict) so a test can distinguish between
    multiple .table() calls in the same request — e.g. the two per-source
    queries an unfiltered "All Parks" request now issues."""

    def __init__(self, call_record, result):
        self.call_record = call_record
        self._result = result

    def select(self, cols, count=None):
        self.call_record["select_count_arg"] = count
        return self

    def eq(self, col, val):
        self.call_record.setdefault("eq_filters", []).append((col, val))
        return self

    def lte(self, col, val):
        self.call_record.setdefault("lte_filters", []).append((col, val))
        return self

    def or_(self, expr):
        # Real postgrest-py appends each or_() call as its own ANDed OR
        # group rather than overwriting — mirror that here so tests can
        # tell "search" and "exp_min" filters apart when both are set.
        self.call_record.setdefault("or_exprs", []).append(expr)
        return self

    @property
    def not_(self):
        return self

    def is_(self, col, val):
        self.call_record.setdefault("is_filters", []).append((col, val))
        return self

    def order(self, col, desc=False):
        self.call_record["order"] = (col, desc)
        return self

    def range(self, start, end):
        self.call_record["range"] = (start, end)
        return self

    def execute(self):
        return self._result


class FakeClient:
    """Records one call dict per .table() invocation, in order, in
    self.calls. For the common single-query-per-request tests, the same
    (data, count) result is returned to every call — pass an explicit
    `results` list instead when a test needs to give distinct fake data
    to each of several calls (e.g. one per source)."""

    def __init__(self, data=None, count=None, results=None):
        self.calls = []
        if results is not None:
            self._results = list(results)
        else:
            self._results = None
            self._default_result = FakeResult(data or [], count)

    def table(self, name):
        call_record = {"table_name": name}
        self.calls.append(call_record)
        if self._results is not None:
            result = self._results[len(self.calls) - 1]
        else:
            result = self._default_result
        return FakeQuery(call_record, result)

    @property
    def recorder(self):
        """Back-compat for existing single-call tests: the first (and
        typically only) call's record."""
        return self.calls[0] if self.calls else {}


def make_app_client(monkeypatch, fake_client):
    monkeypatch.setattr(jobs_module, "get_client", lambda: fake_client)
    app = create_app()
    app.testing = True
    return app.test_client()


def test_list_jobs_always_filters_active_status(monkeypatch):
    fake_client = FakeClient(data=[{"id": 1, "job_title": "Dev"}], count=1)
    client = make_app_client(monkeypatch, fake_client)

    resp = client.get("/api/jobs")

    assert resp.status_code == 200
    assert ("status", "active") in fake_client.recorder["eq_filters"]


def test_list_jobs_returns_pagination_metadata(monkeypatch):
    fake_client = FakeClient(data=[{"id": 1}], count=42)
    client = make_app_client(monkeypatch, fake_client)

    resp = client.get("/api/jobs?source=infopark&page=2&limit=10")

    body = resp.get_json()
    assert body["page"] == 2
    assert body["limit"] == 10
    assert body["total"] == 42
    assert fake_client.recorder["range"] == (10, 19)


def test_list_jobs_limit_is_capped(monkeypatch):
    fake_client = FakeClient(data=[], count=0)
    client = make_app_client(monkeypatch, fake_client)

    resp = client.get("/api/jobs?limit=99999")

    body = resp.get_json()
    assert body["limit"] == 100  # MAX_LIMIT


def test_list_jobs_invalid_page_param_falls_back_to_default(monkeypatch):
    fake_client = FakeClient(data=[], count=0)
    client = make_app_client(monkeypatch, fake_client)

    resp = client.get("/api/jobs?page=notanumber")

    body = resp.get_json()
    assert body["page"] == 1


def test_list_jobs_search_builds_or_filter_on_title_and_company(monkeypatch):
    fake_client = FakeClient(data=[], count=0)
    client = make_app_client(monkeypatch, fake_client)

    client.get("/api/jobs?search=python")

    assert "job_title.ilike.%python%" in fake_client.recorder["or_exprs"][0]
    assert "company.ilike.%python%" in fake_client.recorder["or_exprs"][0]


def test_list_jobs_search_strips_commas_to_avoid_breaking_or_filter(monkeypatch):
    fake_client = FakeClient(data=[], count=0)
    client = make_app_client(monkeypatch, fake_client)

    client.get("/api/jobs?search=python,django")

    assert fake_client.recorder["or_exprs"][0] == (
        "job_title.ilike.%pythondjango%,company.ilike.%pythondjango%"
    )


def test_list_jobs_source_filter_applied_when_present(monkeypatch):
    fake_client = FakeClient(data=[], count=0)
    client = make_app_client(monkeypatch, fake_client)

    client.get("/api/jobs?source=infopark")

    assert ("source", "infopark") in fake_client.recorder["eq_filters"]


def test_list_jobs_no_exp_params_skips_experience_filter(monkeypatch):
    fake_client = FakeClient(data=[], count=0)
    client = make_app_client(monkeypatch, fake_client)

    client.get("/api/jobs")

    assert "is_filters" not in fake_client.recorder
    assert "lte_filters" not in fake_client.recorder


def test_list_jobs_exp_min_excludes_unextracted_rows(monkeypatch):
    fake_client = FakeClient(data=[], count=0)
    client = make_app_client(monkeypatch, fake_client)

    client.get("/api/jobs?exp_min=3")

    assert ("experience_min", "null") in fake_client.recorder["is_filters"]


def test_list_jobs_exp_min_builds_overlap_or_filter(monkeypatch):
    fake_client = FakeClient(data=[], count=0)
    client = make_app_client(monkeypatch, fake_client)

    client.get("/api/jobs?exp_min=3")

    or_exprs = fake_client.recorder["or_exprs"]
    assert "experience_max.gte.3" in or_exprs[0]
    assert "experience_max.is.null" in or_exprs[0]


def test_list_jobs_exp_max_filters_experience_min_lte(monkeypatch):
    fake_client = FakeClient(data=[], count=0)
    client = make_app_client(monkeypatch, fake_client)

    client.get("/api/jobs?exp_max=5")

    assert ("experience_min", 5) in fake_client.recorder["lte_filters"]
    assert ("experience_min", "null") in fake_client.recorder["is_filters"]


def test_list_jobs_exp_min_and_max_both_applied(monkeypatch):
    fake_client = FakeClient(data=[], count=0)
    client = make_app_client(monkeypatch, fake_client)

    client.get("/api/jobs?exp_min=3&exp_max=5")

    assert "experience_max.gte.3" in fake_client.recorder["or_exprs"][0]
    assert ("experience_min", 5) in fake_client.recorder["lte_filters"]


def test_list_jobs_search_and_exp_filter_combine(monkeypatch):
    fake_client = FakeClient(data=[], count=0)
    client = make_app_client(monkeypatch, fake_client)

    client.get("/api/jobs?search=python&exp_min=3")

    or_exprs = fake_client.recorder["or_exprs"]
    assert "job_title.ilike.%python%" in or_exprs[0]
    assert "experience_max.gte.3" in or_exprs[1]


def test_list_jobs_invalid_exp_param_is_ignored(monkeypatch):
    fake_client = FakeClient(data=[], count=0)
    client = make_app_client(monkeypatch, fake_client)

    resp = client.get("/api/jobs?exp_min=notanumber")

    assert resp.status_code == 200
    assert "is_filters" not in fake_client.recorder


def test_list_jobs_query_failure_returns_500(monkeypatch):
    class BrokenQuery(FakeQuery):
        def execute(self):
            raise RuntimeError("db down")

    class BrokenClient(FakeClient):
        def table(self, name):
            return BrokenQuery({}, None)

    client = make_app_client(monkeypatch, BrokenClient())

    resp = client.get("/api/jobs")

    assert resp.status_code == 500
    assert "error" in resp.get_json()


def test_list_jobs_all_parks_queries_each_source_separately(monkeypatch):
    fake_client = FakeClient(data=[], count=0)
    client = make_app_client(monkeypatch, fake_client)

    client.get("/api/jobs")

    assert len(fake_client.calls) == 2
    assert ("source", "infopark") in fake_client.calls[0]["eq_filters"]
    assert ("source", "technopark") in fake_client.calls[1]["eq_filters"]


def test_list_jobs_all_parks_combines_counts_from_both_sources(monkeypatch):
    fake_client = FakeClient(
        results=[
            FakeResult([{"id": 1, "source": "infopark"}], count=30),
            FakeResult([{"id": 2, "source": "technopark"}], count=12),
        ]
    )
    client = make_app_client(monkeypatch, fake_client)

    resp = client.get("/api/jobs?limit=20")

    body = resp.get_json()
    assert body["total"] == 42  # 30 + 12, not just one source's count
    sources_returned = {job["source"] for job in body["jobs"]}
    assert sources_returned == {"infopark", "technopark"}


def test_list_jobs_all_parks_splits_limit_evenly_per_source(monkeypatch):
    fake_client = FakeClient(data=[], count=0)
    client = make_app_client(monkeypatch, fake_client)

    client.get("/api/jobs?limit=20&page=1")

    # 20 split across 2 sources = 10 each, starting at offset 0
    assert fake_client.calls[0]["range"] == (0, 9)
    assert fake_client.calls[1]["range"] == (0, 9)


def test_list_jobs_all_parks_offset_advances_per_source_on_later_pages(monkeypatch):
    fake_client = FakeClient(data=[], count=0)
    client = make_app_client(monkeypatch, fake_client)

    client.get("/api/jobs?limit=20&page=2")

    # page 2 of a 20-per-page, 2-source split = offset 10 within each
    # source's own 10-per-page half, i.e. rows 10-19 of that source
    assert fake_client.calls[0]["range"] == (10, 19)
    assert fake_client.calls[1]["range"] == (10, 19)


def test_list_jobs_all_parks_trims_combined_results_to_requested_limit(monkeypatch):
    fake_client = FakeClient(
        results=[
            FakeResult([{"id": i} for i in range(10)], count=10),
            FakeResult([{"id": i} for i in range(10, 20)], count=10),
        ]
    )
    client = make_app_client(monkeypatch, fake_client)

    resp = client.get("/api/jobs?limit=15")

    body = resp.get_json()
    assert len(body["jobs"]) == 15  # 10 + 10 combined, trimmed to the 15 asked for


def test_list_jobs_single_source_still_issues_only_one_query(monkeypatch):
    fake_client = FakeClient(data=[], count=0)
    client = make_app_client(monkeypatch, fake_client)

    client.get("/api/jobs?source=infopark")

    assert len(fake_client.calls) == 1


def test_get_job_returns_job_when_found(monkeypatch):
    fake_client = FakeClient(data=[{"id": 5, "job_title": "Backend Dev"}])
    client = make_app_client(monkeypatch, fake_client)

    resp = client.get("/api/jobs/5")

    assert resp.status_code == 200
    assert resp.get_json()["job_title"] == "Backend Dev"
    assert ("status", "active") in fake_client.recorder["eq_filters"]
    assert ("id", 5) in fake_client.recorder["eq_filters"]


def test_get_job_returns_404_when_not_found(monkeypatch):
    fake_client = FakeClient(data=[])
    client = make_app_client(monkeypatch, fake_client)

    resp = client.get("/api/jobs/999")

    assert resp.status_code == 404


def test_get_job_query_failure_returns_500(monkeypatch):
    class BrokenQuery(FakeQuery):
        def execute(self):
            raise RuntimeError("db down")

    class BrokenClient(FakeClient):
        def table(self, name):
            return BrokenQuery({}, None)

    client = make_app_client(monkeypatch, BrokenClient())

    resp = client.get("/api/jobs/1")

    assert resp.status_code == 500


def test_health_endpoint(monkeypatch):
    fake_client = FakeClient()
    client = make_app_client(monkeypatch, fake_client)

    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"