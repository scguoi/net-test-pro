import json

from nettest import cli
from nettest.types import ProbeResult


def _fake_latency(target):
    return ProbeResult(target=target, ok=True, data={
        "rtt_avg": 10.0 if "." not in target or target.startswith("2") else 150.0,
        "rtt_stddev": 1.0,
        "loss_pct": 0.0,
    })


def _fake_dig(server, domain):
    return ProbeResult(target=server, ok=True, data={"query_time_ms": 30, "ips": ["1.2.3.4"]})


def _fake_tr(target):
    return ProbeResult(target=target, ok=True, data={
        "hops": [{"hop": 1, "rtt_ms": 1.0, "ip": "192.168.1.1", "lost": False}],
        "reached": True,
    })


def _fake_curl(target):
    return ProbeResult(target=target, ok=True, data={
        "dns_ms": 10, "connect_ms": 10, "tls_ms": 30, "ttfb_ms": 50, "total_ms": 100,
        "http_code": 200, "ok": True,
    })


def _fake_nq():
    return ProbeResult(target="networkQuality", ok=True, data={
        "dl_mbps": 200, "ul_mbps": 40, "rpm": 800,
        "idle_latency_ms": 10, "loaded_latency_ms": 30,
    })


def _fake_env():
    return {
        "wifi": {"ssid": "TestWiFi", "signal_dbm": -50, "channel": "36"},
        "interface": "en0",
        "local_ip": "192.168.1.42",
        "public_ip": "1.2.3.4",
        "location": "Test, TT",
        "org": "Test Org",
        "system_dns": ["192.168.1.1"],
    }


def test_smoke_runs_end_to_end_with_fakes(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("nettest.cli.run_tls_latency", _fake_latency)
    monkeypatch.setattr("nettest.cli.run_dig", _fake_dig)
    monkeypatch.setattr("nettest.cli.run_traceroute", _fake_tr)
    monkeypatch.setattr("nettest.cli.run_curl", _fake_curl)
    monkeypatch.setattr("nettest.cli.run_networkquality", _fake_nq)
    monkeypatch.setattr("nettest.cli.collect_environment", _fake_env)
    monkeypatch.setattr("nettest.cli.save_snapshot", lambda snap: tmp_path / "snap.json")

    rc = cli.main(["--json"])
    assert rc == 0
    out, err = capsys.readouterr()
    payload = json.loads(out)
    assert payload["env"]["wifi"]["ssid"] == "TestWiFi"
    assert len(payload["latency"]) == 8
    assert len(payload["dns"]) == 5  # system DNS (192.168.1.1) + 4 fixed servers
    assert any(r["target"] == "192.168.1.1" for r in payload["dns"])
    assert payload["bandwidth"]["data"]["dl_mbps"] == 200
    assert "diagnostic" in payload
