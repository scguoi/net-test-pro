import re
import subprocess
import time

from nettest.types import ProbeResult

_HEADER_RE = re.compile(r"traceroute to (\S+) \(([\d.]+)\)")
_HOP_LINE_RE = re.compile(r"^\s*(\d+)\s+(.*)$")
_PROBE_RE = re.compile(r"([\d.]+)\s+([\d.]+) ms")


def parse_traceroute_output(stdout: str) -> dict:
    target: str | None = None
    resolved_ip: str | None = None
    hops: list[dict] = []

    for line in stdout.splitlines():
        h = _HEADER_RE.search(line)
        if h:
            target = h.group(1)
            resolved_ip = h.group(2)
            continue
        m = _HOP_LINE_RE.match(line)
        if not m:
            continue
        hop_num = int(m.group(1))
        rest = m.group(2).strip()
        if rest.startswith("*"):
            hops.append({"hop": hop_num, "ip": None, "rtt_ms": None, "lost": True})
            continue
        probe = _PROBE_RE.search(rest)
        if probe:
            hops.append({
                "hop": hop_num,
                "ip": probe.group(1),
                "rtt_ms": float(probe.group(2)),
                "lost": False,
            })
        else:
            hops.append({"hop": hop_num, "ip": None, "rtt_ms": None, "lost": True})

    reached = bool(hops) and hops[-1]["ip"] == resolved_ip and resolved_ip is not None
    return {
        "target": target,
        "resolved_ip": resolved_ip,
        "hops": hops,
        "reached": reached,
    }


def run_traceroute(target: str, *, max_hops: int = 20, wait_s: int = 2) -> ProbeResult:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            [
                "traceroute",
                "-n",
                "-w", str(wait_s),
                "-q", "1",
                "-m", str(max_hops),
                target,
            ],
            capture_output=True,
            text=True,
            timeout=max_hops * wait_s + 10,
        )
    except subprocess.TimeoutExpired:
        return ProbeResult(target=target, ok=False, error="traceroute timed out")
    except FileNotFoundError:
        return ProbeResult(target=target, ok=False, error="traceroute not installed")

    elapsed_ms = (time.monotonic() - started) * 1000
    data = parse_traceroute_output(proc.stdout)
    return ProbeResult(
        target=target,
        ok=bool(data["hops"]),
        data=data,
        error=None if data["hops"] else "no hops parsed",
        elapsed_ms=elapsed_ms,
    )
