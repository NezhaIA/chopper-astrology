# 🌟 Chopper Astrology

> 开源 AI Agent 占星咨询 Skill — 让任意 Agent 变身为你的专属心理占星师。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 是什么

`chopper-astrology` 是 AI Agent 的占星能力包。安装后 Agent 可根据出生信息计算星盘，并生成基于荣格原型心理学的叙事解读。

**核心差异**：不是娱乐星座速查，而是自我认知工具。疗愈导向，拒绝宿命论。

## 真值源

**Swiss Ephemeris**（`pyswisseph`）— 行业标准天文星历表，精度达 0.001 角秒。
- 行星位置：DE431/DE436 星历
- 上升点/天顶：Placidus 宫位系统
- 不依赖网络，不调用外部 API

## 安装

```
/skill install chopper-astrology
```

或手动安装：

```bash
git clone https://github.com/NezhaIA/chopper-astrology.git
cd chopper-astrology
pip install -r scripts/requirements.txt
```

## 依赖

- Python 3.9+
- `pyswisseph` ≥ 2.10 — Swiss Ephemeris Python 绑定
- `pytz` ≥ 2024 — 时区处理

## 首次使用检查

```bash
python3 scripts/check_dependencies.py
```

| stdout 第一行 | 含义 |
|------|------|
| `OK:swe_local` | 全部功能可用 |
| `DEGRADED:missing_dependencies` | 仅 unavailable 模式 |
| `UNAVAILABLE:calculator_not_found` | 仅 unavailable 模式 |

## 快速开始

```
出生日期：1990-06-15
出生时间：14:30
出生地点：上海
出生时间精确度：精确到分钟
```

Agent 自动完成：检查环境 → 计算星盘 → 生成解读。

## 置信度等级

| 等级 | 条件 | 可用数据 |
|------|------|----------|
| high | 时间精确到分钟 + 有效经纬度 | 太阳、月亮、水星、金星、火星、上升点、天顶、宫位、相位 |
| medium | 时间差 ±30 分钟内 + 有效经纬度 | 太阳、月亮、水星、金星、火星、上升点、天顶、无相位 |
| low | 时间差 ±30 分钟 ~ ±2 小时 | 仅太阳星座 |
| unavailable | 时间完全未知 | 仅太阳（置信度 low）|

**注意**：上升点、天顶、宫位需要有效经纬度。未提供经纬度时，即使 precision=exact 也不输出 ASC/MC/houses。

## 项目结构

```
chopper-astrology/
├── SKILL.md
├── README.md
├── LICENSE
└── scripts/
    ├── chart.py              # Swiss Ephemeris 计算器
    ├── check_dependencies.py
    └── requirements.txt
```

## 对照测试

```bash
python3 scripts/chart.py --reference-test
```

此命令输出固定测试用例的基准数据，用于与 Astro.com、Solar Fire 等成熟排盘软件逐项核对。

## 当前实现

| 内容 | 方法 |
|------|------|
| 行星黄经 | Swiss Ephemeris DE431/DE436 |
| 上升点/天顶 | Swiss Ephemeris Placidus 宫位 |
| 宫位制 | Placidus |
| 主要相位 | 合/六分/四分/三分/对分（容许度 6-8°）|

## 当前未实现

| 内容 | 处理 |
|------|------|
| 地理编码 | latitude/longitude=null 或手动传入 |
| 格局分析 | patterns.identified=[] |
| 南北交点 | 后续版本 |
| 先天盘/后天盘 | 后续版本 |

## License

MIT
