from nettest.diagnostic import diagnose
from nettest.types import Rating


def _make_summary(domestic=Rating.EXCELLENT, intl=Rating.EXCELLENT,
                  dns=Rating.EXCELLENT, bandwidth=Rating.EXCELLENT,
                  google_loss=0.0, cloudflare_loss=0.0, dns_inconsistent=False):
    return {
        "domestic_rating": domestic,
        "intl_rating": intl,
        "dns_rating": dns,
        "bandwidth_rating": bandwidth,
        "google_loss_pct": google_loss,
        "cloudflare_loss_pct": cloudflare_loss,
        "dns_inconsistent": dns_inconsistent,
    }


def test_all_excellent_says_good():
    msg = diagnose(_make_summary())
    assert "良好" in msg or "正常" in msg


def test_targeted_google_interference_detected():
    s = _make_summary(intl=Rating.POOR, google_loss=5.0, cloudflare_loss=0.0)
    msg = diagnose(s)
    assert "google" in msg.lower() or "Google" in msg
    assert "干扰" in msg or "代理" in msg


def test_dns_inconsistent_warning():
    s = _make_summary(dns_inconsistent=True)
    msg = diagnose(s)
    assert "DNS" in msg


def test_bandwidth_poor_calls_it_out():
    s = _make_summary(bandwidth=Rating.POOR)
    msg = diagnose(s)
    assert "带宽" in msg
