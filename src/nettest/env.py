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
    airports = data.get("SPAirPortDataType", [])
    if not airports:
        return blank
    iface_list = airports[0].get("spairport_airport_interfaces") or []
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
