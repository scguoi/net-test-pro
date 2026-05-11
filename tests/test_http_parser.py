import pytest
from nettest.probes.http import parse_curl_output


def test_parse_ok(fixture):
    out = parse_curl_output(fixture("curl_ok.txt"))
    assert out["http_code"] == 200
    assert out["dns_ms"] == pytest.approx(12.345)
    # connect_ms = (0.045678 - 0.012345) * 1000
    assert out["connect_ms"] == pytest.approx(33.333, abs=0.01)
    assert out["tls_ms"] == pytest.approx(33.223, abs=0.01)
    assert out["ttfb_ms"] == pytest.approx(23.444, abs=0.01)
    assert out["total_ms"] == pytest.approx(123.456)
    assert out["ok"] is True


def test_parse_failure_marker():
    # When curl times out and our wrapper writes a sentinel, parser must report failure.
    out = parse_curl_output("")
    assert out["ok"] is False
