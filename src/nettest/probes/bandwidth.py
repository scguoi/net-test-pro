import re
import subprocess
import time

from nettest.types import ProbeResult

# macOS phrasing varies across versions ("Uplink"/"Upload", "Downlink"/"Download").
_DL_RE = re.compile(r"Down(?:link|load) capacity:\s*([\d.]+)\s*Mbps")
_UL_RE = re.compile(r"Up(?:link|load) capacity:\s*([\d.]+)\s*Mbps")
# Old format (macOS 12/13): Responsiveness: Medium (920 RPM)
# New format (macOS 15+):   Responsiveness: Low (645.824 milliseconds | 92 RPM)
_RPM_RE = re.compile(
    r"Responsiveness:\s*(\w+)\s*\("
    r"(?:[\d.]+ milli(?:-seconds|seconds) \| )?(\d+)\s*RPM\)"
)
# Old format: Idle Latency: 12.345 milli-seconds | Loaded Latency: 38.123 milli-seconds
# New format: Idle Latency: 169.560 milliseconds | 353 RPM
_IDLE_RE = re.compile(r"Idle Latency:\s*([\d.]+)\s*milli(?:-seconds|seconds)")
_LOADED_RE = re.compile(r"Loaded Latency:\s*([\d.]+)\s*milli(?:-seconds|seconds)")


def parse_networkquality_output(stdout: str) -> dict:
    dl = _DL_RE.search(stdout)
    ul = _UL_RE.search(stdout)
    rpm = _RPM_RE.search(stdout)
    idle = _IDLE_RE.search(stdout)
    loaded = _LOADED_RE.search(stdout)
    data = {
        "dl_mbps": float(dl.group(1)) if dl else None,
        "ul_mbps": float(ul.group(1)) if ul else None,
        "rpm": int(rpm.group(2)) if rpm else None,
        "rpm_classification": rpm.group(1) if rpm else None,
        "idle_latency_ms": float(idle.group(1)) if idle else None,
        "loaded_latency_ms": float(loaded.group(1)) if loaded else None,
    }
    data["ok"] = data["dl_mbps"] is not None and data["ul_mbps"] is not None
    return data


def run_networkquality(*, timeout_s: int = 60) -> ProbeResult:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            ["networkQuality", "-v"],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return ProbeResult(target="networkQuality", ok=False, error="bandwidth test timed out")
    except FileNotFoundError:
        return ProbeResult(target="networkQuality", ok=False, error="requires macOS 12.3+")

    elapsed_ms = (time.monotonic() - started) * 1000
    data = parse_networkquality_output(proc.stdout)
    return ProbeResult(
        target="networkQuality",
        ok=data["ok"],
        data=data,
        error=None if data["ok"] else "could not parse bandwidth output",
        elapsed_ms=elapsed_ms,
    )
