from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from nettest.types import Rating, Verdict


def render_report(payload: dict, *, console: Console | None = None, verbose: bool = False) -> None:
    console = console or Console()
    _render_header(payload, console)
    _render_summary(payload, console)
    _render_latency(payload, console)
    _render_dns(payload, console)
    _render_traceroute(payload, console, verbose=verbose)
    _render_http(payload, console)
    _render_bandwidth(payload, console)
    _render_footer(payload, console)


def _render_header(p: dict, c: Console) -> None:
    env = p["env"]
    wifi = env.get("wifi") or {}
    signal = wifi.get("signal_dbm")
    signal_str = f"{signal}dBm" if signal is not None else "—"
    text = (
        f"时间：{p.get('timestamp', '—')}\n"
        f"WiFi：{wifi.get('ssid') or '—'} ({signal_str}, channel {wifi.get('channel') or '—'})\n"
        f"本机 IP：{env.get('local_ip') or '—'}  →  公网 IP：{env.get('public_ip') or '—'} ({env.get('location') or '—'})\n"
        f"系统 DNS：{', '.join(env.get('system_dns') or ['—'])}"
    )
    c.print(Panel(text, title="WiFi 网络体检报告", expand=False))


def _render_summary(p: dict, c: Console) -> None:
    c.rule("总评")
    for key in ("domestic", "intl", "dns", "bandwidth"):
        v: Verdict | None = p["summary_verdicts"].get(key)
        if not v:
            continue
        c.print(f"{v.rating.value} {v.headline}     {v.detail}")
    c.print()
    c.print(f"诊断：{p.get('diagnostic', '')}")


def _render_latency(p: dict, c: Console) -> None:
    c.rule("① 延迟 / 丢包 (TLS 443)")
    t = Table(show_header=True, header_style="bold")
    t.add_column("目标")
    t.add_column("延迟(ms)", justify="right")
    t.add_column("抖动", justify="right")
    t.add_column("丢包", justify="right")
    t.add_column("评价")
    for r in p["latency_results"]:
        d = r.data
        avg = d.get("rtt_avg")
        jit = d.get("rtt_stddev")
        loss = d.get("loss_pct")
        rating = _quick_latency_rating(avg, loss, r.target)
        t.add_row(
            r.target,
            f"{avg:.1f}" if avg is not None else "—",
            f"{jit:.1f}" if jit is not None else "—",
            f"{loss:.1f}%" if loss is not None else "—",
            rating,
        )
    c.print(t)


def _render_dns(p: dict, c: Console) -> None:
    c.rule("② DNS 解析")
    t = Table(show_header=True, header_style="bold")
    t.add_column("DNS 服务器")
    t.add_column("耗时(ms)", justify="right")
    t.add_column("返回 IP")
    t.add_column("状态")
    for r in p["dns_results"]:
        d = r.data
        t.add_row(
            r.target,
            f"{d.get('query_time_ms')}" if d.get("query_time_ms") is not None else "—",
            ", ".join(d.get("ips") or []) or "—",
            "🟢" if r.ok else "🔴",
        )
    c.print(t)


def _render_traceroute(p: dict, c: Console, *, verbose: bool = False) -> None:
    c.rule("③ 路由摘要")
    t = Table(show_header=True, header_style="bold")
    t.add_column("目标")
    t.add_column("跳数", justify="right")
    t.add_column("首跳延迟", justify="right")
    t.add_column("末跳延迟", justify="right")
    t.add_column("到达")
    for r in p["traceroute_results"]:
        hops = r.data.get("hops") or []
        first = next((h["rtt_ms"] for h in hops if h.get("rtt_ms")), None)
        last = next((h["rtt_ms"] for h in reversed(hops) if h.get("rtt_ms")), None)
        t.add_row(
            r.target,
            str(len(hops)),
            f"{first:.1f}ms" if first is not None else "—",
            f"{last:.1f}ms" if last is not None else "—",
            "🟢" if r.data.get("reached") else "🟡",
        )
    c.print(t)
    if verbose:
        for r in p["traceroute_results"]:
            hops = r.data.get("hops") or []
            c.print(f"  完整路径 → {r.target}")
            for h in hops:
                hop_num = h.get("hop", "?")
                if h.get("lost"):
                    c.print(f"    {hop_num:>3}  *  (lost)")
                else:
                    ip = h.get("ip") or "?"
                    rtt = h.get("rtt_ms")
                    rtt_str = f"{rtt} ms" if rtt is not None else "?"
                    c.print(f"    {hop_num:>3}  {ip}  {rtt_str}")


def _render_http(p: dict, c: Console) -> None:
    c.rule("④ HTTP 时序")
    t = Table(show_header=True, header_style="bold")
    for col in ("目标", "DNS", "TCP", "TLS", "TTFB", "总时长", "状态"):
        t.add_column(col, justify="right" if col != "目标" else "left")
    for r in p["http_results"]:
        d = r.data
        cells = [r.target]
        for k in ("dns_ms", "connect_ms", "tls_ms", "ttfb_ms", "total_ms"):
            v = d.get(k)
            cells.append(f"{v:.0f}" if v is not None else "—")
        code = d.get("http_code")
        cells.append(f"🟢 {code}" if r.ok else f"🔴 {code or 'fail'}")
        t.add_row(*cells)
    c.print(t)


def _render_bandwidth(p: dict, c: Console) -> None:
    c.rule("⑤ 带宽 (networkQuality)")
    r = p["bandwidth_result"]
    if not r.ok:
        c.print(f"⏭️ 跳过：{r.error or '不可用'}")
        return
    d = r.data
    c.print(f"下行容量：{d.get('dl_mbps', 0):>7.1f} Mbps")
    c.print(f"上行容量：{d.get('ul_mbps', 0):>7.1f} Mbps")
    if d.get("idle_latency_ms") is not None:
        c.print(f"空载延迟：{d['idle_latency_ms']:>7.1f} ms")
    if d.get("loaded_latency_ms") is not None:
        c.print(f"负载延迟：{d['loaded_latency_ms']:>7.1f} ms")
    rpm = d.get("rpm")
    c.print(f"Responsiveness (RPM)：{rpm if rpm is not None else '—'}")


def _render_footer(p: dict, c: Console) -> None:
    c.rule("")
    c.print(f"报告生成耗时：{p.get('elapsed_s', '?')} 秒")
    if p.get("cache_path"):
        c.print(f"完整数据已保存：{p['cache_path']}")


def _quick_latency_rating(avg: float | None, loss: float | None, target: str) -> str:
    if avg is None or loss is None: return "🔴 故障"
    if loss > 5: return "🔴 高丢包"
    if loss > 1: return "🟠 较差"
    if avg < 150: return "🟢 优秀"
    if avg < 400: return "🟡 一般"
    return "🟠 较差"
