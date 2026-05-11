# net-test-pro — Mac WiFi 网络体检工具 设计文档

- **日期**：2026-05-11
- **状态**：设计阶段，待用户确认后进入实现计划
- **作者**：alex89689633@gmail.com + Claude

---

## 1. 一句话定位

Mac 上的网络体检命令行工具。一条命令运行约 1 分钟，输出当前 WiFi 到国内/国外常见目标的延迟、丢包、DNS、路由、HTTP 时序、带宽报告，并给出"当前 WiFi 整体好不好用"的总评。

---

## 2. 目标用户与使用场景

- 单一用户（开发者本人）日常使用
- 切换 WiFi 后想快速摸清"这条网现在状况"
- 排查"是不是网络出问题"而非"是不是代码出问题"
- 想知道国内站点和国外站点哪个更糟、糟在哪一层（DNS / 网络 / 应用）

明确**不做**的事：
- 不做 TUI 实时仪表盘
- 不做配置化目标（用户加目标的需求暂不支持）
- 不做历史趋势对比 / 自动定时任务

---

## 3. 核心设计原则

1. **不重复造轮子** — 调用 macOS 自带的 `ping`、`dig`、`traceroute`、`curl`、`networkQuality`，工具本身只做"编排 + 解析输出 + 报告生成"
2. **零外部二进制依赖** — macOS 12.3+ 开箱即用，不需要 `brew install` 任何东西
3. **结果导向** — 用户跑一次就要拿到"够用的网络体检报告"，包含可读性强的总评 + 各维度明细
4. **一次性运行** — 不常驻、不刷新，跑完即退出

---

## 4. 技术栈

- **语言**：Python 3.11+
- **依赖管理**：`uv`（不使用系统 Python）
- **第三方库**：
  - `rich` — 彩色表格、进度条、分组输出
  - 其他保持最小化，能用标准库就用标准库（`subprocess`、`re`、`statistics`、`concurrent.futures`、`json`、`asyncio` 视情况）
- **测试**：`pytest`

不引入：requests / scapy / speedtest-cli 等，因为本项目不直接发包，只解析 shell 工具输出。

---

## 5. 测试目标清单（预设固定）

### 5.1 延迟/路由/HTTP 共用的目标（8 个）

| 地区 | 目标 | 类型 | 用途 |
|---|---|---|---|
| 🇨🇳 | `baidu.com` | 域名 | 国内通用基准 |
| 🇨🇳 | `taobao.com` | 域名 | 阿里系 CDN |
| 🇨🇳 | `qq.com` | 域名 | 腾讯系 CDN |
| 🇨🇳 | `223.5.5.5` | IP | 阿里 DNS，纯网络层基准 |
| 🌍 | `google.com` | 域名 | 验证墙的状态 |
| 🌍 | `github.com` | 域名 | 开发者高频站点 |
| 🌍 | `cloudflare.com` | 域名 | 国际 CDN |
| 🌍 | `1.1.1.1` | IP | Cloudflare DNS，纯网络层基准 |

### 5.2 DNS 维度专用对比清单

均解析 `github.com`：
- 系统 DNS（运行时检测当前 WiFi 下发的）
- `223.5.5.5`（阿里）
- `114.114.114.114`（114）
- `8.8.8.8`（Google）
- `1.1.1.1`（Cloudflare）

### 5.3 带宽

使用 `networkQuality`，测到 Apple CDN，无需指定目标。

---

## 6. 测试维度与底层命令

### ① 延迟 / 丢包（8 个目标，并发）
```
ping -c 20 -i 0.2 -W 2000 <target>
```
解析每包 RTT、丢包率、抖动 (stddev)。

### ② DNS（5 个 DNS 服务器，并发）
```
dig @<dns> github.com +time=3 +tries=1 +stats
```
解析 Query time 和返回 IP 集合，对比一致性。

### ③ 路由（8 个目标，并发）
```
traceroute -n -w 2 -q 1 -m 20 <target>
```
解析跳数、每跳延迟、`*` 丢失跳。**报告只输出摘要**（跳数、首跳/末跳延迟、是否出现延迟陡增），完整路由用 `--verbose` 才打印。

### ④ HTTP 时序（8 个目标，并发）
```
curl -sS -o /dev/null -m 10 \
  -w "%{time_namelookup} %{time_connect} %{time_appconnect} %{time_starttransfer} %{time_total} %{http_code}\n" \
  https://<target>/
```
得到 DNS / TCP / TLS / TTFB / 总时长 / 状态码。

### ⑤ 带宽（单跑，不并发）
```
networkQuality -v
```
解析下行 Mbps、上行 Mbps、空载延迟、负载延迟、Responsiveness (RPM)。

### 执行顺序（B 方案：维度间串行，维度内并发）
```
[1/5] ping × 8         ≈ 6s
[2/5] dig × 5          ≈ 1s
[3/5] traceroute × 8   ≈ 30s（瓶颈，由最慢目标决定）
[4/5] curl × 8         ≈ 10s
[5/5] networkQuality   ≈ 15s
合计 约 60~70s
```

---

## 7. 报告输出（核心交付物）

完整样例见对话中 §4，要点：

- **报告头**：时间、WiFi 名称 + 信号强度 + 信道、本机 IP、公网 IP（含归属地）、系统 DNS
- **总评**（首屏可见）：
  - 国内网络 🟢/🟡/🔴 + 简短判断
  - 国际网络 🟢/🟡/🔴 + 简短判断
  - DNS 🟢/🟡/🔴 + 简短判断
  - 带宽 🟢/🟡/🔴 + 简短判断
  - 一句话整体诊断（基于规则推断，例如检测到 google.com 有丢包但 cloudflare 正常 → 提示"疑似 google 被针对性干扰"）
- **5 个维度的明细表**
- **结尾**：耗时、完整数据 JSON 落盘路径

### 评级阈值（初版规则，后续可调）

| 指标 | 🟢 优秀 | 🟡 一般 | 🟠 较差 | 🔴 故障 |
|---|---|---|---|---|
| 国内延迟 | < 30ms | 30-80 | 80-150 | > 150 或丢包>5% |
| 国际延迟 | < 100ms | 100-200 | 200-400 | > 400 或丢包>5% |
| 丢包率 | 0% | < 1% | 1-5% | > 5% |
| DNS 耗时 | < 50ms | 50-150 | 150-500 | 超时 |
| 带宽 ↓ | > 100Mbps | 30-100 | 5-30 | < 5 |
| RPM | > 500 | 200-500 | 100-200 | < 100 |

### 输出物
- **stdout**：彩色报告（用 `rich`）。检测到不是 TTY 时自动关闭颜色，方便 `> report.txt` 重定向。
- **JSON 落盘**：完整原始数据写入 `~/.cache/nettest/<timestamp>.json`，方便事后比对/取证。

---

## 8. 命令行接口

```
nettest [选项]

选项：
  -v, --verbose      打印完整 traceroute 路由和每个目标的原始数据
  -q, --quiet        仅打印总评 + 一句话诊断，不打印明细表
  --no-bandwidth     跳过带宽测试（节省 15 秒，不消耗流量）
  --json             以 JSON 格式打印到 stdout（不打印人类可读报告）
  --no-color         强制关闭颜色（非 TTY 时自动开启此模式）
  --version
  -h, --help
```

不做的选项：自定义目标、定时运行、对比历史报告。

---

## 9. 架构与模块划分

```
src/nettest/
├── __init__.py
├── cli.py              # 入口、参数解析、串联流程
├── targets.py          # 预设目标清单（5.1/5.2 表中数据）
├── env.py              # 环境信息采集（WiFi 名称/信号/信道、本机 IP、公网 IP、系统 DNS）
├── probes/
│   ├── __init__.py
│   ├── ping.py         # 调用 ping，解析输出
│   ├── dns.py          # 调用 dig，解析输出
│   ├── traceroute.py   # 调用 traceroute，解析输出
│   ├── http.py         # 调用 curl，解析输出
│   └── bandwidth.py    # 调用 networkQuality，解析输出
├── runner.py           # 并发执行各 probe（同维度并发，维度间串行）
├── rating.py           # 阈值规则、🟢🟡🟠🔴 评级、一句话诊断生成
├── report.py           # rich 渲染人类可读报告 / JSON 序列化
└── cache.py            # JSON 落盘到 ~/.cache/nettest/

tests/
├── fixtures/           # 各工具的真实输出样例（ping/dig/traceroute/curl/networkQuality）
├── test_probes.py      # 解析器单测，喂 fixtures，验证产出结构
├── test_rating.py      # 评级规则单测
└── test_report.py      # 报告渲染快照测试
```

### 数据流
```
env.collect()                ─┐
targets.load()                ├─► runner.run_all()
probes.* (并发)              ─┘       │
                                      ▼
                              raw_results: dict
                                      │
                                      ├─► rating.evaluate() ─► verdict
                                      │
                                      └─► report.render() / report.to_json()
                                                  │
                                                  └─► cache.save()
```

### 文件大小约束
单文件 < 400 行，参考全局 coding style 要求。

---

## 10. 错误处理

| 场景 | 处理方式 |
|---|---|
| 工具缺失（极少见，例如 `dig`） | 启动时检查，缺少则报"需要 macOS 12.3+"，列出缺哪个工具 |
| `networkQuality` 不存在（macOS < 12） | 带宽维度标记 ⏭️ 跳过，其他维度照常，报告里注明 |
| 单个目标 ping 全丢包 | 该目标显示 🔴 + 标 "100% 丢包"，不影响其他目标 |
| traceroute 中途超时 | 显示已探测到的部分 + "未到达" 标记 |
| curl 超时 / 连接拒绝 | 表格显示 timeout / refused，状态 🔴 |
| 无网络（默认网关 unreachable） | 启动时探测一次，若无网络直接报错退出，不浪费时间 |
| 子进程异常 | 单 probe 异常不影响整体；该 probe 标记失败，报告记录原因 |
| `Ctrl+C` | 取消所有未完成的子进程，打印"已中断"提示 |

所有 probe 的执行结果统一是 `Result(ok: bool, data: dict, error: str | None)`，下游 rating/report 模块不需要分支处理"成功/失败"。

---

## 11. 测试策略

- **Parser 单测**：每个 probe 的解析函数喂入 `tests/fixtures/` 里真实工具的输出文本，验证产出的字段、类型、数值。
  - 准备 fixtures 时跑一次工具，把 stdout 复制进 fixtures 目录
  - 包含 happy path + 异常 path（超时、全丢包、部分失败）
- **Rating 单测**：构造各种数据组合，验证评级和"一句话诊断"的判定逻辑
- **Report 快照测试**：固定输入数据，渲染出文本，与快照比对，回归友好
- **Smoke 集成测试**：跑一次完整流程，仅断言"没抛异常 + 生成了 JSON 文件 + 报告含必要章节"。不依赖具体网络环境数值。
- **目标覆盖率**：单测覆盖率 > 80%，重点在 probes 解析逻辑（这是最容易出错的部分）。

---

## 12. 分发方式

- 项目用 `uv` 管理，发布形态：
  - `uv tool install .` 后获得全局 `nettest` 命令
  - 也支持 `uvx --from . nettest`（无需安装）
- 后续可考虑发布到 PyPI 或写一个 Homebrew formula，但**本期不做**

---

## 13. 非目标（避免范围蔓延）

- ❌ 不做 IPv6 专项测试（一般用户用不上，复杂度高）
- ❌ 不做 WebSocket / UDP 应用层测试
- ❌ 不做代理探测（"我用的是 Clash 哪条规则"这种问题）
- ❌ 不做电池友好的低频后台轮询
- ❌ 不做 Windows / Linux 支持（macOS 专属）

---

## 14. 风险与权衡

| 风险 | 影响 | 缓解 |
|---|---|---|
| 解析 shell 输出依赖具体版本格式 | 未来 macOS 升级可能改输出 | parser 单测 + 容错解析（找不到字段就 None，不崩溃） |
| `traceroute` 是整体时长瓶颈 | 用户等不及 | 后期考虑 `--quick` 模式跳过 traceroute；本期不实现 |
| `networkQuality` 测到 Apple CDN，国内用户结果不代表真实速度 | 带宽数据偏高 | 报告里注明"测到 Apple CDN" |
| 不同 DNS 返回 github.com 的 IP 本身就可能不同（CDN 地域分配），不一定等于污染 | DNS 一致性判定容易误报 | 判定时只比对"返回的 IP 是否落在合理的同一 ASN/区域池"；无法可靠判定时只展示数据，不下"污染"结论 |
| "一句话诊断"是规则推断，可能误判 | 给用户错误结论 | 规则尽量保守、写"疑似"而非"确定"，明细表保留原始数据让用户自己判断 |

---

## 15. 实现里程碑（粗粒度，详细计划由 writing-plans 产出）

1. 项目骨架 + `uv` 配置 + CI 基础
2. 各 probe 解析器（用 fixtures 做 TDD）
3. runner 并发编排
4. env 信息采集
5. rating 规则 + 一句话诊断
6. report 渲染（rich）+ JSON 序列化
7. CLI 串联 + 错误处理
8. smoke 测试 + 真机跑通
