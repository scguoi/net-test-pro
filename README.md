# net-test-pro

一个面向 macOS 的命令行 WiFi 网络体检工具：一条命令，约 1 分钟，输出当前网络到国内/国外常见目标的延迟、丢包、DNS、路由、HTTP 时序、带宽的完整报告，并给出"当前 WiFi 整体好不好用"的总评。

不重复造轮子：底层调用 macOS 自带的 `ping` / `dig` / `traceroute` / `curl` / `networkQuality`，工具本身只做编排、解析和报告生成，**零外部二进制依赖**。

## 特性

- 国内 + 国外目标对比，一目了然看出问题出在哪一层
- 5 个 DNS 服务器并发对比（系统 DNS + 阿里 + 114 + Google + Cloudflare），自动检测解析一致性
- traceroute 默认只输出摘要，`--verbose` 看完整路径
- 评级体系：🟢 优秀 / 🟡 一般 / 🟠 较差 / 🔴 故障
- 规则化"一句话诊断"：例如 Google 丢包但 Cloudflare 正常 → 提示疑似针对性干扰
- 彩色终端报告（基于 [rich](https://github.com/Textualize/rich)），也支持 `--json` / `--no-color` 给脚本消费
- 每次运行自动落盘 JSON 快照到 `~/.cache/nettest/`，方便事后对比

## 系统要求

- macOS 12.3 或更高（依赖系统自带的 `networkQuality`，旧版可用 `--no-bandwidth` 跳过）
- Python 3.11+
- [uv](https://github.com/astral-sh/uv)（推荐用于管理依赖）

## 安装

```bash
git clone https://github.com/scguoi/net-test-pro.git
cd net-test-pro
uv tool install .
```

之后即可在任意目录运行 `nettest`。

也可以不安装、直接跑：

```bash
uv run nettest
```

## 用法

```
nettest [选项]

选项:
  -v, --verbose      打印完整 traceroute 路径
  -q, --quiet        仅输出总评和一句话诊断
  --no-bandwidth     跳过带宽测试（缩短约 15 秒、不消耗流量）
  --json             输出 JSON 到 stdout，便于脚本消费
  --no-color         关闭彩色（非 TTY 时自动启用）
  --version          打印版本
  -h, --help         打印帮助
```

常见组合：

```bash
nettest                       # 完整体检（≈ 60-90s）
nettest --no-bandwidth        # 跳过带宽测试（≈ 45s）
nettest --quiet               # 只看结论
nettest --verbose             # 含完整路由
nettest --json > report.json  # 机器可读
```

## 报告内容

每次跑完输出：

1. **报告头** — 时间、WiFi 名称 + 信号强度 + 信道、本机 IP、公网 IP（含地理位置）、系统 DNS
2. **总评** — 国内网络 / 国际网络 / DNS / 带宽 四个维度的 🟢🟡🟠🔴 + 一句话诊断
3. **延迟 / 丢包** — 8 个目标的平均延迟、抖动、丢包率
4. **DNS 解析** — 5 个 DNS 服务器对同一域名的解析耗时和返回 IP，自动检测不一致
5. **路由摘要** — 每个目标的跳数、首末跳延迟、是否到达
6. **HTTP 时序** — 每个目标的 DNS / TCP / TLS / TTFB / 总时长 / 状态码
7. **带宽** — `networkQuality` 测到 Apple CDN 的下行 / 上行 / RPM / 空载 + 负载延迟
8. **结尾** — 总耗时、JSON 快照路径

## 测试目标

国内（4 个）：`baidu.com`、`taobao.com`、`qq.com`、`223.5.5.5`
国外（4 个）：`google.com`、`github.com`、`cloudflare.com`、`1.1.1.1`

含纯 IP 目标的设计：方便区分"是 DNS 出问题"还是"网络层出问题"。

## 开发

```bash
uv sync               # 安装依赖
uv run pytest -v      # 跑测试（45+ 个）
uv run nettest        # 本地跑工具
```

项目结构：

```
src/nettest/
├── cli.py              # 入口、参数解析、串联流程
├── types.py            # ProbeResult / Rating / Verdict
├── targets.py          # 预设目标清单
├── env.py              # 环境信息采集
├── runner.py           # 并发执行
├── rating.py           # 阈值评级
├── diagnostic.py       # 规则化诊断
├── report.py           # rich 渲染
├── cache.py            # JSON 落盘
└── probes/             # 5 个 probe 模块
tests/
├── fixtures/           # 真实工具输出样例
└── test_*.py           # 各模块单测 + 端到端 smoke
```

设计文档见 [`docs/superpowers/specs/`](docs/superpowers/specs/)，实现计划见 [`docs/superpowers/plans/`](docs/superpowers/plans/)。

## License

MIT — 详见 [LICENSE](LICENSE)。
