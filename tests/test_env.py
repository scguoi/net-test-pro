import json

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
