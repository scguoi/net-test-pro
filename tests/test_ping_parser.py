from nettest.probes.ping import parse_ping_output


def test_parse_ok(fixture):
    out = parse_ping_output(fixture("ping_ok.txt"))
    assert out["resolved_ip"] == "39.156.66.10"
    assert out["packets_sent"] == 5
    assert out["packets_received"] == 5
    assert out["loss_pct"] == 0.0
    assert out["rtt_min"] == 8.123
    assert out["rtt_avg"] == 8.523
    assert out["rtt_max"] == 9.012
    assert out["rtt_stddev"] == 0.345
    assert out["rtt_samples"] == [8.123, 8.456, 8.789, 9.012, 8.234]


def test_parse_full_loss(fixture):
    out = parse_ping_output(fixture("ping_full_loss.txt"))
    assert out["resolved_ip"] == "203.0.113.99"
    assert out["packets_sent"] == 3
    assert out["packets_received"] == 0
    assert out["loss_pct"] == 100.0
    assert out["rtt_avg"] is None
    assert out["rtt_samples"] == []


def test_parse_partial_loss(fixture):
    out = parse_ping_output(fixture("ping_partial_loss.txt"))
    assert out["packets_sent"] == 5
    assert out["packets_received"] == 3
    assert out["loss_pct"] == 40.0
    assert out["rtt_avg"] == 145.456
    assert len(out["rtt_samples"]) == 3
