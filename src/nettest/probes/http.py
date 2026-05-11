import subprocess
import time

from nettest.types import ProbeResult


def parse_curl_output(stdout: str) -> dict:
    fields = stdout.strip().split()
    if len(fields) != 6:
        return {"ok": False}
    try:
        namelookup = float(fields[0])
        connect = float(fields[1])
        appconnect = float(fields[2])
        starttransfer = float(fields[3])
        total = float(fields[4])
        code = int(fields[5])
    except ValueError:
        return {"ok": False}

    def _delta(later: float, earlier: float) -> float | None:
        if later <= 0 or earlier <= 0:
            return None
        return (later - earlier) * 1000

    return {
        "dns_ms": namelookup * 1000 if namelookup > 0 else None,
        "connect_ms": _delta(connect, namelookup),
        "tls_ms": _delta(appconnect, connect),
        "ttfb_ms": _delta(starttransfer, appconnect),
        "total_ms": total * 1000,
        "http_code": code,
        "ok": 200 <= code < 400,
    }


_W_FMT = "%{time_namelookup} %{time_connect} %{time_appconnect} %{time_starttransfer} %{time_total} %{http_code}\n"


def run_curl(target: str, *, timeout_s: int = 10) -> ProbeResult:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            [
                "curl",
                "-sS",
                "-o", "/dev/null",
                "-m", str(timeout_s),
                "-w", _W_FMT,
                f"https://{target}/",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_s + 5,
        )
    except subprocess.TimeoutExpired:
        return ProbeResult(target=target, ok=False, error="curl timed out")
    except FileNotFoundError:
        return ProbeResult(target=target, ok=False, error="curl not installed")

    elapsed_ms = (time.monotonic() - started) * 1000
    data = parse_curl_output(proc.stdout)
    return ProbeResult(
        target=target,
        ok=data["ok"],
        data=data,
        error=None if data["ok"] else (proc.stderr.strip() or "request failed"),
        elapsed_ms=elapsed_ms,
    )
