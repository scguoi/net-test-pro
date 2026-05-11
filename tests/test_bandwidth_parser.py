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


def test_parse_macos26_verbose_format(fixture):
    """macOS 26 (Tahoe) uses a different format:
    SUMMARY: Responsiveness: Low (645.824 milliseconds | 92 RPM)
    SUMMARY: Idle Latency: 169.560 milliseconds | 353 RPM
    """
    out = parse_networkquality_output(fixture("networkquality_macos26.txt"))
    assert out["dl_mbps"] == 131.273
    assert out["ul_mbps"] == 28.006
    assert out["rpm"] == 92
    assert out["rpm_classification"] == "Low"
    assert out["idle_latency_ms"] == 169.560
    assert out["loaded_latency_ms"] is None
    assert out["ok"] is True
