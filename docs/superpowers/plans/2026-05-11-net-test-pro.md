# net-test-pro Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a macOS CLI tool `nettest` that runs a one-shot WiFi network health check (≈1 minute) and prints a structured report covering latency, DNS, routing, HTTP timing, and bandwidth across preset domestic and international targets.

**Architecture:** Python orchestrator that shells out to `ping`/`dig`/`traceroute`/`curl`/`networkQuality`, parses each tool's text output via pure functions, runs probes concurrently within each dimension (serial across dimensions), rates each indicator against fixed thresholds, and renders a `rich`-formatted text report. Parsers are unit-tested against captured fixtures; the orchestrator is covered by a smoke test.

**Tech Stack:** Python 3.11+, `uv` (project & venv management), `rich` (CLI rendering), `pytest` (testing). No third-party network libraries — all network work happens through macOS-bundled CLI tools.

---

## File Structure

```
pyproject.toml                          # uv-managed project metadata + deps
.python-version                          # pin Python version for uv
README.md                                # short usage notes
src/nettest/
├── __init__.py
├── __main__.py                          # enables `python -m nettest`
├── cli.py                               # argparse + top-level orchestration
├── types.py                             # ProbeResult dataclass, Rating enum, Verdict
├── targets.py                           # preset target lists (constants)
├── env.py                               # WiFi/IP/DNS environment collection
├── runner.py                            # concurrent execution of probes per dimension
├── rating.py                            # threshold rules + per-indicator rating
├── diagnostic.py                        # rule-based one-liner verdict
├── report.py                            # rich rendering + JSON serialization
├── cache.py                             # write JSON snapshot to ~/.cache/nettest/
└── probes/
    ├── __init__.py
    ├── ping.py                          # ping subprocess + parser
    ├── dns.py                           # dig subprocess + parser
    ├── traceroute.py                    # traceroute subprocess + parser
    ├── http.py                          # curl subprocess + parser
    └── bandwidth.py                     # networkQuality subprocess + parser
tests/
├── conftest.py                          # shared fixture loader
├── fixtures/
│   ├── ping_ok.txt
│   ├── ping_full_loss.txt
│   ├── ping_partial_loss.txt
│   ├── dig_ok.txt
│   ├── dig_timeout.txt
│   ├── traceroute_ok.txt
│   ├── traceroute_with_loss.txt
│   ├── traceroute_unreached.txt
│   ├── curl_ok.txt
│   ├── networkquality_ok.txt
│   └── networkquality_missing_loaded.txt
├── test_ping_parser.py
├── test_dns_parser.py
├── test_traceroute_parser.py
├── test_http_parser.py
├── test_bandwidth_parser.py
├── test_rating.py
├── test_diagnostic.py
├── test_report.py
└── test_smoke.py
```

## Shared Data Shapes

All probe parsers return plain `dict`s with stable keys (documented in each parser task).
The probe subprocess wrappers wrap those dicts in a `ProbeResult`:

```python
# src/nettest/types.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class Rating(Enum):
    EXCELLENT = "🟢"
    OK = "🟡"
    POOR = "🟠"
    BAD = "🔴"
    SKIPPED = "⏭️"

@dataclass
class ProbeResult:
    target: str
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    elapsed_ms: float | None = None

@dataclass
class Verdict:
    rating: Rating
    headline: str         # "国内网络：优秀"
    detail: str           # "平均延迟 12ms  丢包 0%"
```

---

### Task 1: Project skeleton with uv

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `README.md`
- Modify: `.gitignore` (already exists; verify entries cover uv/pytest)
- Create: `src/nettest/__init__.py`
- Create: `src/nettest/__main__.py`

- [ ] **Step 1: Verify `uv` is installed**

Run: `uv --version`
Expected: prints a version like `uv 0.4.x` or newer. If missing, install via `brew install uv`.

- [ ] **Step 2: Pin Python version**

Create `.python-version` with content:
```
3.11
```

Run: `uv python install 3.11`
Expected: downloads CPython 3.11 if not already present.

- [ ] **Step 3: Write `pyproject.toml`**

Create `pyproject.toml` with:
```toml
[project]
name = "net-test-pro"
version = "0.1.0"
description = "macOS WiFi network health check CLI"
requires-python = ">=3.11"
dependencies = [
    "rich>=13.7",
]

[project.scripts]
nettest = "nettest.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/nettest"]

[dependency-groups]
dev = [
    "pytest>=8.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

- [ ] **Step 4: Create package skeleton**

Create `src/nettest/__init__.py`:
```python
__version__ = "0.1.0"
```

Create `src/nettest/__main__.py`:
```python
from nettest.cli import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Update `.gitignore`**

The existing `.gitignore` already contains uv/pytest/python entries. Verify it lists at minimum: `__pycache__/`, `.venv/`, `.pytest_cache/`, `dist/`, `*.egg-info/`. If anything missing, append it.

- [ ] **Step 6: Write README.md (short)**

Create `README.md`:
```markdown
# net-test-pro

A one-shot macOS WiFi network health check CLI.

## Install

```bash
uv tool install .
```

## Run

```bash
nettest
```

See `docs/superpowers/specs/` for design.
```

- [ ] **Step 7: Sync dependencies**

Run: `uv sync`
Expected: creates `.venv/` and `uv.lock`, installs `rich` and `pytest`.

- [ ] **Step 8: Verify the package imports**

Run: `uv run python -c "import nettest; print(nettest.__version__)"`
Expected: prints `0.1.0`.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml .python-version README.md .gitignore src/nettest/__init__.py src/nettest/__main__.py uv.lock
git commit -m "chore: scaffold uv-managed project"
```

---

### Task 2: Shared types module

**Files:**
- Create: `src/nettest/types.py`
- Create: `tests/test_types.py`

- [ ] **Step 1: Write failing test for `ProbeResult` defaults**

Create `tests/__init__.py` (empty) and `tests/test_types.py`:
```python
from nettest.types import ProbeResult, Rating, Verdict


def test_probe_result_defaults():
    r = ProbeResult(target="baidu.com", ok=True)
    assert r.target == "baidu.com"
    assert r.ok is True
    assert r.data == {}
    assert r.error is None
    assert r.elapsed_ms is None


def test_rating_values():
    assert Rating.EXCELLENT.value == "🟢"
    assert Rating.BAD.value == "🔴"
    assert Rating.SKIPPED.value == "⏭️"


def test_verdict_fields():
    v = Verdict(rating=Rating.EXCELLENT, headline="国内网络：优秀", detail="平均延迟 12ms")
    assert v.rating is Rating.EXCELLENT
    assert "国内网络" in v.headline
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_types.py -v`
Expected: `ModuleNotFoundError: No module named 'nettest.types'`.

- [ ] **Step 3: Implement types**

Create `src/nettest/types.py`:
```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Rating(Enum):
    EXCELLENT = "🟢"
    OK = "🟡"
    POOR = "🟠"
    BAD = "🔴"
    SKIPPED = "⏭️"


@dataclass
class ProbeResult:
    target: str
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    elapsed_ms: float | None = None


@dataclass
class Verdict:
    rating: Rating
    headline: str
    detail: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_types.py -v`
Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/nettest/types.py tests/__init__.py tests/test_types.py
git commit -m "feat: add shared ProbeResult, Rating, Verdict types"
```

---

### Task 3: Targets module

**Files:**
- Create: `src/nettest/targets.py`
- Create: `tests/test_targets.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_targets.py`:
```python
from nettest.targets import GENERAL_TARGETS, DNS_SERVERS, Target


def test_general_targets_have_8_with_4_each_region():
    assert len(GENERAL_TARGETS) == 8
    domestic = [t for t in GENERAL_TARGETS if t.region == "CN"]
    international = [t for t in GENERAL_TARGETS if t.region == "INTL"]
    assert len(domestic) == 4
    assert len(international) == 4


def test_general_targets_include_key_hosts():
    hosts = {t.host for t in GENERAL_TARGETS}
    assert "baidu.com" in hosts
    assert "google.com" in hosts
    assert "1.1.1.1" in hosts
    assert "223.5.5.5" in hosts


def test_dns_servers_include_system_placeholder():
    # System DNS is resolved at runtime; the constant list contains the 4 public ones.
    ips = {s.ip for s in DNS_SERVERS}
    assert ips == {"223.5.5.5", "114.114.114.114", "8.8.8.8", "1.1.1.1"}


def test_target_is_immutable_dataclass():
    t = GENERAL_TARGETS[0]
    # frozen dataclass: mutation raises FrozenInstanceError
    import dataclasses
    try:
        t.host = "x"
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("Target should be frozen")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_targets.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement targets module**

Create `src/nettest/targets.py`:
```python
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Target:
    host: str
    region: Literal["CN", "INTL"]
    kind: Literal["domain", "ip"]
    label: str


@dataclass(frozen=True)
class DnsServer:
    ip: str
    label: str


GENERAL_TARGETS: tuple[Target, ...] = (
    Target("baidu.com",       "CN",   "domain", "百度"),
    Target("taobao.com",      "CN",   "domain", "淘宝"),
    Target("qq.com",          "CN",   "domain", "腾讯"),
    Target("223.5.5.5",       "CN",   "ip",     "阿里 DNS (IP)"),
    Target("google.com",      "INTL", "domain", "Google"),
    Target("github.com",      "INTL", "domain", "GitHub"),
    Target("cloudflare.com",  "INTL", "domain", "Cloudflare"),
    Target("1.1.1.1",         "INTL", "ip",     "Cloudflare DNS (IP)"),
)

DNS_SERVERS: tuple[DnsServer, ...] = (
    DnsServer("223.5.5.5",       "阿里"),
    DnsServer("114.114.114.114", "114"),
    DnsServer("8.8.8.8",         "Google"),
    DnsServer("1.1.1.1",         "Cloudflare"),
)

DNS_PROBE_DOMAIN = "github.com"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_targets.py -v`
Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/nettest/targets.py tests/test_targets.py
git commit -m "feat: add preset target and DNS server lists"
```

---

### Task 4: ping probe (parser + subprocess wrapper)

**Files:**
- Create: `tests/fixtures/ping_ok.txt`
- Create: `tests/fixtures/ping_full_loss.txt`
- Create: `tests/fixtures/ping_partial_loss.txt`
- Create: `tests/conftest.py`
- Create: `src/nettest/probes/__init__.py`
- Create: `src/nettest/probes/ping.py`
- Create: `tests/test_ping_parser.py`

- [ ] **Step 1: Create fixture files**

Create `tests/fixtures/ping_ok.txt`:
```
PING baidu.com (39.156.66.10): 56 data bytes
64 bytes from 39.156.66.10: icmp_seq=0 ttl=53 time=8.123 ms
64 bytes from 39.156.66.10: icmp_seq=1 ttl=53 time=8.456 ms
64 bytes from 39.156.66.10: icmp_seq=2 ttl=53 time=8.789 ms
64 bytes from 39.156.66.10: icmp_seq=3 ttl=53 time=9.012 ms
64 bytes from 39.156.66.10: icmp_seq=4 ttl=53 time=8.234 ms

--- baidu.com ping statistics ---
5 packets transmitted, 5 packets received, 0.0% packet loss
round-trip min/avg/max/stddev = 8.123/8.523/9.012/0.345 ms
```

Create `tests/fixtures/ping_full_loss.txt`:
```
PING somehost.invalid (203.0.113.99): 56 data bytes
Request timeout for icmp_seq 0
Request timeout for icmp_seq 1
Request timeout for icmp_seq 2

--- somehost.invalid ping statistics ---
3 packets transmitted, 0 packets received, 100.0% packet loss
```

Create `tests/fixtures/ping_partial_loss.txt`:
```
PING flaky.example (198.51.100.42): 56 data bytes
64 bytes from 198.51.100.42: icmp_seq=0 ttl=58 time=120.123 ms
Request timeout for icmp_seq 1
64 bytes from 198.51.100.42: icmp_seq=2 ttl=58 time=135.456 ms
64 bytes from 198.51.100.42: icmp_seq=3 ttl=58 time=180.789 ms
Request timeout for icmp_seq 4

--- flaky.example ping statistics ---
5 packets transmitted, 3 packets received, 40.0% packet loss
round-trip min/avg/max/stddev = 120.123/145.456/180.789/25.678 ms
```

- [ ] **Step 2: Create fixture loader in conftest**

Create `tests/conftest.py`:
```python
from pathlib import Path
import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture():
    def _load(name: str) -> str:
        return (FIXTURE_DIR / name).read_text()
    return _load
```

- [ ] **Step 3: Write failing parser tests**

Create `src/nettest/probes/__init__.py` (empty).

Create `tests/test_ping_parser.py`:
```python
from nettest.probes.ping import parse_ping_output


def test_parse_ok(fixture):
    out = parse_ping_output(fixture("ping_ok.txt"))
    assert out["resolved_ip"] == "39.156.66.10"
    assert out["packets_sent"] == 5
    assert out["packets_received"] == 5
    assert out["loss_pct"] == 0.0
    assert out["rtt_min"] == 8.123
    assert out["rtt_avg"] == 8.523
    assert out["rtt_max"] == 9.012
    assert out["rtt_stddev"] == 0.345
    assert out["rtt_samples"] == [8.123, 8.456, 8.789, 9.012, 8.234]


def test_parse_full_loss(fixture):
    out = parse_ping_output(fixture("ping_full_loss.txt"))
    assert out["resolved_ip"] == "203.0.113.99"
    assert out["packets_sent"] == 3
    assert out["packets_received"] == 0
    assert out["loss_pct"] == 100.0
    assert out["rtt_avg"] is None
    assert out["rtt_samples"] == []


def test_parse_partial_loss(fixture):
    out = parse_ping_output(fixture("ping_partial_loss.txt"))
    assert out["packets_sent"] == 5
    assert out["packets_received"] == 3
    assert out["loss_pct"] == 40.0
    assert out["rtt_avg"] == 145.456
    assert len(out["rtt_samples"]) == 3
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run pytest tests/test_ping_parser.py -v`
Expected: `ModuleNotFoundError: No module named 'nettest.probes.ping'`.

- [ ] **Step 5: Implement the parser + subprocess wrapper**

Create `src/nettest/probes/ping.py`:
```python
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
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_ping_parser.py -v`
Expected: 3 tests PASS.

- [ ] **Step 7: Smoke test the subprocess wrapper against localhost**

Run: `uv run python -c "from nettest.probes.ping import run_ping; r = run_ping('127.0.0.1', count=3); print(r)"`
Expected: prints a `ProbeResult` with `ok=True` and `rtt_avg` populated. (Localhost ping always works on macOS.)

- [ ] **Step 8: Commit**

```bash
git add tests/conftest.py tests/fixtures/ping_ok.txt tests/fixtures/ping_full_loss.txt tests/fixtures/ping_partial_loss.txt tests/test_ping_parser.py src/nettest/probes/__init__.py src/nettest/probes/ping.py
git commit -m "feat: add ping probe with parser and tests"
```

---

### Task 5: dig (DNS) probe

**Files:**
- Create: `tests/fixtures/dig_ok.txt`
- Create: `tests/fixtures/dig_timeout.txt`
- Create: `src/nettest/probes/dns.py`
- Create: `tests/test_dns_parser.py`

- [ ] **Step 1: Create fixture files**

Create `tests/fixtures/dig_ok.txt`:
```

; <<>> DiG 9.10.6 <<>> @8.8.8.8 github.com +time=3 +tries=1 +stats
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 41927
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 512
;; QUESTION SECTION:
;github.com.			IN	A

;; ANSWER SECTION:
github.com.		60	IN	A	140.82.121.4

;; Query time: 35 msec
;; SERVER: 8.8.8.8#53(8.8.8.8)
;; WHEN: Sun May 11 15:23:01 CST 2026
;; MSG SIZE  rcvd: 55
```

Create `tests/fixtures/dig_timeout.txt`:
```

; <<>> DiG 9.10.6 <<>> @203.0.113.99 github.com +time=3 +tries=1 +stats
; (1 server found)
;; global options: +cmd
;; connection timed out; no servers could be reached
```

- [ ] **Step 2: Write failing parser tests**

Create `tests/test_dns_parser.py`:
```python
from nettest.probes.dns import parse_dig_output


def test_parse_ok(fixture):
    out = parse_dig_output(fixture("dig_ok.txt"))
    assert out["server"] == "8.8.8.8"
    assert out["query_time_ms"] == 35
    assert out["ips"] == ["140.82.121.4"]
    assert out["ok"] is True


def test_parse_timeout(fixture):
    out = parse_dig_output(fixture("dig_timeout.txt"))
    assert out["ok"] is False
    assert out["ips"] == []
    assert out["query_time_ms"] is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_dns_parser.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 4: Implement parser + wrapper**

Create `src/nettest/probes/dns.py`:
```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_dns_parser.py -v`
Expected: 2 tests PASS.

- [ ] **Step 6: Smoke test against 1.1.1.1**

Run: `uv run python -c "from nettest.probes.dns import run_dig; print(run_dig('1.1.1.1', 'github.com'))"`
Expected: `ProbeResult` with `ok=True` and `query_time_ms` populated.

- [ ] **Step 7: Commit**

```bash
git add tests/fixtures/dig_ok.txt tests/fixtures/dig_timeout.txt tests/test_dns_parser.py src/nettest/probes/dns.py
git commit -m "feat: add dig DNS probe with parser and tests"
```

---

### Task 6: traceroute probe

**Files:**
- Create: `tests/fixtures/traceroute_ok.txt`
- Create: `tests/fixtures/traceroute_with_loss.txt`
- Create: `tests/fixtures/traceroute_unreached.txt`
- Create: `src/nettest/probes/traceroute.py`
- Create: `tests/test_traceroute_parser.py`

- [ ] **Step 1: Create fixture files**

Create `tests/fixtures/traceroute_ok.txt`:
```
traceroute to baidu.com (39.156.66.10), 20 hops max, 52 byte packets
 1  192.168.1.1  2.123 ms
 2  10.0.0.1  5.234 ms
 3  100.64.1.1  6.789 ms
 4  61.49.1.1  7.456 ms
 5  39.156.66.10  8.234 ms
```

Create `tests/fixtures/traceroute_with_loss.txt`:
```
traceroute to google.com (142.250.66.110), 20 hops max, 52 byte packets
 1  192.168.1.1  2.123 ms
 2  10.0.0.1  5.234 ms
 3  *
 4  *
 5  100.64.1.5  85.123 ms
 6  142.250.66.110  185.456 ms
```

Create `tests/fixtures/traceroute_unreached.txt`:
```
traceroute to unreach.example (203.0.113.99), 20 hops max, 52 byte packets
 1  192.168.1.1  2.123 ms
 2  10.0.0.1  5.234 ms
 3  *
 4  *
 5  *
```

- [ ] **Step 2: Write failing parser tests**

Create `tests/test_traceroute_parser.py`:
```python
from nettest.probes.traceroute import parse_traceroute_output


def test_parse_ok(fixture):
    out = parse_traceroute_output(fixture("traceroute_ok.txt"))
    assert out["target"] == "baidu.com"
    assert out["resolved_ip"] == "39.156.66.10"
    assert len(out["hops"]) == 5
    assert out["hops"][0] == {"hop": 1, "ip": "192.168.1.1", "rtt_ms": 2.123, "lost": False}
    assert out["hops"][-1]["ip"] == "39.156.66.10"
    assert out["reached"] is True


def test_parse_with_loss(fixture):
    out = parse_traceroute_output(fixture("traceroute_with_loss.txt"))
    assert out["reached"] is True
    lost_hops = [h for h in out["hops"] if h["lost"]]
    assert len(lost_hops) == 2
    assert lost_hops[0]["hop"] == 3


def test_parse_unreached(fixture):
    out = parse_traceroute_output(fixture("traceroute_unreached.txt"))
    assert out["reached"] is False
    assert all(h["lost"] for h in out["hops"][-3:])
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_traceroute_parser.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 4: Implement parser + wrapper**

Create `src/nettest/probes/traceroute.py`:
```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_traceroute_parser.py -v`
Expected: 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/traceroute_ok.txt tests/fixtures/traceroute_with_loss.txt tests/fixtures/traceroute_unreached.txt tests/test_traceroute_parser.py src/nettest/probes/traceroute.py
git commit -m "feat: add traceroute probe with parser and tests"
```

---

### Task 7: curl HTTP probe

**Files:**
- Create: `tests/fixtures/curl_ok.txt`
- Create: `src/nettest/probes/http.py`
- Create: `tests/test_http_parser.py`

The output format from `-w` is space-separated: `time_namelookup time_connect time_appconnect time_starttransfer time_total http_code`.

- [ ] **Step 1: Create fixture file**

Create `tests/fixtures/curl_ok.txt`:
```
0.012345 0.045678 0.078901 0.102345 0.123456 200
```

- [ ] **Step 2: Write failing parser tests**

Create `tests/test_http_parser.py`:
```python
import pytest
from nettest.probes.http import parse_curl_output


def test_parse_ok(fixture):
    out = parse_curl_output(fixture("curl_ok.txt"))
    assert out["http_code"] == 200
    assert out["dns_ms"] == pytest.approx(12.345)
    # connect_ms = (0.045678 - 0.012345) * 1000
    assert out["connect_ms"] == pytest.approx(33.333, abs=0.01)
    assert out["tls_ms"] == pytest.approx(33.223, abs=0.01)
    assert out["ttfb_ms"] == pytest.approx(23.444, abs=0.01)
    assert out["total_ms"] == pytest.approx(123.456)
    assert out["ok"] is True


def test_parse_failure_marker():
    # When curl times out and our wrapper writes a sentinel, parser must report failure.
    out = parse_curl_output("")
    assert out["ok"] is False
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_http_parser.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 4: Implement parser + wrapper**

Create `src/nettest/probes/http.py`:
```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_http_parser.py -v`
Expected: 2 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/curl_ok.txt tests/test_http_parser.py src/nettest/probes/http.py
git commit -m "feat: add curl HTTP timing probe with parser and tests"
```

---

### Task 8: networkQuality bandwidth probe

**Files:**
- Create: `tests/fixtures/networkquality_ok.txt`
- Create: `tests/fixtures/networkquality_missing_loaded.txt`
- Create: `src/nettest/probes/bandwidth.py`
- Create: `tests/test_bandwidth_parser.py`

- [ ] **Step 1: Create fixture files**

Create `tests/fixtures/networkquality_ok.txt`:
```
==== SUMMARY ====
Upload capacity: 42.123 Mbps
Download capacity: 285.456 Mbps
Upload flows: 16
Download flows: 12
Responsiveness: Medium (920 RPM)
Idle Latency: 12.345 milli-seconds | Loaded Latency: 38.123 milli-seconds
```

Create `tests/fixtures/networkquality_missing_loaded.txt`:
```
==== SUMMARY ====
Uplink capacity: 12.500 Mbps
Downlink capacity: 95.200 Mbps
Responsiveness: Low (180 RPM)
```

- [ ] **Step 2: Write failing parser tests**

Create `tests/test_bandwidth_parser.py`:
```python
from nettest.probes.bandwidth import parse_networkquality_output


def test_parse_ok(fixture):
    out = parse_networkquality_output(fixture("networkquality_ok.txt"))
    assert out["dl_mbps"] == 285.456
    assert out["ul_mbps"] == 42.123
    assert out["rpm"] == 920
    assert out["rpm_classification"] == "Medium"
    assert out["idle_latency_ms"] == 12.345
    assert out["loaded_latency_ms"] == 38.123
    assert out["ok"] is True


def test_parse_missing_loaded(fixture):
    out = parse_networkquality_output(fixture("networkquality_missing_loaded.txt"))
    assert out["dl_mbps"] == 95.200
    assert out["ul_mbps"] == 12.500
    assert out["rpm"] == 180
    assert out["idle_latency_ms"] is None
    assert out["loaded_latency_ms"] is None
    assert out["ok"] is True
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_bandwidth_parser.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 4: Implement parser + wrapper**

Create `src/nettest/probes/bandwidth.py`:
```python
import re
import subprocess
import time

from nettest.types import ProbeResult

# macOS phrasing varies across versions ("Uplink"/"Upload", "Downlink"/"Download").
_DL_RE = re.compile(r"Down(?:link|load) capacity:\s*([\d.]+)\s*Mbps")
_UL_RE = re.compile(r"Up(?:link|load) capacity:\s*([\d.]+)\s*Mbps")
_RPM_RE = re.compile(r"Responsiveness:\s*(\w+)\s*\((\d+)\s*RPM\)")
_IDLE_RE = re.compile(r"Idle Latency:\s*([\d.]+)\s*milli-seconds")
_LOADED_RE = re.compile(r"Loaded Latency:\s*([\d.]+)\s*milli-seconds")


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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_bandwidth_parser.py -v`
Expected: 2 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/networkquality_ok.txt tests/fixtures/networkquality_missing_loaded.txt tests/test_bandwidth_parser.py src/nettest/probes/bandwidth.py
git commit -m "feat: add networkQuality bandwidth probe with parser and tests"
```

---

### Task 9: Concurrent runner

**Files:**
- Create: `src/nettest/runner.py`
- Create: `tests/test_runner.py`

The runner orchestrates a list of (target, callable) jobs concurrently within a single dimension, with a hard wall-clock cap.

- [ ] **Step 1: Write failing test**

Create `tests/test_runner.py`:
```python
import time
from nettest.runner import run_concurrent
from nettest.types import ProbeResult


def _fake_probe(target: str, sleep_s: float = 0.05) -> ProbeResult:
    time.sleep(sleep_s)
    return ProbeResult(target=target, ok=True, data={"target": target})


def test_run_concurrent_returns_results_in_target_order():
    targets = ["a", "b", "c", "d"]
    results = run_concurrent(targets, lambda t: _fake_probe(t, 0.05), max_workers=4)
    assert [r.target for r in results] == targets
    assert all(r.ok for r in results)


def test_run_concurrent_runs_in_parallel_faster_than_serial():
    targets = ["a", "b", "c", "d"]
    started = time.monotonic()
    run_concurrent(targets, lambda t: _fake_probe(t, 0.1), max_workers=4)
    elapsed = time.monotonic() - started
    # serial would be ~0.4s; parallel should be well under 0.25s
    assert elapsed < 0.25, f"runner was not concurrent: {elapsed:.3f}s"


def test_run_concurrent_isolates_failures():
    def flaky(target: str) -> ProbeResult:
        if target == "bad":
            raise RuntimeError("boom")
        return _fake_probe(target, 0)

    results = run_concurrent(["a", "bad", "c"], flaky, max_workers=4)
    assert [r.target for r in results] == ["a", "bad", "c"]
    assert results[0].ok is True
    assert results[1].ok is False
    assert "boom" in (results[1].error or "")
    assert results[2].ok is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_runner.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement the runner**

Create `src/nettest/runner.py`:
```python
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Iterable

from nettest.types import ProbeResult


def run_concurrent(
    targets: Iterable[str],
    probe: Callable[[str], ProbeResult],
    *,
    max_workers: int = 8,
) -> list[ProbeResult]:
    targets = list(targets)
    results: list[ProbeResult | None] = [None] * len(targets)

    def _safe(idx: int, target: str) -> None:
        try:
            results[idx] = probe(target)
        except Exception as e:  # noqa: BLE001 — we want to surface any probe-level crash
            results[idx] = ProbeResult(target=target, ok=False, error=str(e))

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_safe, i, t) for i, t in enumerate(targets)]
        for f in futures:
            f.result()

    return [r for r in results if r is not None]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_runner.py -v`
Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/nettest/runner.py tests/test_runner.py
git commit -m "feat: add concurrent probe runner"
```

---

### Task 10: Environment info collection

**Files:**
- Create: `src/nettest/env.py`
- Create: `tests/test_env.py`

Collects: WiFi SSID + signal + channel, local IP, public IP + geo, system DNS. Each collector returns `None` on failure rather than raising.

- [ ] **Step 1: Write failing tests**

Create `tests/test_env.py`:
```python
import json
from unittest.mock import patch

from nettest.env import (
    parse_wifi_info,
    parse_system_dns,
    parse_local_ip,
    parse_public_ip,
)


def test_parse_wifi_info_from_system_profiler_json():
    sample = json.dumps({
        "SPAirPortDataType": [{
            "spairport_airport_interfaces": [{
                "_name": "en0",
                "spairport_current_network_information": {
                    "_name": "MyHome-5G",
                    "spairport_network_channel": "36 (5GHz, 80MHz)",
                    "spairport_signal_noise": "-52 dBm / -90 dBm",
                },
            }]
        }]
    })
    info = parse_wifi_info(sample)
    assert info["ssid"] == "MyHome-5G"
    assert info["channel"] == "36 (5GHz, 80MHz)"
    assert info["signal_dbm"] == -52


def test_parse_wifi_info_missing_returns_none_fields():
    info = parse_wifi_info(json.dumps({"SPAirPortDataType": []}))
    assert info == {"ssid": None, "channel": None, "signal_dbm": None}


def test_parse_system_dns_from_scutil():
    sample = """
DNS configuration

resolver #1
  nameserver[0] : 192.168.1.1
  nameserver[1] : 192.168.1.2

resolver #2
  domain   : local
  nameserver[0] : 224.0.0.251
"""
    assert parse_system_dns(sample) == ["192.168.1.1", "192.168.1.2"]


def test_parse_local_ip_from_route_get():
    sample = """
   route to: default
destination: default
       mask: default
    gateway: 192.168.1.1
  interface: en0
"""
    sample_ifconfig = """en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
\tinet 192.168.1.42 netmask 0xffffff00 broadcast 192.168.1.255
\tinet6 fe80::1%en0 prefixlen 64 scopeid 0x6
"""
    assert parse_local_ip(sample, sample_ifconfig) == ("en0", "192.168.1.42")


def test_parse_public_ip_from_ipinfo_json():
    sample = json.dumps({
        "ip": "223.104.99.99",
        "city": "Beijing",
        "region": "Beijing",
        "country": "CN",
        "org": "AS9808 China Mobile",
    })
    out = parse_public_ip(sample)
    assert out["ip"] == "223.104.99.99"
    assert "Beijing" in out["location"]
    assert "China Mobile" in out["org"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_env.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement env**

Create `src/nettest/env.py`:
```python
import json
import re
import subprocess
import urllib.request
from typing import Any


def parse_wifi_info(json_text: str) -> dict[str, Any]:
    blank = {"ssid": None, "channel": None, "signal_dbm": None}
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        return blank
    iface_list = data.get("SPAirPortDataType", [{}])[0].get("spairport_airport_interfaces") or []
    for iface in iface_list:
        current = iface.get("spairport_current_network_information")
        if not current:
            continue
        signal = None
        sig_text = current.get("spairport_signal_noise", "")
        m = re.match(r"(-?\d+)", sig_text)
        if m:
            signal = int(m.group(1))
        return {
            "ssid": current.get("_name"),
            "channel": current.get("spairport_network_channel"),
            "signal_dbm": signal,
        }
    return blank


def parse_system_dns(scutil_output: str) -> list[str]:
    servers: list[str] = []
    in_first_resolver = False
    for line in scutil_output.splitlines():
        if line.startswith("resolver #1"):
            in_first_resolver = True
            continue
        if line.startswith("resolver #") and not line.startswith("resolver #1"):
            break
        if in_first_resolver:
            m = re.search(r"nameserver\[\d+\]\s*:\s*([\d.]+)", line)
            if m:
                servers.append(m.group(1))
    return servers


def parse_local_ip(route_out: str, ifconfig_out: str) -> tuple[str | None, str | None]:
    iface_m = re.search(r"interface:\s*(\S+)", route_out)
    if not iface_m:
        return None, None
    iface = iface_m.group(1)
    pattern = re.compile(rf"^{re.escape(iface)}:.*?inet\s+([\d.]+)", re.DOTALL | re.MULTILINE)
    m = pattern.search(ifconfig_out)
    return (iface, m.group(1) if m else None)


def parse_public_ip(json_text: str) -> dict[str, Any]:
    try:
        d = json.loads(json_text)
    except json.JSONDecodeError:
        return {"ip": None, "location": None, "org": None}
    location_parts = [d.get("city"), d.get("region"), d.get("country")]
    location = ", ".join(p for p in location_parts if p) or None
    return {
        "ip": d.get("ip"),
        "location": location,
        "org": d.get("org"),
    }


def collect_environment() -> dict[str, Any]:
    """Best-effort collection; any failure yields None for that field."""
    env: dict[str, Any] = {
        "wifi": {"ssid": None, "channel": None, "signal_dbm": None},
        "interface": None,
        "local_ip": None,
        "system_dns": [],
        "public_ip": None,
        "location": None,
        "org": None,
    }

    try:
        wifi_proc = subprocess.run(
            ["system_profiler", "SPAirPortDataType", "-json"],
            capture_output=True, text=True, timeout=5,
        )
        env["wifi"] = parse_wifi_info(wifi_proc.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        route_proc = subprocess.run(
            ["route", "-n", "get", "default"],
            capture_output=True, text=True, timeout=3,
        )
        ifconfig_proc = subprocess.run(
            ["ifconfig"],
            capture_output=True, text=True, timeout=3,
        )
        iface, local_ip = parse_local_ip(route_proc.stdout, ifconfig_proc.stdout)
        env["interface"] = iface
        env["local_ip"] = local_ip
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        dns_proc = subprocess.run(
            ["scutil", "--dns"],
            capture_output=True, text=True, timeout=3,
        )
        env["system_dns"] = parse_system_dns(dns_proc.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        req = urllib.request.Request(
            "https://ipinfo.io/json",
            headers={"User-Agent": "net-test-pro"},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            body = resp.read().decode()
        info = parse_public_ip(body)
        env["public_ip"] = info["ip"]
        env["location"] = info["location"]
        env["org"] = info["org"]
    except Exception:  # noqa: BLE001 — best-effort; offline is fine
        pass

    return env
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_env.py -v`
Expected: 5 tests PASS.

- [ ] **Step 5: Smoke test `collect_environment` on the real machine**

Run: `uv run python -c "from nettest.env import collect_environment; import json; print(json.dumps(collect_environment(), indent=2, ensure_ascii=False))"`
Expected: prints JSON containing your current SSID, local IP, system DNS, and (if online) public IP info.

- [ ] **Step 6: Commit**

```bash
git add src/nettest/env.py tests/test_env.py
git commit -m "feat: add environment info collection (wifi, ip, dns)"
```

---

### Task 11: Rating module (thresholds)

**Files:**
- Create: `src/nettest/rating.py`
- Create: `tests/test_rating.py`

Per the spec's threshold table (§7 in the design doc). The rating module never reads probe outputs directly; it takes plain numeric inputs.

- [ ] **Step 1: Write failing tests**

Create `tests/test_rating.py`:
```python
from nettest.rating import (
    Rating,
    rate_latency,
    rate_loss,
    rate_dns_query_ms,
    rate_bandwidth_down_mbps,
    rate_rpm,
)


def test_rate_latency_domestic():
    assert rate_latency(10, region="CN") is Rating.EXCELLENT
    assert rate_latency(50, region="CN") is Rating.OK
    assert rate_latency(120, region="CN") is Rating.POOR
    assert rate_latency(200, region="CN") is Rating.BAD


def test_rate_latency_international():
    assert rate_latency(80, region="INTL") is Rating.EXCELLENT
    assert rate_latency(150, region="INTL") is Rating.OK
    assert rate_latency(300, region="INTL") is Rating.POOR
    assert rate_latency(500, region="INTL") is Rating.BAD


def test_rate_latency_none_is_bad():
    assert rate_latency(None, region="CN") is Rating.BAD


def test_rate_loss():
    assert rate_loss(0) is Rating.EXCELLENT
    assert rate_loss(0.5) is Rating.OK
    assert rate_loss(3) is Rating.POOR
    assert rate_loss(10) is Rating.BAD
    assert rate_loss(None) is Rating.BAD


def test_rate_dns():
    assert rate_dns_query_ms(20) is Rating.EXCELLENT
    assert rate_dns_query_ms(100) is Rating.OK
    assert rate_dns_query_ms(300) is Rating.POOR
    assert rate_dns_query_ms(None) is Rating.BAD


def test_rate_bandwidth():
    assert rate_bandwidth_down_mbps(200) is Rating.EXCELLENT
    assert rate_bandwidth_down_mbps(50) is Rating.OK
    assert rate_bandwidth_down_mbps(10) is Rating.POOR
    assert rate_bandwidth_down_mbps(2) is Rating.BAD


def test_rate_rpm():
    assert rate_rpm(800) is Rating.EXCELLENT
    assert rate_rpm(300) is Rating.OK
    assert rate_rpm(150) is Rating.POOR
    assert rate_rpm(50) is Rating.BAD


def test_worst_rating_helper():
    from nettest.rating import worst
    assert worst([Rating.EXCELLENT, Rating.OK, Rating.POOR]) is Rating.POOR
    assert worst([Rating.EXCELLENT, Rating.EXCELLENT]) is Rating.EXCELLENT
    assert worst([Rating.SKIPPED, Rating.EXCELLENT]) is Rating.EXCELLENT
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_rating.py -v`
Expected: `ImportError: cannot import name 'rate_latency'`.

- [ ] **Step 3: Implement rating**

Create `src/nettest/rating.py`:
```python
from typing import Iterable, Literal

from nettest.types import Rating

# Ordering for "worst" comparison: SKIPPED is ignored.
_SEVERITY = {
    Rating.EXCELLENT: 0,
    Rating.OK: 1,
    Rating.POOR: 2,
    Rating.BAD: 3,
}


def rate_latency(avg_ms: float | None, *, region: Literal["CN", "INTL"]) -> Rating:
    if avg_ms is None:
        return Rating.BAD
    if region == "CN":
        if avg_ms < 30: return Rating.EXCELLENT
        if avg_ms < 80: return Rating.OK
        if avg_ms < 150: return Rating.POOR
        return Rating.BAD
    if avg_ms < 100: return Rating.EXCELLENT
    if avg_ms < 200: return Rating.OK
    if avg_ms < 400: return Rating.POOR
    return Rating.BAD


def rate_loss(loss_pct: float | None) -> Rating:
    if loss_pct is None:
        return Rating.BAD
    if loss_pct == 0: return Rating.EXCELLENT
    if loss_pct < 1: return Rating.OK
    if loss_pct < 5: return Rating.POOR
    return Rating.BAD


def rate_dns_query_ms(ms: float | None) -> Rating:
    if ms is None:
        return Rating.BAD
    if ms < 50: return Rating.EXCELLENT
    if ms < 150: return Rating.OK
    if ms < 500: return Rating.POOR
    return Rating.BAD


def rate_bandwidth_down_mbps(mbps: float | None) -> Rating:
    if mbps is None:
        return Rating.BAD
    if mbps > 100: return Rating.EXCELLENT
    if mbps > 30: return Rating.OK
    if mbps > 5: return Rating.POOR
    return Rating.BAD


def rate_rpm(rpm: int | None) -> Rating:
    if rpm is None:
        return Rating.BAD
    if rpm > 500: return Rating.EXCELLENT
    if rpm > 200: return Rating.OK
    if rpm > 100: return Rating.POOR
    return Rating.BAD


def worst(ratings: Iterable[Rating]) -> Rating:
    effective = [r for r in ratings if r is not Rating.SKIPPED]
    if not effective:
        return Rating.SKIPPED
    return max(effective, key=lambda r: _SEVERITY[r])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_rating.py -v`
Expected: 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/nettest/rating.py tests/test_rating.py
git commit -m "feat: add rating thresholds for each indicator"
```

---

### Task 12: Diagnostic one-liner

**Files:**
- Create: `src/nettest/diagnostic.py`
- Create: `tests/test_diagnostic.py`

The diagnostic is a small rule engine that takes the aggregate results and outputs one to two sentences, e.g. detecting "google has loss but cloudflare doesn't → targeted interference suspected".

- [ ] **Step 1: Write failing tests**

Create `tests/test_diagnostic.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_diagnostic.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement diagnostic**

Create `src/nettest/diagnostic.py`:
```python
from nettest.types import Rating


def diagnose(summary: dict) -> str:
    bits: list[str] = []

    if (summary.get("google_loss_pct") or 0) > 1 and (summary.get("cloudflare_loss_pct") or 0) < 1:
        bits.append("Google 出现丢包但 Cloudflare 正常，疑似针对性干扰，可能需要代理才能稳定使用。")

    if summary.get("dns_inconsistent"):
        bits.append("不同 DNS 返回 IP 差异较大，注意可能的 DNS 污染或地域差异。")

    if summary.get("bandwidth_rating") in (Rating.POOR, Rating.BAD):
        bits.append("带宽较低，可能影响视频/下载。")

    intl = summary.get("intl_rating")
    dom = summary.get("domestic_rating")
    if intl in (Rating.POOR, Rating.BAD) and dom in (Rating.EXCELLENT, Rating.OK):
        bits.append("国内访问流畅，国际链路质量较差。")

    if not bits:
        return "当前 WiFi 各维度均良好，访问正常。"

    return " ".join(bits)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_diagnostic.py -v`
Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/nettest/diagnostic.py tests/test_diagnostic.py
git commit -m "feat: add rule-based diagnostic one-liner"
```

---

### Task 13: JSON cache

**Files:**
- Create: `src/nettest/cache.py`
- Create: `tests/test_cache.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_cache.py`:
```python
import json
from pathlib import Path

from nettest.cache import save_snapshot
from nettest.types import ProbeResult, Rating


def test_save_snapshot_writes_json(tmp_path):
    snap = {
        "timestamp": "2026-05-11T15:23:01",
        "results": {
            "ping": [ProbeResult(target="baidu.com", ok=True, data={"rtt_avg": 8.5})],
        },
        "rating": {"domestic": Rating.EXCELLENT},
    }
    path = save_snapshot(snap, cache_dir=tmp_path)
    assert path.parent == tmp_path
    assert path.suffix == ".json"
    loaded = json.loads(path.read_text())
    assert loaded["timestamp"] == "2026-05-11T15:23:01"
    assert loaded["rating"]["domestic"] == "🟢"
    assert loaded["results"]["ping"][0]["data"]["rtt_avg"] == 8.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cache.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement cache**

Create `src/nettest/cache.py`:
```python
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


def _default_dir() -> Path:
    return Path.home() / ".cache" / "nettest"


def _encode(obj: Any) -> Any:
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(f"not serializable: {type(obj)!r}")


def save_snapshot(snapshot: dict, *, cache_dir: Path | None = None) -> Path:
    cache_dir = cache_dir or _default_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    ts = snapshot.get("timestamp") or datetime.now().strftime("%Y-%m-%d-%H%M%S")
    safe_ts = ts.replace(":", "").replace("T", "-")
    path = cache_dir / f"{safe_ts}.json"
    path.write_text(json.dumps(snapshot, default=_encode, ensure_ascii=False, indent=2))
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cache.py -v`
Expected: 1 test PASSES.

- [ ] **Step 5: Commit**

```bash
git add src/nettest/cache.py tests/test_cache.py
git commit -m "feat: add JSON snapshot cache"
```

---

### Task 14: Report renderer

**Files:**
- Create: `src/nettest/report.py`
- Create: `tests/test_report.py`

Renders the human-readable terminal report using `rich`. Tests are snapshot-style: feed fixed inputs and assert key strings appear.

- [ ] **Step 1: Write failing tests**

Create `tests/test_report.py`:
```python
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
        "ping_results": [
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


def test_skipped_bandwidth_renders_skipped_marker():
    payload = _sample_payload()
    payload["bandwidth_result"] = ProbeResult("networkQuality", False, error="requires macOS 12.3+")
    payload["summary_verdicts"]["bandwidth"] = Verdict(Rating.SKIPPED, "带宽：跳过", "需要 macOS 12.3+")
    buf = StringIO()
    console = Console(file=buf, force_terminal=False, width=120)
    render_report(payload, console=console)
    out = buf.getvalue()
    assert "跳过" in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_report.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement renderer**

Create `src/nettest/report.py`:
```python
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from nettest.types import Rating, Verdict


def render_report(payload: dict, *, console: Console | None = None) -> None:
    console = console or Console()
    _render_header(payload, console)
    _render_summary(payload, console)
    _render_latency(payload, console)
    _render_dns(payload, console)
    _render_traceroute(payload, console)
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
    c.rule("① 延迟 / 丢包")
    t = Table(show_header=True, header_style="bold")
    t.add_column("目标")
    t.add_column("延迟(ms)", justify="right")
    t.add_column("抖动", justify="right")
    t.add_column("丢包", justify="right")
    t.add_column("评价")
    for r in p["ping_results"]:
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


def _render_traceroute(p: dict, c: Console) -> None:
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
    c.print(f"Responsiveness (RPM)：{d.get('rpm', '—')}")


def _render_footer(p: dict, c: Console) -> None:
    c.rule("")
    c.print(f"报告生成耗时：{p.get('elapsed_s', '?')} 秒")
    if p.get("cache_path"):
        c.print(f"完整数据已保存：{p['cache_path']}")


def _quick_latency_rating(avg: float | None, loss: float | None, target: str) -> str:
    # Approximate inline indicator using ASCII-tolerant logic; real rating is in summary.
    if avg is None or loss is None: return "🔴 故障"
    if loss > 5: return "🔴 高丢包"
    if loss > 1: return "🟠 较差"
    if avg < 30: return "🟢 优秀"
    if avg < 150: return "🟡 一般"
    return "🟠 较差"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_report.py -v`
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/nettest/report.py tests/test_report.py
git commit -m "feat: add rich-based report renderer"
```

---

### Task 15: CLI entry point and orchestration

**Files:**
- Create: `src/nettest/cli.py`

The CLI wires everything: collect env, run probes per dimension, build summary verdicts, render the report, cache snapshot.

- [ ] **Step 1: Implement CLI**

Create `src/nettest/cli.py`:
```python
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
from nettest.probes.ping import run_ping
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
    progress.print("[1/5] 延迟测试 ...", end="\r")
    ping_results = run_concurrent(
        [t.host for t in GENERAL_TARGETS],
        run_ping,
        max_workers=8,
    )
    progress.print("[2/5] DNS 解析 ...    ", end="\r")
    dns_results = run_concurrent(
        [s.ip for s in DNS_SERVERS],
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
    progress.print("                       ", end="\r")  # clear progress line

    env = collect_environment()
    summary = _build_summary(
        ping_results=ping_results,
        dns_results=dns_results,
        bandwidth_result=bandwidth_result,
    )
    diagnostic = diagnose(summary)

    elapsed_s = int(time.monotonic() - started)
    snapshot = {
        "timestamp": timestamp,
        "env": env,
        "summary": _ratings_to_str(summary),
        "diagnostic": diagnostic,
        "ping": [_pr_to_dict(r) for r in ping_results],
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

    verdicts = _build_verdicts(summary, ping_results, dns_results, bandwidth_result)

    payload = {
        "timestamp": timestamp,
        "env": env,
        "summary_verdicts": verdicts,
        "diagnostic": diagnostic,
        "ping_results": ping_results,
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
        render_report(payload, console=out_console)
    return 0


def _build_summary(*, ping_results, dns_results, bandwidth_result) -> dict:
    domestic_ping = [r for r in ping_results if r.target in {"baidu.com", "taobao.com", "qq.com", "223.5.5.5"} and r.ok]
    intl_ping = [r for r in ping_results if r.target in {"google.com", "github.com", "cloudflare.com", "1.1.1.1"} and r.ok]

    def avg_or_none(values):
        clean = [v for v in values if v is not None]
        return mean(clean) if clean else None

    dom_avg = avg_or_none([r.data.get("rtt_avg") for r in domestic_ping])
    dom_loss = avg_or_none([r.data.get("loss_pct") for r in domestic_ping])
    intl_avg = avg_or_none([r.data.get("rtt_avg") for r in intl_ping])
    intl_loss = avg_or_none([r.data.get("loss_pct") for r in intl_ping])

    google_loss = next((r.data.get("loss_pct") for r in ping_results if r.target == "google.com"), None)
    cloudflare_loss = next((r.data.get("loss_pct") for r in ping_results if r.target == "cloudflare.com"), None)

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
        bw_rating = worst([
            rate_bandwidth_down_mbps(bandwidth_result.data.get("dl_mbps")),
            rate_rpm(bandwidth_result.data.get("rpm")),
        ])
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
        "system_dns_ms": next((r.data.get("query_time_ms") for r in dns_results if r.ok), None),
    }


def _build_verdicts(summary, ping_results, dns_results, bandwidth_result):
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
            f"最快 DNS {fmt_ms(summary['system_dns_ms'])}" + ("，存在不一致" if summary["dns_inconsistent"] else "，结果一致"),
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
```

- [ ] **Step 2: Verify CLI is wired**

Run: `uv run nettest --version`
Expected: prints `nettest 0.1.0`.

Run: `uv run nettest --help`
Expected: prints help text listing all options.

- [ ] **Step 3: Commit**

```bash
git add src/nettest/cli.py
git commit -m "feat: add CLI entry point wiring all probes"
```

---

### Task 16: Smoke test the full pipeline

**Files:**
- Create: `tests/test_smoke.py`

This test runs the CLI's underlying functions (not the full network calls — those are too slow for a unit test). It uses monkeypatching to replace probe runners with fakes.

- [ ] **Step 1: Write smoke test**

Create `tests/test_smoke.py`:
```python
import json
from io import StringIO

from rich.console import Console

from nettest import cli
from nettest.types import ProbeResult


def _fake_ping(target):
    return ProbeResult(target=target, ok=True, data={
        "rtt_avg": 10.0 if "." not in target or target.startswith("2") else 150.0,
        "rtt_stddev": 1.0,
        "loss_pct": 0.0,
    })


def _fake_dig(server, domain):
    return ProbeResult(target=server, ok=True, data={"query_time_ms": 30, "ips": ["1.2.3.4"]})


def _fake_tr(target):
    return ProbeResult(target=target, ok=True, data={
        "hops": [{"hop": 1, "rtt_ms": 1.0, "ip": "192.168.1.1", "lost": False}],
        "reached": True,
    })


def _fake_curl(target):
    return ProbeResult(target=target, ok=True, data={
        "dns_ms": 10, "connect_ms": 10, "tls_ms": 30, "ttfb_ms": 50, "total_ms": 100,
        "http_code": 200, "ok": True,
    })


def _fake_nq():
    return ProbeResult(target="networkQuality", ok=True, data={
        "dl_mbps": 200, "ul_mbps": 40, "rpm": 800,
        "idle_latency_ms": 10, "loaded_latency_ms": 30,
    })


def _fake_env():
    return {
        "wifi": {"ssid": "TestWiFi", "signal_dbm": -50, "channel": "36"},
        "interface": "en0",
        "local_ip": "192.168.1.42",
        "public_ip": "1.2.3.4",
        "location": "Test, TT",
        "org": "Test Org",
        "system_dns": ["192.168.1.1"],
    }


def test_smoke_runs_end_to_end_with_fakes(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr("nettest.cli.run_ping", _fake_ping)
    monkeypatch.setattr("nettest.cli.run_dig", _fake_dig)
    monkeypatch.setattr("nettest.cli.run_traceroute", _fake_tr)
    monkeypatch.setattr("nettest.cli.run_curl", _fake_curl)
    monkeypatch.setattr("nettest.cli.run_networkquality", _fake_nq)
    monkeypatch.setattr("nettest.cli.collect_environment", _fake_env)
    monkeypatch.setattr("nettest.cli.save_snapshot", lambda snap: tmp_path / "snap.json")

    rc = cli.main(["--json"])
    assert rc == 0
    out, err = capsys.readouterr()
    payload = json.loads(out)
    assert payload["env"]["wifi"]["ssid"] == "TestWiFi"
    assert len(payload["ping"]) == 8
    assert len(payload["dns"]) == 4
    assert payload["bandwidth"]["data"]["dl_mbps"] == 200
    assert "diagnostic" in payload
```

- [ ] **Step 2: Run smoke test**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: 1 test PASSES.

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest -v`
Expected: all tests PASS (you should have roughly 30-40 tests across all parser, rating, runner, env, report, cache, and smoke suites).

- [ ] **Step 4: Commit**

```bash
git add tests/test_smoke.py
git commit -m "test: add end-to-end smoke test with fake probes"
```

---

### Task 17: Manual real-network verification + polish

**Files:**
- Modify: `README.md` (document any caveats discovered during real run)

This task is the only one that hits the real network. Do not skip it — many parser bugs only surface against real macOS tool output.

- [ ] **Step 1: Run the tool against the live network**

Run: `uv run nettest`
Expected: prints the full report. Total runtime ≈ 60-90s. Inspect:
- Header shows your real SSID/IP/DNS
- Latency table has all 8 targets with reasonable values
- DNS table has all 5 servers
- Traceroute table populated
- HTTP table populated
- Bandwidth section shows actual Mbps values

- [ ] **Step 2: If any parser failed to extract a field, capture the real output and tighten the parser**

For each failing field:
1. Run the underlying command manually: e.g., `dig @1.1.1.1 github.com +time=3 +tries=1 +stats`
2. Save the raw output as a new fixture under `tests/fixtures/`
3. Add a parser test asserting the expected output
4. Adjust the parser to make the test pass
5. Commit the fixture + test + fix together

- [ ] **Step 3: Verify alternative flags work**

Run each:
```bash
uv run nettest --no-bandwidth
uv run nettest --quiet
uv run nettest --json | jq '.summary'
uv run nettest --no-color > /tmp/report.txt && cat /tmp/report.txt
```
Expected:
- `--no-bandwidth`: bandwidth section shows `跳过`, total runtime ≈ 45s.
- `--quiet`: only summary + diagnostic printed; no tables.
- `--json`: valid JSON parseable by `jq`.
- `--no-color`: plain text file, no ANSI escapes.

- [ ] **Step 4: Confirm JSON snapshot was saved**

Run: `ls -la ~/.cache/nettest/`
Expected: lists recent timestamped `.json` files.

- [ ] **Step 5: Update README with anything user-facing learned during the run**

If `networkQuality` output format on your macOS differed and required fixes, note macOS version range in README. Otherwise just confirm install/run instructions still work.

- [ ] **Step 6: Final commit (if any changes from real-run polish)**

```bash
git add <files-changed-during-polish>
git commit -m "fix: handle real-output edge cases discovered in smoke run"
```

If nothing changed, skip the commit.

---

## Self-Review (completed by plan author)

**1. Spec coverage check** — every section in the design doc maps to one or more tasks:
- §3 design principles: covered implicitly (Tasks 4-8 shell out to system tools; Task 1 keeps deps minimal)
- §4 tech stack: Task 1
- §5 target lists: Task 3
- §6 testing dimensions and shell commands: Tasks 4-8 (one per probe)
- §7 report structure and rating: Tasks 11 (rating), 12 (diagnostic), 14 (renderer)
- §8 CLI flags: Task 15 + Task 17 verification
- §9 architecture and module split: matches Task structure 1-1
- §10 error handling: each probe wrapper handles timeouts/missing tools; runner handles raised exceptions (Task 9); env collectors swallow failures (Task 10)
- §11 testing strategy: every probe has fixture-based parser tests; rating and diagnostic have direct unit tests; report has snapshot-style tests; smoke test in Task 16; real-network verification in Task 17
- §12 distribution: pyproject configures `[project.scripts]`, `uv tool install .` works after Task 1
- §13 non-goals: not implemented — correct
- §14 risks: regex tolerance for tool output variations is built into each parser; DNS inconsistency is reported, not flagged as "pollution" (per design risk row)

**2. Placeholder scan** — no "TBD" / "implement later" / "similar to Task N" found in tasks. All code blocks contain complete, runnable code. All shell commands are exact.

**3. Type consistency** — `ProbeResult` defined in Task 2 is used identically in Tasks 4-9, 14-16. `Rating` enum members (`EXCELLENT`/`OK`/`POOR`/`BAD`/`SKIPPED`) used consistently. `Verdict` fields (`rating`, `headline`, `detail`) consistent in Tasks 14 and 15. Parser dict keys (e.g., `rtt_avg`, `query_time_ms`, `dl_mbps`) used identically in parsers and report renderer.
