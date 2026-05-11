import socket
import ssl
import statistics
import time

from nettest.types import ProbeResult


def measure_tls_rtt(host: str, port: int, timeout_s: float) -> float | None:
    """Time the TLS handshake to host:port in ms. Returns None on failure.

    TCP connect alone is unreliable through TUN-based proxies (Quantumult X,
    Clash, Surge) — they terminate TCP locally for instant accept. TLS
    handshake forces multiple real round-trips through the proxy/tunnel,
    so it reflects actual end-to-end latency.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection((host, port), timeout=timeout_s) as sock:
            sock.settimeout(timeout_s)
            started = time.monotonic()
            wrapped = ctx.wrap_socket(sock, server_hostname=host)
            rtt = (time.monotonic() - started) * 1000
            try:
                wrapped.close()
            except OSError:
                pass
            return rtt
    except (socket.timeout, TimeoutError, OSError, ssl.SSLError):
        return None


def run_tls_latency(
    target: str,
    *,
    count: int = 5,
    port: int = 443,
    timeout_s: float = 2.0,
) -> ProbeResult:
    started = time.monotonic()
    samples: list[float] = []
    for _ in range(count):
        rtt = measure_tls_rtt(target, port, timeout_s)
        if rtt is not None:
            samples.append(rtt)

    elapsed_ms = (time.monotonic() - started) * 1000
    loss_pct = (1 - len(samples) / count) * 100

    if not samples:
        return ProbeResult(
            target=target,
            ok=False,
            data={
                "port": port,
                "attempts": count,
                "succeeded": 0,
                "loss_pct": loss_pct,
                "rtt_min": None,
                "rtt_avg": None,
                "rtt_max": None,
                "rtt_stddev": None,
                "rtt_samples": [],
            },
            error="all TLS handshakes failed (timeout or error)",
            elapsed_ms=elapsed_ms,
        )

    return ProbeResult(
        target=target,
        ok=True,
        data={
            "port": port,
            "attempts": count,
            "succeeded": len(samples),
            "loss_pct": loss_pct,
            "rtt_min": min(samples),
            "rtt_avg": statistics.mean(samples),
            "rtt_max": max(samples),
            "rtt_stddev": statistics.stdev(samples) if len(samples) > 1 else 0.0,
            "rtt_samples": samples,
        },
        error=None,
        elapsed_ms=elapsed_ms,
    )
