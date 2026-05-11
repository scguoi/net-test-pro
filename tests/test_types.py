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
