from nettest.probes.traceroute import parse_traceroute_output


def test_parse_ok(fixture):
    out = parse_traceroute_output(fixture("traceroute_ok.txt"))
    assert out["target"] == "baidu.com"
    assert out["resolved_ip"] == "39.156.66.10"
    assert len(out["hops"]) == 5
    assert out["hops"][0] == {"hop": 1, "ip": "192.168.1.1", "rtt_ms": 2.123, "lost": False}
    assert out["hops"][-1]["ip"] == "39.156.66.10"
    assert out["reached"] is True


def test_parse_with_loss(fixture):
    out = parse_traceroute_output(fixture("traceroute_with_loss.txt"))
    assert out["reached"] is True
    lost_hops = [h for h in out["hops"] if h["lost"]]
    assert len(lost_hops) == 2
    assert lost_hops[0]["hop"] == 3


def test_parse_unreached(fixture):
    out = parse_traceroute_output(fixture("traceroute_unreached.txt"))
    assert out["reached"] is False
    assert all(h["lost"] for h in out["hops"][-3:])
