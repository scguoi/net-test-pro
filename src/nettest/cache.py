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
