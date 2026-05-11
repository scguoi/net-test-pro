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
