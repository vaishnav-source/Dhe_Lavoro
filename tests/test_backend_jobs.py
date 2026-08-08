import json

import backend.routes.jobs as jobs_module
from backend.app import create_app


class FakeResult:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class FakeQuery:
    """Chainable fake mimicking supabase-py's query builder for the exact
    chains backend/routes/jobs.py uses."""

    def __init__(self, recorder, result):
        self.recorder = recorder
        self._result = result

    def select(self, cols, count=None):
        self.recorder["select_count_arg"] = count
        return self

    def eq(self, col, val):
        self.recorder.setdefault("eq_filters", []).append((col, val))
        return self

    def or_(self, expr):
        self.recorder["or_expr"] = expr
        return self

    def order(self, col, desc=False):
        self.recorder["order"] = (col, desc)
        return self

    def range(self, start, end):
        self.recorder["range"] = (start, end)
        return self

    def execute(self):
        return self._result


class FakeClient:
    def __init__(self, data=None, count=None):
        self.recorder = {}
        self._result = FakeResult(data or [], count)

    def table(self, name):
        self.recorder["table_name"] = name
        return FakeQuery(self.recorder, self._result)


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

    resp = client.get("/api/jobs?page=2&limit=10")

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

    assert "job_title.ilike.%python%" in fake_client.recorder["or_expr"]
    assert "company.ilike.%python%" in fake_client.recorder["or_expr"]


def test_list_jobs_search_strips_commas_to_avoid_breaking_or_filter(monkeypatch):
    fake_client = FakeClient(data=[], count=0)
    client = make_app_client(monkeypatch, fake_client)

    client.get("/api/jobs?search=python,django")

    assert fake_client.recorder["or_expr"] == (
        "job_title.ilike.%pythondjango%,company.ilike.%pythondjango%"
    )


def test_list_jobs_source_filter_applied_when_present(monkeypatch):
    fake_client = FakeClient(data=[], count=0)
    client = make_app_client(monkeypatch, fake_client)

    client.get("/api/jobs?source=infopark")

    assert ("source", "infopark") in fake_client.recorder["eq_filters"]


def test_list_jobs_query_failure_returns_500(monkeypatch):
    class BrokenQuery(FakeQuery):
        def execute(self):
            raise RuntimeError("db down")

    class BrokenClient(FakeClient):
        def table(self, name):
            return BrokenQuery(self.recorder, None)

    client = make_app_client(monkeypatch, BrokenClient())

    resp = client.get("/api/jobs")

    assert resp.status_code == 500
    assert "error" in resp.get_json()


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
            return BrokenQuery(self.recorder, None)

    client = make_app_client(monkeypatch, BrokenClient())

    resp = client.get("/api/jobs/1")

    assert resp.status_code == 500


def test_health_endpoint(monkeypatch):
    fake_client = FakeClient()
    client = make_app_client(monkeypatch, fake_client)

    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"