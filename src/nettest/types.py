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
