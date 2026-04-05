---
name: chopper-astrology
version: "0.2.0"
description: >
  占星咨询技能。当用户提到以下场景时激活：
  - 想看本命盘、星盘、占星分析
  - 提供生日、出生时间、出生地，询问性格/感情/事业/财务
  - 想做近期运势、近况分析、人生方向建议
  - 需要通过占星辅助当前决策或情绪困惑
  关键词：星盘、占星、命盘、太阳星座、月亮星座、上升星座、本命盘
triggers:
  - "*占星*"
  - "*星盘*"
  - "*命盘*"
  - "*太阳星座*"
  - "*月亮星座*"
  - "*上升*星座*"
  - "*本命盘*"
  - "*出生*年*月*日*"
  - "*感情*事业*占星*"
  - "*运势*占星*"
requires:
  python: "3.9"
  packages:
    - ephem
    - pytz
---

# Chopper Astrology — 占星咨询技能 v0.2

## 定位

本 skill 是占星**咨询流程编排器 + 解释引擎**，不进行天文计算。

职责：
1. 引导用户完成出生信息采集
2. 调用本地计算器 `scripts/chart.py` 获取结构化星盘 JSON
3. 基于 JSON 结果进行心理占星解读
4. 真值源不可用时主动降级，不虚构数据

**核心原则**：不做确定性预言，只做基于象征系统的自我觉察工具。所有结论必须同时给出「依据」和「置信度」。

---

## 一、置信度分级体系（四级）

| 等级 | 触发条件 |
|------|----------|
| high | 出生时间精确到分钟 |
| medium | 出生时间差 ±30 分钟内 |
| low | 出生时间差 ±30 分钟 ~ ±2 小时 |
| unavailable | 出生时间完全未知；或计算器不可用 |

### 各等级数据裁剪规则

| 输出内容 | high | medium | low | unavailable |
|----------|------|---------|-----|-------------|
| 太阳星座 | ✅ | ✅ | ✅ | ✅（置信度 low）|
| 月亮星座 | ✅ | ✅ | ❌ | ❌ |
| 水星星座 | ✅ | ✅ | ❌ | ❌ |
| 金星星座 | ✅ | ✅ | ❌ | ❌ |
| 火星星座 | ✅ | ✅ | ❌ | ❌ |
| 婚神星座 | ✅ | ❌ | ❌ | ❌ |
| 上升星座 | ❌ | ❌ | ❌ | ❌ |
| 相位 | ✅ | ❌ | ❌ | ❌ |
| 宫位 | ❌ | ❌ | ❌ | ❌ |
| 格局 | ❌ | ❌ | ❌ | ❌ |

### data_source 定义

| 值 | 含义 |
|------|------|
| `local_cli` | 计算器执行成功 |
| `unavailable` | 计算器不可用或 precision=unknown |

### confidence 定义

| 等级 | overall | sun | moon | mercury | venus | mars | juno | aspects |
|------|---------|-----|------|---------|-------|------|------|--------|
| high | high | high | high | medium | medium | medium | low | medium |
| medium | medium | high | medium | medium | medium | medium | unavail | none |
| low | low | low | unavail | unavail | unavail | unavail | unavail | none |
| unavailable | unavail | low | unavail | unavail | unavail | unavail | unavail | none |

**unavailable 的 sun=low 说明**：太阳星座虽可计算，但因出生时间完全未知，置信度降为 low。解释层按 low 规则输出太阳结论，不得声称精确。

---

## 二、外部真值源调用规则

### 优先级

```
本地计算器 scripts/chart.py  →  unavailable 模式（兜底）
     [主路径]                       [无 fallback]
```

### 第一步：检查环境

```bash
python3 scripts/check_dependencies.py
```

stdout 第一行必须是以下三种状态之一：
- `OK:local_cli`
- `DEGRADED:missing_dependencies`
- `UNAVAILABLE:calculator_not_found`

### 第二步：调用计算器

```bash
python3 scripts/chart.py --json \
  --birth-date=YYYY-MM-DD \
  --birth-time=HH:MM \
  --birth-location="地址" \
  --birth-time-precision=exact|estimated|approximate|unknown \
  --timezone=Asia/Shanghai
```

**--json 模式下必填参数：** `--birth-date`、`--birth-time`、`--birth-location`，任一缺失返回非零退出码并输出 JSON 错误。

---

## 三、安装后默认行为

skill 首次被调用时，若用户未提供完整出生信息，**必须先进入 intake**，不得跳过直接分析。

### Intake 流程

```
你好，我是乔巴的占星咨询技能。在开始分析之前，我需要收集一些基本信息：

1. 阳历出生日期（YYYY-MM-DD）
2. 出生时间（精确到几点几分）
3. 出生地点（城市或区县级别）
4. 出生时间是否精确到分钟？
   A. 精确到分钟
   B. 大概知道几点，不确定几分
   C. 只知道上午/下午，不确定几点
   D. 完全不确定

请依次告诉我，我会根据信息的完整度选择合适的分析方法。
```

### 精度与置信度映射

| 用户回答 | 置信度 | --birth-time-precision |
|----------|--------|----------------------|
| A. 精确到分钟 | high | exact |
| B. 大概几点 | medium | estimated |
| C. 上午/下午 | low | approximate |
| D. 完全不确定 | unavailable | unknown |

---

## 四、出生信息校验规则

### 禁止行为

- ❌ 不得将"上午""中午""大概"自动转换为具体时间
- ❌ 不得在 unavailable 时声称太阳星座精确
- ❌ 不得在 unavailable 时输出月亮、水星、金星、火星、相位
- ❌ 不得在 low 时输出确定的月亮星座
- ❌ 不得伪造 `meta.data_source`
- ❌ 不得在无 JSON 结果时直接解释

---

## 五、统一 JSON 契约

### high（precision=exact）

```json
{
  "meta": {
    "data_source": "local_cli",
    "calculator_version": "0.1.0",
    "generated_at": "ISO8601",
    "confidence": {
      "overall": "high", "sun": "high", "moon": "high",
      "mercury": "medium", "venus": "medium", "mars": "medium",
      "juno": "low", "houses": "unavailable",
      "aspects_fast": "medium", "aspects_slow": "medium"
    },
    "warnings": [],
    "birth_time_precision": "exact"
  },
  "input": {
    "birth_date": "YYYY-MM-DD", "birth_time": "HH:MM",
    "birth_time_precision": "exact", "birth_location": "地址",
    "latitude": null, "longitude": null, "timezone": "Asia/Shanghai"
  },
  "chart": {
    "planets": {
      "sun": { "sign": "\u2648", "sign_name": "白羊座", "degree": 16.6, "raw_lon": 16.6 },
      "moon": { "sign": "\u2648", "sign_name": "白羊座", "degree": 25.8, "raw_lon": 25.8 },
      "mercury": { "sign": "\u2652", "sign_name": "水瓶座", "degree": 9.1, "raw_lon": 309.1 },
      "venus": { "sign": "\u2653", "sign_name": "双鱼座", "degree": 2.4, "raw_lon": 332.4 },
      "mars": { "sign": "\u2651", "sign_name": "摩羯座", "degree": 14.9, "raw_lon": 284.9 },
      "juno": { "sign": "\u2652", "sign_name": "水瓶座", "degree": 29.0, "raw_lon": 299.0 }
    },
    "aspects": [
      { "p1": "sun", "p2": "mars", "angle": 1.7, "type": "conjunction", "orb": 1.7, "confidence": "medium" }
    ],
    "patterns": { "identified": [], "notes": "非完整格局分析" }
  }
}
```

### medium（precision=estimated）

```json
{
  "meta": {
    "data_source": "local_cli",
    "calculator_version": "0.1.0",
    "generated_at": "ISO8601",
    "confidence": {
      "overall": "medium", "sun": "high", "moon": "medium",
      "mercury": "medium", "venus": "medium", "mars": "medium",
      "juno": "unavailable", "houses": "unavailable",
      "aspects_fast": "unavailable", "aspects_slow": "unavailable"
    },
    "warnings": [
      { "code": "BIRTH_TIME_ESTIMATED", "field": "birth_time",
        "message": "出生时间为估算值，相位不可用",
        "affected": ["moon", "aspects"] }
    ],
    "birth_time_precision": "estimated"
  },
  "input": {
    "birth_date": "YYYY-MM-DD", "birth_time": "HH:MM",
    "birth_time_precision": "estimated", "birth_location": "地址",
    "latitude": null, "longitude": null, "timezone": "Asia/Shanghai"
  },
  "chart": {
    "planets": {
      "sun": { "sign": "\u2648", "sign_name": "白羊座", "degree": 16.6, "raw_lon": 16.6 },
      "moon": { "sign": "\u2648", "sign_name": "白羊座", "degree": 25.8, "raw_lon": 25.8 },
      "mercury": { "sign": "\u2652", "sign_name": "水瓶座", "degree": 9.1, "raw_lon": 309.1 },
      "venus": { "sign": "\u2653", "sign_name": "双鱼座", "degree": 2.4, "raw_lon": 332.4 },
      "mars": { "sign": "\u2651", "sign_name": "摩羯座", "degree": 14.9, "raw_lon": 284.9 }
    },
    "aspects": [],
    "patterns": { "identified": [], "notes": "非完整格局分析" }
  }
}
```

### low（precision=approximate）

```json
{
  "meta": {
    "data_source": "local_cli",
    "calculator_version": "0.1.0",
    "generated_at": "ISO8601",
    "confidence": {
      "overall": "low", "sun": "low", "moon": "unavailable",
      "mercury": "unavailable", "venus": "unavailable", "mars": "unavailable",
      "juno": "unavailable", "houses": "unavailable",
      "aspects_fast": "unavailable", "aspects_slow": "unavailable"
    },
    "warnings": [
      { "code": "BIRTH_TIME_APPROXIMATE", "field": "birth_time",
        "message": "出生时间仅有模糊区间，仅太阳星座可用",
        "affected": ["moon", "mercury", "venus", "mars", "juno", "aspects"] }
    ],
    "birth_time_precision": "approximate"
  },
  "input": {
    "birth_date": "YYYY-MM-DD", "birth_time": "HH:MM",
    "birth_time_precision": "approximate", "birth_location": "地址",
    "latitude": null, "longitude": null, "timezone": "Asia/Shanghai"
  },
  "chart": {
    "planets": {
      "sun": { "sign": "\u2648", "sign_name": "白羊座", "degree": 16.6, "raw_lon": 16.6 }
    },
    "aspects": [],
    "patterns": { "identified": [], "notes": "非完整格局分析" }
  }
}
```

### unavailable（precision=unknown 或计算器不可用）

```json
{
  "meta": {
    "data_source": "unavailable",
    "calculator_version": "0.1.0",
    "generated_at": "ISO8601",
    "confidence": {
      "overall": "unavailable", "sun": "low", "moon": "unavailable",
      "mercury": "unavailable", "venus": "unavailable", "mars": "unavailable",
      "juno": "unavailable", "houses": "unavailable",
      "aspects_fast": "unavailable", "aspects_slow": "unavailable"
    },
    "warnings": [
      { "code": "BIRTH_TIME_UNKNOWN", "field": "birth_time",
        "message": "出生时间完全未知，或计算器不可用。太阳星座置信度降为 low，不得声称精确。",
        "affected": ["moon", "mercury", "venus", "mars", "juno", "aspects"] }
    ],
    "birth_time_precision": "unknown"
  },
  "input": {
    "birth_date": "YYYY-MM-DD", "birth_time": "HH:MM",
    "birth_time_precision": "unknown", "birth_location": "地址",
    "latitude": null, "longitude": null, "timezone": "Asia/Shanghai"
  },
  "chart": {
    "planets": {
      "sun": { "sign": "\u2648", "sign_name": "白羊座", "degree": 16.6, "raw_lon": 16.6 }
    },
    "aspects": [],
    "patterns": { "identified": [], "notes": "非完整格局分析" }
  }
}
```

**必填字段：** `meta.data_source`、`meta.confidence`、`input.birth_date`、`chart.planets.sun`

---

## 六、分析输出结构

### 6.1 信息确认

```
出生日期：YYYY-MM-DD
出生时间：HH:MM（精度：[exact / estimated / approximate / unknown]）
出生地点：XX省XX市XX区/县
置信度等级：[high / medium / low / unavailable]
数据来源：[local_cli / unavailable]
```

### 6.2 置信度说明

```
置信度等级：{meta.confidence.overall}
可用范围：{基于 JSON 中实际出现的行星字段}
警告项：{meta.warnings}
```

### 6.3 本命核心主题

**☀️ 太阳星座 — 核心自我**（始终输出）
- 结论：
- 依据：
- 置信度：

**🌙 月亮星座**（仅当 JSON 中存在 moon 字段时）
- 结论：
- 依据：
- 置信度：

### 6.4 三大方向分析

每个方向均含：结论 + 依据 + 置信度。

### 6.5 建议与行动方向（1-3 条）

### 6.6 后续追问入口

```
📌 基于以上分析，你目前最想深入了解哪个方向？

1. 【感情/亲密关系】
2. 【事业/学业与人生方向】
3. 【财务/重大决策压力】

请选择一个，或直接告诉我你目前最想聊的事。
```

---

## 七、证据链约束与禁止事项

- ❌ 在 unavailable 时声称太阳星座精确
- ❌ 在 unavailable 时输出月亮、水星、金星、火星、相位
- ❌ 在 low 时输出确定的月亮星座
- ❌ 伪造 `meta.data_source`
- ❌ 在无 JSON 结果时直接解释

---

## 八、输出前自检清单

```
[ ] 是否标注了 meta.data_source？
[ ] confidence.overall 为哪一级？
[ ] JSON 中是否只包含该置信度允许的行星字段？
[ ] unavailable 时 sun 是否以 low 置信度输出，且已注明不得声称精确？
[ ] 是否已给出后续追问入口？
```

---

## 九、风格规范

- ✅ 专业、稳健、有洞察感、有边界感
- ❌ 禁止神化（"宇宙能量""灵性觉醒"）
- ❌ 禁止绝对化（"你一定会""命中注定"）
- ❌ 禁止制造恐慌（"水逆会导致灾难"）

---

## 十、风险与边界

- ✅ 可用于：自我觉察、性格理解、情感沟通、决策参考、情绪梳理
- ❌ 不可用于：替代医疗诊断、法律建议，投资决策，心理治疗

---

## 十一、首次使用检查

```bash
python3 scripts/check_dependencies.py
```

| stdout 第一行 | 含义 |
|------|------|
| `OK:local_cli` | 主路径激活 |
| `DEGRADED:missing_dependencies` | 进入 unavailable |
| `UNAVAILABLE:calculator_not_found` | 进入 unavailable |

---

## 十二、适用限制

**适用：** 有出生信息的本命盘分析；无精确盘面时的咨询式对话分析

**不适用：** 娱乐星座配对；精确每日/每周运势；天文精度盘面计算

---

> 本 skill 基于荣格原型心理学与现代心理占星，不构成命运预测或专业医疗/法律/投资建议。
