import json

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
