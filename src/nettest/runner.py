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
