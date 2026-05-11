from nettest.types import Rating


def diagnose(summary: dict) -> str:
    bits: list[str] = []

    if (summary.get("google_loss_pct") or 0) > 1 and (summary.get("cloudflare_loss_pct") or 0) < 1:
        bits.append("Google 出现丢包但 Cloudflare 正常，疑似针对性干扰，可能需要代理才能稳定使用。")

    if summary.get("dns_inconsistent"):
        bits.append("不同 DNS 返回 IP 差异较大，注意可能的 DNS 污染或地域差异。")

    if summary.get("bandwidth_rating") in (Rating.POOR, Rating.BAD):
        bits.append("带宽较低，可能影响视频/下载。")

    intl = summary.get("intl_rating")
    dom = summary.get("domestic_rating")
    if intl in (Rating.POOR, Rating.BAD) and dom in (Rating.EXCELLENT, Rating.OK):
        bits.append("国内访问流畅，国际链路质量较差。")

    if not bits:
        return "当前 WiFi 各维度均良好，访问正常。"

    return " ".join(bits)
