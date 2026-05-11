from nettest.probes.dns import parse_dig_output


def test_parse_ok(fixture):
    out = parse_dig_output(fixture("dig_ok.txt"))
    assert out["server"] == "8.8.8.8"
    assert out["query_time_ms"] == 35
    assert out["ips"] == ["140.82.121.4"]
    assert out["ok"] is True


def test_parse_timeout(fixture):
    out = parse_dig_output(fixture("dig_timeout.txt"))
    assert out["ok"] is False
    assert out["ips"] == []
    assert out["query_time_ms"] is None
