import argparse
import json
import sys
import time
from datetime import datetime
from statistics import mean

from rich.console import Console

from nettest import __version__
from nettest.cache import save_snapshot
from nettest.diagnostic import diagnose
from nettest.env import collect_environment
from nettest.probes.bandwidth import run_networkquality
from nettest.probes.dns import run_dig
from nettest.probes.http import run_curl
from nettest.probes.latency import run_tls_latency
from nettest.probes.traceroute import run_traceroute
from nettest.rating import (
    Rating,
    rate_bandwidth_down_mbps,
    rate_dns_query_ms,
    rate_latency,
    rate_loss,
    rate_rpm,
    worst,
)
from nettest.report import render_report
from nettest.runner import run_concurrent
from nettest.targets import DNS_PROBE_DOMAIN, DNS_SERVERS, GENERAL_TARGETS
from nettest.types import Verdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nettest", description="macOS WiFi network health check")
    parser.add_argument("-v", "--verbose", action="store_true", help="print full traceroute and raw data")
    parser.add_argument("-q", "--quiet", action="store_true", help="only print summary + diagnostic")
    parser.add_argument("--no-bandwidth", action="store_true", help="skip bandwidth test (~15s faster)")
    parser.add_argument("--json", action="store_true", help="emit JSON to stdout instead of the human report")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    parser.add_argument("--version", action="version", version=f"nettest {__version__}")
    args = parser.parse_args(argv)

    started = time.monotonic()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    progress = Console(file=sys.stderr, no_color=args.no_color)
    env = collect_environment()
    progress.print("[1/5] 延迟测试 (TLS 443) ...", end="\r")
    latency_results = run_concurrent(
        [t.host for t in GENERAL_TARGETS],
        run_tls_latency,
        max_workers=8,
    )
    progress.print("[2/5] DNS 解析 ...    ", end="\r")
    system_dns_ip = (env.get("system_dns") or [None])[0]
    dns_targets: list[tuple[str, str]] = []
    if system_dns_ip:
        dns_targets.append((system_dns_ip, "系统 DNS"))
    for s in DNS_SERVERS:
        if s.ip != system_dns_ip:
            dns_targets.append((s.ip, s.label))
    dns_results = run_concurrent(
        [ip for ip, _ in dns_targets],
        lambda ip: run_dig(ip, DNS_PROBE_DOMAIN),
        max_workers=5,
    )
    progress.print("[3/5] 路由测试 ...    ", end="\r")
    traceroute_results = run_concurrent(
        [t.host for t in GENERAL_TARGETS],
        run_traceroute,
        max_workers=8,
    )
    progress.print("[4/5] HTTP 时序 ...   ", end="\r")
    http_results = run_concurrent(
        [t.host for t in GENERAL_TARGETS],
        run_curl,
        max_workers=8,
    )
    if args.no_bandwidth:
        from nettest.types import ProbeResult
        bandwidth_result = ProbeResult(target="networkQuality", ok=False, error="skipped via --no-bandwidth")
    else:
        progress.print("[5/5] 带宽测试 ...    ", end="\r")
        bandwidth_result = run_networkquality()
    progress.print("                       ", end="\r")

    summary = _build_summary(
        latency_results=latency_results,
        dns_results=dns_results,
        bandwidth_result=bandwidth_result,
        system_dns_ip=system_dns_ip,
    )
    diagnostic = diagnose(summary)

    elapsed_s = int(time.monotonic() - started)
    snapshot = {
        "timestamp": timestamp,
        "env": env,
        "summary": _ratings_to_str(summary),
        "diagnostic": diagnostic,
        "latency": [_pr_to_dict(r) for r in latency_results],
        "dns": [_pr_to_dict(r) for r in dns_results],
        "traceroute": [_pr_to_dict(r) for r in traceroute_results],
        "http": [_pr_to_dict(r) for r in http_results],
        "bandwidth": _pr_to_dict(bandwidth_result),
        "elapsed_s": elapsed_s,
    }
    cache_path = save_snapshot(snapshot)

    if args.json:
        snapshot["cache_path"] = str(cache_path)
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
        return 0

    verdicts = _build_verdicts(summary, latency_results, dns_results, bandwidth_result)

    payload = {
        "timestamp": timestamp,
        "env": env,
        "summary_verdicts": verdicts,
        "diagnostic": diagnostic,
        "latency_results": latency_results,
        "dns_results": dns_results,
        "traceroute_results": traceroute_results,
        "http_results": http_results,
        "bandwidth_result": bandwidth_result,
        "elapsed_s": elapsed_s,
        "cache_path": str(cache_path),
    }

    out_console = Console(no_color=args.no_color, force_terminal=not args.no_color)
    if args.quiet:
        _render_quiet(payload, out_console)
    else:
        render_report(payload, console=out_console, verbose=args.verbose)
    return 0


def _build_summary(*, latency_results, dns_results, bandwidth_result, system_dns_ip: str | None = None) -> dict:
    domestic_ping = [r for r in latency_results if r.target in {"baidu.com", "taobao.com", "qq.com", "223.5.5.5"} and r.ok]
    intl_ping = [r for r in latency_results if r.target in {"google.com", "github.com", "cloudflare.com", "1.1.1.1"} and r.ok]

    def avg_or_none(values):
        clean = [v for v in values if v is not None]
        return mean(clean) if clean else None

    dom_avg = avg_or_none([r.data.get("rtt_avg") for r in domestic_ping])
    dom_loss = avg_or_none([r.data.get("loss_pct") for r in domestic_ping])
    intl_avg = avg_or_none([r.data.get("rtt_avg") for r in intl_ping])
    intl_loss = avg_or_none([r.data.get("loss_pct") for r in intl_ping])

    google_loss = next((r.data.get("loss_pct") for r in latency_results if r.target == "google.com"), None)
    cloudflare_loss = next((r.data.get("loss_pct") for r in latency_results if r.target == "cloudflare.com"), None)

    domestic_rating = worst([
        rate_latency(dom_avg, region="CN"),
        rate_loss(dom_loss),
    ])
    intl_rating = worst([
        rate_latency(intl_avg, region="INTL"),
        rate_loss(intl_loss),
    ])

    dns_rating = worst([rate_dns_query_ms(r.data.get("query_time_ms")) for r in dns_results if r.ok] or [Rating.BAD])
    dns_ip_sets = [tuple(sorted(r.data.get("ips") or [])) for r in dns_results if r.ok and r.data.get("ips")]
    dns_inconsistent = len(set(dns_ip_sets)) > 1

    if bandwidth_result.ok:
        bw_ratings = [rate_bandwidth_down_mbps(bandwidth_result.data.get("dl_mbps"))]
        rpm = bandwidth_result.data.get("rpm")
        if rpm is not None:
            bw_ratings.append(rate_rpm(rpm))
        bw_rating = worst(bw_ratings)
    else:
        bw_rating = Rating.SKIPPED

    return {
        "domestic_rating": domestic_rating,
        "intl_rating": intl_rating,
        "dns_rating": dns_rating,
        "bandwidth_rating": bw_rating,
        "dom_avg_ms": dom_avg,
        "dom_loss_pct": dom_loss,
        "intl_avg_ms": intl_avg,
        "intl_loss_pct": intl_loss,
        "google_loss_pct": google_loss,
        "cloudflare_loss_pct": cloudflare_loss,
        "dns_inconsistent": dns_inconsistent,
        "dl_mbps": bandwidth_result.data.get("dl_mbps") if bandwidth_result.ok else None,
        "ul_mbps": bandwidth_result.data.get("ul_mbps") if bandwidth_result.ok else None,
        "system_dns_ms": next(
            (r.data.get("query_time_ms") for r in dns_results if r.ok and r.target == system_dns_ip),
            None,
        ),
    }


def _build_verdicts(summary, latency_results, dns_results, bandwidth_result):
    def fmt_ms(v): return f"{v:.0f}ms" if v is not None else "—"
    def fmt_loss(v): return f"{v:.1f}%" if v is not None else "—"

    return {
        "domestic": Verdict(
            summary["domestic_rating"],
            f"国内网络：{_label(summary['domestic_rating'])}",
            f"平均延迟 {fmt_ms(summary['dom_avg_ms'])}  丢包 {fmt_loss(summary['dom_loss_pct'])}",
        ),
        "intl": Verdict(
            summary["intl_rating"],
            f"国际网络：{_label(summary['intl_rating'])}",
            f"平均延迟 {fmt_ms(summary['intl_avg_ms'])}  丢包 {fmt_loss(summary['intl_loss_pct'])}",
        ),
        "dns": Verdict(
            summary["dns_rating"],
            f"DNS：{_label(summary['dns_rating'])}",
            f"系统 DNS {fmt_ms(summary['system_dns_ms'])}" + ("，存在不一致" if summary["dns_inconsistent"] else "，结果一致"),
        ),
        "bandwidth": Verdict(
            summary["bandwidth_rating"],
            f"带宽：{_label(summary['bandwidth_rating'])}",
            (
                f"↓ {summary['dl_mbps']:.0f} Mbps   ↑ {summary['ul_mbps']:.0f} Mbps"
                if summary["bandwidth_rating"] is not Rating.SKIPPED
                else "已跳过"
            ),
        ),
    }


def _label(r: Rating) -> str:
    return {
        Rating.EXCELLENT: "优秀",
        Rating.OK: "一般",
        Rating.POOR: "较差",
        Rating.BAD: "故障",
        Rating.SKIPPED: "跳过",
    }[r]


def _render_quiet(payload, console):
    for v in payload["summary_verdicts"].values():
        console.print(f"{v.rating.value} {v.headline}  {v.detail}")
    console.print()
    console.print(payload["diagnostic"])


def _pr_to_dict(pr) -> dict:
    return {
        "target": pr.target,
        "ok": pr.ok,
        "data": pr.data,
        "error": pr.error,
        "elapsed_ms": pr.elapsed_ms,
    }


def _ratings_to_str(summary) -> dict:
    out = dict(summary)
    for k in ("domestic_rating", "intl_rating", "dns_rating", "bandwidth_rating"):
        out[k] = summary[k].value
    return out


if __name__ == "__main__":
    sys.exit(main())
