from nettest.probes.bandwidth import parse_networkquality_output


def test_parse_ok(fixture):
    out = parse_networkquality_output(fixture("networkquality_ok.txt"))
    assert out["dl_mbps"] == 285.456
    assert out["ul_mbps"] == 42.123
    assert out["rpm"] == 920
    assert out["rpm_classification"] == "Medium"
    assert out["idle_latency_ms"] == 12.345
    assert out["loaded_latency_ms"] == 38.123
    assert out["ok"] is True


def test_parse_missing_loaded(fixture):
    out = parse_networkquality_output(fixture("networkquality_missing_loaded.txt"))
    assert out["dl_mbps"] == 95.200
    assert out["ul_mbps"] == 12.500
    assert out["rpm"] == 180
    assert out["idle_latency_ms"] is None
    assert out["loaded_latency_ms"] is None
    assert out["ok"] is True
