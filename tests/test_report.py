from io import StringIO

from rich.console import Console

from nettest.report import render_report
from nettest.types import ProbeResult, Rating, Verdict


def _sample_payload():
    return {
        "timestamp": "2026-05-11 15:23:01",
        "env": {
            "wifi": {"ssid": "MyHome-5G", "signal_dbm": -52, "channel": "36"},
            "interface": "en0",
            "local_ip": "192.168.1.42",
            "public_ip": "223.104.99.99",
            "location": "Beijing, CN",
            "org": "China Mobile",
            "system_dns": ["192.168.1.1"],
        },
        "summary_verdicts": {
            "domestic": Verdict(Rating.EXCELLENT, "国内网络：优秀", "平均延迟 12ms  丢包 0%"),
            "intl": Verdict(Rating.OK, "国际网络：一般", "平均延迟 168ms  丢包 2%"),
            "dns": Verdict(Rating.EXCELLENT, "DNS：正常", "系统 DNS 35ms"),
            "bandwidth": Verdict(Rating.EXCELLENT, "带宽：良好", "↓ 285 Mbps  ↑ 42 Mbps"),
        },
        "diagnostic": "当前 WiFi 各维度均良好，访问正常。",
        "latency_results": [
            ProbeResult("baidu.com", True, {"rtt_avg": 8.2, "rtt_stddev": 0.4, "loss_pct": 0.0}),
            ProbeResult("google.com", True, {"rtt_avg": 185.4, "rtt_stddev": 22.5, "loss_pct": 5.0}),
        ],
        "dns_results": [
            ProbeResult("223.5.5.5", True, {"query_time_ms": 18, "ips": ["140.82.121.4"]}),
            ProbeResult("8.8.8.8", True, {"query_time_ms": 152, "ips": ["140.82.121.4"]}),
        ],
        "traceroute_results": [
            ProbeResult("baidu.com", True, {"hops": [{"hop": 1, "rtt_ms": 2.1, "ip": "1.1", "lost": False}, {"hop": 5, "rtt_ms": 8.2, "ip": "x", "lost": False}], "reached": True}),
        ],
        "http_results": [
            ProbeResult("baidu.com", True, {"dns_ms": 12, "connect_ms": 9, "tls_ms": 45, "ttfb_ms": 85, "total_ms": 108, "http_code": 200}),
        ],
        "bandwidth_result": ProbeResult("networkQuality", True, {
            "dl_mbps": 285.456, "ul_mbps": 42.123, "rpm": 920,
            "idle_latency_ms": 12.0, "loaded_latency_ms": 38.0,
        }),
        "elapsed_s": 68,
        "cache_path": "/tmp/nettest/2026-05-11-152301.json",
    }


def test_renders_all_sections():
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    render_report(_sample_payload(), console=console)
    out = buf.getvalue()
    assert "WiFi 网络体检报告" in out
    assert "MyHome-5G" in out
    assert "国内网络" in out
    assert "国际网络" in out
    assert "baidu.com" in out
    assert "google.com" in out
    assert "285" in out  # dl_mbps appears
    assert "正常" in out  # diagnostic


def test_verbose_prints_full_hops():
    from io import StringIO
    from rich.console import Console
    payload = _sample_payload()
    payload["traceroute_results"][0].data["hops"] = [
        {"hop": 1, "ip": "192.168.1.1", "rtt_ms": 2.0, "lost": False},
        {"hop": 2, "ip": None, "rtt_ms": None, "lost": True},
        {"hop": 3, "ip": "8.8.8.8", "rtt_ms": 15.5, "lost": False},
    ]
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    render_report(payload, console=console, verbose=True)
    out = buf.getvalue()
    assert "192.168.1.1" in out
    assert "8.8.8.8" in out
    assert "15.5" in out

    # default (non-verbose) should NOT print the per-hop list
    buf2 = StringIO()
    console2 = Console(file=buf2, force_terminal=False, width=120)
    render_report(payload, console=console2, verbose=False)
    out2 = buf2.getvalue()
    assert "192.168.1.1" not in out2 or "完整路径" not in out2


def test_skipped_bandwidth_renders_skipped_marker():
    payload = _sample_payload()
    payload["bandwidth_result"] = ProbeResult("networkQuality", False, error="requires macOS 12.3+")
    payload["summary_verdicts"]["bandwidth"] = Verdict(Rating.SKIPPED, "带宽：跳过", "需要 macOS 12.3+")
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    render_report(payload, console=console)
    out = buf.getvalue()
    assert "跳过" in out
