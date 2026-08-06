import scraper.run_all as run_all


def test_run_all_calls_every_step_in_order(monkeypatch):
    call_order = []

    fake_steps = [
        ("step_a", lambda: call_order.append("step_a") or {"ok": True}),
        ("step_b", lambda: call_order.append("step_b") or {"ok": True}),
        ("step_c", lambda: call_order.append("step_c") or {"ok": True}),
    ]
    monkeypatch.setattr(run_all, "STEPS", fake_steps)

    results = run_all.run_all()

    assert call_order == ["step_a", "step_b", "step_c"]
    assert set(results.keys()) == {"step_a", "step_b", "step_c"}
    assert all(r == {"ok": True} for r in results.values())


def test_run_all_isolates_step_failure(monkeypatch):
    call_order = []

    def broken_step():
        call_order.append("broken")
        raise RuntimeError("something went wrong")

    def ok_step():
        call_order.append("ok")
        return {"found": 1}

    monkeypatch.setattr(run_all, "STEPS", [
        ("broken_step", broken_step),
        ("ok_step", ok_step),
    ])

    results = run_all.run_all()

    # both steps ran despite the first one failing
    assert call_order == ["broken", "ok"]
    assert results["broken_step"]["failed"] is True
    assert "something went wrong" in results["broken_step"]["error"]
    assert results["ok_step"] == {"found": 1}


def test_run_all_step_order_matches_pipeline_dependencies():
    """Sanity check on the real STEPS list — scrape before detail backfill,
    detail backfill before summaries, cleanup last."""
    names = [name for name, _ in run_all.STEPS]
    assert names.index("scrape_and_upsert") < names.index("infopark_backfill_details")
    assert names.index("infopark_backfill_details") < names.index("infopark_backfill_summaries")
    assert names.index("technopark_backfill_details") < names.index("technopark_backfill_summaries")
    assert names[-1] == "cleanup_expired"


def test_run_forever_calls_run_all_and_sleeps_each_cycle(monkeypatch):
    call_count = {"n": 0}

    def fake_run_all():
        call_count["n"] += 1
        if call_count["n"] >= 3:
            raise KeyboardInterrupt  # stop the infinite loop for the test

    sleep_calls = []
    monkeypatch.setattr(run_all, "run_all", fake_run_all)
    monkeypatch.setattr(run_all.time, "sleep", lambda s: sleep_calls.append(s))

    try:
        run_all.run_forever(interval_days=2)
    except KeyboardInterrupt:
        pass

    assert call_count["n"] == 3
    assert sleep_calls == [2 * 24 * 60 * 60, 2 * 24 * 60 * 60]