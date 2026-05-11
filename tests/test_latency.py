import pytest

from nettest.probes.latency import run_tls_latency


def test_aggregates_samples(monkeypatch):
    samples = iter([100.0, 110.0, 120.0])
    monkeypatch.setattr(
        "nettest.probes.latency.measure_tls_rtt",
        lambda h, p, t: next(samples),
    )
    r = run_tls_latency("example.com", count=3, timeout_s=1)
    assert r.ok
    d = r.data
    assert d["attempts"] == 3
    assert d["succeeded"] == 3
    assert d["loss_pct"] == 0.0
    assert d["rtt_min"] == 100.0
    assert d["rtt_avg"] == pytest.approx(110.0)
    assert d["rtt_max"] == 120.0
    assert d["rtt_stddev"] == pytest.approx(10.0)
    assert d["rtt_samples"] == [100.0, 110.0, 120.0]


def test_partial_loss(monkeypatch):
    results = iter([100.0, None, 200.0, None])
    monkeypatch.setattr(
        "nettest.probes.latency.measure_tls_rtt",
        lambda h, p, t: next(results),
    )
    r = run_tls_latency("example.com", count=4, timeout_s=1)
    assert r.ok
    assert r.data["succeeded"] == 2
    assert r.data["loss_pct"] == 50.0
    assert r.data["rtt_avg"] == pytest.approx(150.0)


def test_full_loss(monkeypatch):
    monkeypatch.setattr(
        "nettest.probes.latency.measure_tls_rtt",
        lambda h, p, t: None,
    )
    r = run_tls_latency("example.com", count=3, timeout_s=1)
    assert not r.ok
    d = r.data
    assert d["attempts"] == 3
    assert d["succeeded"] == 0
    assert d["loss_pct"] == 100.0
    assert d["rtt_avg"] is None
    assert d["rtt_samples"] == []
    assert "TLS handshakes failed" in (r.error or "")
