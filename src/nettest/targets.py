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
