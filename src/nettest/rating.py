from typing import Iterable, Literal

from nettest.types import Rating

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
