# 🌟 Chopper Astrology

> 开源 AI Agent 占星咨询 Skill — 让任意 Agent 变身为你的专属心理占星师。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 是什么

`chopper-astrology` 是 AI Agent 的占星能力包。安装后 Agent 可根据出生信息计算星盘，并生成基于荣格原型心理学的叙事解读。

**核心差异**：不是娱乐星座速查，而是自我认知工具。疗愈导向，拒绝宿命论。

## 支持的行星

| 符号 | 行星 | 解读维度 |
|------|------|----------|
| ☀️ | 太阳 | 核心自我、人生使命 |
| 🌙 | 月亮 | 情感模式、潜意识需求 |
| ♀️ | 金星 | 情感模式、审美引力 |
| ♂️ | 火星 | 行动力、冲突模式 |
| ☿ | 水星 | 思维与沟通方式 |
| ⚹ | 婚神 | 长期关系模式、承诺需求 |

**注意**：本轮不包含上升星座和宫位系统。

## 安装

```
/skill install chopper-astrology
```

或手动安装：

```bash
git clone https://github.com/daisy-ai/chopper-astrology.git
cd chopper-astrology
pip install ephem pytz
```

## 依赖

- Python 3.9+
- `ephem` — 星体位置计算
- `pytz` — 时区处理

Skill **不调用任何 LLM API**，解读生成由 Agent 内置模型完成。

## 首次使用检查

| stdout 第一行 | 含义 |
|------|------|
| `OK:local_cli` | 全部功能可用 |
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
| high | 时间精确到分钟 | 太阳、月亮、水星、金星、火星、婚神、相位 |
| medium | 时间差 ±30 分钟内 | 太阳、月亮、水星、金星、火星、无相位 |
| low | 时间差 ±30 分钟 ~ ±2 小时 | 仅太阳星座 |
| unavailable | 时间完全未知 | 仅太阳星座（置信度 low）|

## 项目结构

```
chopper-astrology/
├── SKILL.md
├── README.md
├── LICENSE
└── scripts/
    ├── chart.py
    ├── check_dependencies.py
    └── requirements.txt
```

## 当前实现

- **星体位置**：`ephem` 库，RA/Dec 转热带黄道经度
- **婚神星**：VSOP87 近似轨道（仅 high 时输出）
- **相位**：合相/六分相/四分相/三分相/对分相（仅 high 时输出）

## 当前未实现

| 内容 | 处理 |
|------|------|
| 上升星座 | unavailable |
| 宫位系统 | unavailable |
| 地理编码 | latitude/longitude=null |
| 格局分析 | patterns.identified=[] |
| 远程 API | 本轮未实现 |

## License

MIT
