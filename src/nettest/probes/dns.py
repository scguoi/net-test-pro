import re
import subprocess
import time

from nettest.types import ProbeResult

_QTIME_RE = re.compile(r";; Query time: (\d+) msec")
_SERVER_RE = re.compile(r";; SERVER: ([^#\s]+)")
_ANSWER_A_RE = re.compile(r"^\S+\.\s+\d+\s+IN\s+A\s+([\d.]+)$", re.MULTILINE)


def parse_dig_output(stdout: str) -> dict:
    qtime_m = _QTIME_RE.search(stdout)
    query_time_ms = int(qtime_m.group(1)) if qtime_m else None

    server_m = _SERVER_RE.search(stdout)
    server = server_m.group(1) if server_m else None

    ips = _ANSWER_A_RE.findall(stdout)
    ok = bool(ips) and query_time_ms is not None
    return {
        "server": server,
        "query_time_ms": query_time_ms,
        "ips": ips,
        "ok": ok,
    }


def run_dig(dns_server: str, domain: str, *, timeout_s: int = 3) -> ProbeResult:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            [
                "dig",
                f"@{dns_server}",
                domain,
                f"+time={timeout_s}",
                "+tries=1",
                "+stats",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_s + 5,
        )
    except subprocess.TimeoutExpired:
        return ProbeResult(target=dns_server, ok=False, error="dig timed out")
    except FileNotFoundError:
        return ProbeResult(target=dns_server, ok=False, error="dig not installed")

    elapsed_ms = (time.monotonic() - started) * 1000
    data = parse_dig_output(proc.stdout)
    return ProbeResult(
        target=dns_server,
        ok=data["ok"],
        data=data,
        error=None if data["ok"] else "no answer or timeout",
        elapsed_ms=elapsed_ms,
    )
