import re
import subprocess
import time

from nettest.types import ProbeResult

_RESOLVED_RE = re.compile(r"PING \S+ \(([\d.]+)\)")
_SAMPLE_RE = re.compile(r"icmp_seq=\d+ ttl=\d+ time=([\d.]+) ms")
_STATS_RE = re.compile(
    r"(\d+) packets transmitted, (\d+) packets received, ([\d.]+)% packet loss"
)
_RTT_RE = re.compile(
    r"round-trip min/avg/max/stddev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms"
)


def parse_ping_output(stdout: str) -> dict:
    resolved_ip = None
    m = _RESOLVED_RE.search(stdout)
    if m:
        resolved_ip = m.group(1)

    samples = [float(x) for x in _SAMPLE_RE.findall(stdout)]

    stats = _STATS_RE.search(stdout)
    if not stats:
        return {
            "resolved_ip": resolved_ip,
            "packets_sent": 0,
            "packets_received": 0,
            "loss_pct": 100.0,
            "rtt_min": None,
            "rtt_avg": None,
            "rtt_max": None,
            "rtt_stddev": None,
            "rtt_samples": samples,
        }

    sent = int(stats.group(1))
    received = int(stats.group(2))
    loss_pct = float(stats.group(3))

    rtt = _RTT_RE.search(stdout)
    if rtt:
        rtt_min, rtt_avg, rtt_max, rtt_stddev = (
            float(rtt.group(1)),
            float(rtt.group(2)),
            float(rtt.group(3)),
            float(rtt.group(4)),
        )
    else:
        rtt_min = rtt_avg = rtt_max = rtt_stddev = None

    return {
        "resolved_ip": resolved_ip,
        "packets_sent": sent,
        "packets_received": received,
        "loss_pct": loss_pct,
        "rtt_min": rtt_min,
        "rtt_avg": rtt_avg,
        "rtt_max": rtt_max,
        "rtt_stddev": rtt_stddev,
        "rtt_samples": samples,
    }


def run_ping(target: str, *, count: int = 20, interval: float = 0.2, timeout_ms: int = 2000) -> ProbeResult:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            [
                "ping",
                "-c", str(count),
                "-i", str(interval),
                "-W", str(timeout_ms),
                target,
            ],
            capture_output=True,
            text=True,
            timeout=count * interval + 10,
        )
    except subprocess.TimeoutExpired:
        return ProbeResult(target=target, ok=False, error="ping timed out")
    except FileNotFoundError:
        return ProbeResult(target=target, ok=False, error="ping not installed")

    elapsed_ms = (time.monotonic() - started) * 1000
    data = parse_ping_output(proc.stdout)
    ok = data["packets_received"] > 0
    return ProbeResult(
        target=target,
        ok=ok,
        data=data,
        error=None if ok else "no packets received",
        elapsed_ms=elapsed_ms,
    )
