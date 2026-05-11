from nettest.rating import (
    Rating,
    rate_latency,
    rate_loss,
    rate_dns_query_ms,
    rate_bandwidth_down_mbps,
    rate_rpm,
)


def test_rate_latency_domestic():
    assert rate_latency(50, region="CN") is Rating.EXCELLENT
    assert rate_latency(150, region="CN") is Rating.OK
    assert rate_latency(300, region="CN") is Rating.POOR
    assert rate_latency(500, region="CN") is Rating.BAD


def test_rate_latency_international():
    assert rate_latency(150, region="INTL") is Rating.EXCELLENT
    assert rate_latency(300, region="INTL") is Rating.OK
    assert rate_latency(500, region="INTL") is Rating.POOR
    assert rate_latency(1000, region="INTL") is Rating.BAD


def test_rate_latency_none_is_bad():
    assert rate_latency(None, region="CN") is Rating.BAD


def test_rate_loss():
    assert rate_loss(0) is Rating.EXCELLENT
    assert rate_loss(0.5) is Rating.OK
    assert rate_loss(3) is Rating.POOR
    assert rate_loss(10) is Rating.BAD
    assert rate_loss(None) is Rating.BAD


def test_rate_dns():
    assert rate_dns_query_ms(20) is Rating.EXCELLENT
    assert rate_dns_query_ms(100) is Rating.OK
    assert rate_dns_query_ms(300) is Rating.POOR
    assert rate_dns_query_ms(None) is Rating.BAD


def test_rate_bandwidth():
    assert rate_bandwidth_down_mbps(200) is Rating.EXCELLENT
    assert rate_bandwidth_down_mbps(50) is Rating.OK
    assert rate_bandwidth_down_mbps(10) is Rating.POOR
    assert rate_bandwidth_down_mbps(2) is Rating.BAD


def test_rate_rpm():
    assert rate_rpm(800) is Rating.EXCELLENT
    assert rate_rpm(300) is Rating.OK
    assert rate_rpm(150) is Rating.POOR
    assert rate_rpm(50) is Rating.BAD


def test_worst_rating_helper():
    from nettest.rating import worst
    assert worst([Rating.EXCELLENT, Rating.OK, Rating.POOR]) is Rating.POOR
    assert worst([Rating.EXCELLENT, Rating.EXCELLENT]) is Rating.EXCELLENT
    assert worst([Rating.SKIPPED, Rating.EXCELLENT]) is Rating.EXCELLENT
