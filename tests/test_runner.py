import time
from nettest.runner import run_concurrent
from nettest.types import ProbeResult


def _fake_probe(target: str, sleep_s: float = 0.05) -> ProbeResult:
    time.sleep(sleep_s)
    return ProbeResult(target=target, ok=True, data={"target": target})


def test_run_concurrent_returns_results_in_target_order():
    targets = ["a", "b", "c", "d"]
    results = run_concurrent(targets, lambda t: _fake_probe(t, 0.05), max_workers=4)
    assert [r.target for r in results] == targets
    assert all(r.ok for r in results)


def test_run_concurrent_runs_in_parallel_faster_than_serial():
    targets = ["a", "b", "c", "d"]
    started = time.monotonic()
    run_concurrent(targets, lambda t: _fake_probe(t, 0.1), max_workers=4)
    elapsed = time.monotonic() - started
    # serial would be ~0.4s; parallel should be well under 0.25s
    assert elapsed < 0.25, f"runner was not concurrent: {elapsed:.3f}s"


def test_run_concurrent_isolates_failures():
    def flaky(target: str) -> ProbeResult:
        if target == "bad":
            raise RuntimeError("boom")
        return _fake_probe(target, 0)

    results = run_concurrent(["a", "bad", "c"], flaky, max_workers=4)
    assert [r.target for r in results] == ["a", "bad", "c"]
    assert results[0].ok is True
    assert results[1].ok is False
    assert "boom" in (results[1].error or "")
    assert results[2].ok is True
