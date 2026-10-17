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

    def limit(self, n):
        self.call_record["limit"] = n
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
    # call 0 = count query, call 1 = the actual page slice
    assert fake_client.calls[1]["range"] == (10, 19)


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


class MemoryQuery:
    """Tiny in-memory stand-in for a supabase query over a list of rows.
    Honors eq(), order(), limit(), range() and count="exact" like
    PostgREST — including raising when range() starts past the end of
    the rows, which is what caused the old "page 38 -> 500" bug."""

    def __init__(self, rows):
        self._rows = rows
        self._count = False
        self._limit = None
        self._range = None
        self._desc = False

    def select(self, cols, count=None):
        self._count = count == "exact"
        return self

    def eq(self, col, val):
        self._rows = [r for r in self._rows if r.get(col) == val]
        return self

    def order(self, col, desc=False):
        self._rows = sorted(self._rows, key=lambda r: r[col], reverse=desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def execute(self):
        total = len(self._rows)
        rows = self._rows
        if self._range is not None:
            start, end = self._range
            if start >= total and total > 0:
                raise RuntimeError("416 Requested range not satisfiable")
            rows = rows[start:end + 1]
        if self._limit is not None:
            rows = rows[:self._limit]
        return FakeResult(rows, total if self._count else None)


class MemoryClient:
    def __init__(self, rows):
        self.rows = rows
        self.calls = 0

    def table(self, name):
        self.calls += 1
        return MemoryQuery(list(self.rows))


def make_rows(infopark, technopark):
    rows = []
    for i in range(infopark):
        rows.append({"id": 1000 + i, "source": "infopark", "status": "active"})
    for i in range(technopark):
        rows.append({"id": 5000 + i, "source": "technopark", "status": "active"})
    return rows


def fetch_all_pages(client, limit=20, query=""):
    ids, page, total = [], 1, None
    while True:
        body = client.get(f"/api/jobs?page={page}&limit={limit}{query}").get_json()
        assert "error" not in body, f"page {page} failed"
        total = body["total"]
        ids.extend(j["id"] for j in body["jobs"])
        if page >= -(-total // limit):
            return ids, total
        page += 1


def test_all_parks_unbalanced_sources_every_page_works_and_every_job_reachable(monkeypatch):
    # Regression: 365 vs 445 jobs. Old code asked the smaller source for
    # rows past its end around page 37 -> HTTP 500.
    rows = make_rows(365, 445)
    client = make_app_client(monkeypatch, MemoryClient(rows))

    ids, total = fetch_all_pages(client, limit=20)

    assert total == 810
    assert len(ids) == 810            # no page lost jobs
    assert len(set(ids)) == 810       # no duplicates across pages


def test_all_parks_pages_are_full_until_the_last(monkeypatch):
    client = make_app_client(monkeypatch, MemoryClient(make_rows(365, 445)))

    sizes = [
        len(client.get(f"/api/jobs?page={p}&limit=20").get_json()["jobs"])
        for p in range(1, 42)
    ]

    assert sizes[:40] == [20] * 40
    assert sizes[40] == 10            # 810 = 40 full pages + 10


def test_all_parks_first_page_mixes_both_sources_newest_first(monkeypatch):
    client = make_app_client(monkeypatch, MemoryClient(make_rows(50, 50)))

    jobs = client.get("/api/jobs?page=1&limit=20").get_json()["jobs"]

    assert [j["source"] for j in jobs[:4]] == [
        "infopark", "technopark", "infopark", "technopark",
    ]
    infopark_ids = [j["id"] for j in jobs if j["source"] == "infopark"]
    assert infopark_ids == sorted(infopark_ids, reverse=True)


def test_all_parks_one_source_empty_still_paginates(monkeypatch):
    client = make_app_client(monkeypatch, MemoryClient(make_rows(0, 45)))

    ids, total = fetch_all_pages(client, limit=20)

    assert total == 45
    assert len(set(ids)) == 45


def test_all_parks_page_past_the_end_returns_empty_not_500(monkeypatch):
    client = make_app_client(monkeypatch, MemoryClient(make_rows(10, 10)))

    resp = client.get("/api/jobs?page=99&limit=20")

    assert resp.status_code == 200
    assert resp.get_json()["jobs"] == []
    assert resp.get_json()["total"] == 20


def test_single_source_page_past_the_end_returns_empty_not_500(monkeypatch):
    client = make_app_client(monkeypatch, MemoryClient(make_rows(10, 10)))

    resp = client.get("/api/jobs?source=infopark&page=99&limit=20")

    assert resp.status_code == 200
    assert resp.get_json()["jobs"] == []
    assert resp.get_json()["total"] == 10


def test_single_source_last_partial_page(monkeypatch):
    client = make_app_client(monkeypatch, MemoryClient(make_rows(25, 10)))

    body = client.get("/api/jobs?source=infopark&page=2&limit=20").get_json()

    assert len(body["jobs"]) == 5
    assert all(j["source"] == "infopark" for j in body["jobs"])


def test_all_parks_counts_each_source_separately(monkeypatch):
    fake_client = FakeClient(data=[], count=0)
    client = make_app_client(monkeypatch, fake_client)

    client.get("/api/jobs")

    assert len(fake_client.calls) == 2
    assert ("source", "infopark") in fake_client.calls[0]["eq_filters"]
    assert ("source", "technopark") in fake_client.calls[1]["eq_filters"]


def test_single_source_with_no_matches_issues_only_the_count_query(monkeypatch):
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