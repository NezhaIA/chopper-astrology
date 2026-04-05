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
    - pyswisseph
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
| high | 出生时间精确到分钟 + 有效经纬度 |
| medium | 出生时间差 ±30 分钟内 + 有效经纬度 |
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
| 上升星座 | ✅（需经纬度）| ✅（需经纬度）| ❌ | ❌ |
| 天顶 | ✅（需经纬度）| ✅（需经纬度）| ❌ | ❌ |
| 宫位 | ✅（需经纬度）| ❌ | ❌ | ❌ |
| 相位 | ✅ | ❌ | ❌ | ❌ |
| 格局 | ❌ | ❌ | ❌ | ❌ |

### data_source 定义

| 值 | 含义 |
|------|------|
| `swe_local` | Swiss Ephemeris 计算器执行成功 |
| `unavailable` | 计算器不可用或 precision=unknown |

### confidence 定义

| 等级 | overall | sun | moon | mercury | venus | mars | asc | mc | houses | aspects |
|------|---------|-----|------|---------|-------|------|-----|----|--------|--------|
| high | high | high | high | medium | medium | medium | high | high | high | medium |
| medium | medium | high | medium | medium | medium | medium | medium | medium | unavail | none |
| low | low | low | unavail | unavail | unavail | unavail | unavail | unavail | unavail | none |
| unavailable | unavail | low | unavail | unavail | unavail | unavail | unavail | unavail | unavail | none |

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
- `OK:swe_local`
- `DEGRADED:missing_dependencies`
- `UNAVAILABLE:calculator_not_found`

### 第二步：调用计算器

```bash
python3 scripts/chart.py --json \
  --birth-date=YYYY-MM-DD \
  --birth-time=HH:MM \
  --birth-location="地址" \
  --latitude=XX.XXXX \
  --longitude=XX.XXXX \
  --birth-time-precision=exact|estimated|approximate|unknown \
  --timezone=Asia/Shanghai
```

**--json 模式下必填参数：** `--birth-date`、`--birth-time`、`--birth-location`，任一缺失返回非零退出码并输出 JSON 错误。

**经纬度说明**：未提供 `--latitude/--longitude` 时，不输出 ascendant、midheaven、house_cusps。即使 precision=exact，若无有效经纬度，ascendant、midheaven、house_cusps 也不输出。

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

### high（precision=exact + 有效经纬度）

```json
{
  "meta": {
    "data_source": "swe_local",
    "calculator_engine": "Swiss Ephemeris 2.10.03",
    "calculator_version": "0.2.0",
    "generated_at": "ISO8601",
    "confidence": {
      "overall": "high", "sun": "high", "moon": "high",
      "mercury": "medium", "venus": "medium", "mars": "medium",
      "ascendant": "high", "midheaven": "high",
      "houses": "high",
      "aspects_fast": "medium", "aspects_slow": "medium"
    },
    "warnings": [],
    "birth_time_precision": "exact"
  },
  "input": {
    "birth_date": "YYYY-MM-DD", "birth_time": "HH:MM",
    "birth_time_precision": "exact", "birth_location": "地址",
    "latitude": 32.0, "longitude": 116.0, "timezone": "Asia/Shanghai"
  },
  "chart": {
    "planets": {
      "sun":    { "sign": "\u264c", "sign_name": "狮子座", "sign_index": 4, "degree": 23.11, "ecliptic_lon": 143.1129, "ecliptic_lat": 0.0, "house": 10 },
      "moon":   { "sign": "\u2650", "sign_name": "射手座", "sign_index": 8, "degree": 2.32,  "ecliptic_lon": 242.3159, "ecliptic_lat": 1.157,  "house": 1  },
      "mercury":{ "sign": "\u264d", "sign_name": "处女座", "sign_index": 5, "degree": 15.68, "ecliptic_lon": 165.6754, "ecliptic_lat": 0.132, "house": 11 },
      "venus":  { "sign": "\u264e", "sign_name": "天秤座", "sign_index": 6, "degree": 8.97,  "ecliptic_lon": 188.9685, "ecliptic_lat": -1.151, "house": 11 },
      "mars":   { "sign": "\u264c", "sign_name": "狮子座", "sign_index": 4, "degree": 21.43, "ecliptic_lon": 141.4286, "ecliptic_lat": 1.149,  "house": 10 }
    },
    "ascendant": { "lon": 216.5561, "sign": "\u264f", "sign_name": "天蝎座", "sign_index": 7, "degree": 6.56,  "house": 1 },
    "midheaven":{ "lon": 130.5414, "sign": "\u264c", "sign_name": "狮子座", "sign_index": 4, "degree": 10.54 },
    "house_cusps": [216.5561, 245.5395, 277.1655, 310.5414, 343.0591, 11.9774, 36.5561, 65.5395, 97.1655, 130.5414, 163.0591, 191.9774],
    "aspects": [
      { "p1": "sun", "p2": "mars", "lon1": 143.1129, "lon2": 141.4286, "angle": 1.68, "type": "conjunction", "orb": 1.68, "confidence": "high" }
    ],
    "patterns": { "identified": [], "notes": "非完整格局分析" }
  }
}
```

### medium（precision=estimated + 有效经纬度，无相位）

```json
{
  "meta": {
    "data_source": "swe_local",
    "calculator_engine": "Swiss Ephemeris 2.10.03",
    "calculator_version": "0.2.0",
    "generated_at": "ISO8601",
    "confidence": {
      "overall": "medium", "sun": "high", "moon": "medium",
      "mercury": "medium", "venus": "medium", "mars": "medium",
      "ascendant": "medium", "midheaven": "medium",
      "houses": "unavailable",
      "aspects_fast": "unavailable", "aspects_slow": "unavailable"
    },
    "warnings": [
      { "code": "BIRTH_TIME_ESTIMATED", "field": "birth_time",
        "message": "出生时间为估算值，相位不可用",
        "affected": ["ascendant", "midheaven", "aspects"] }
    ],
    "birth_time_precision": "estimated"
  },
  "input": {
    "birth_date": "YYYY-MM-DD", "birth_time": "HH:MM",
    "birth_time_precision": "estimated", "birth_location": "地址",
    "latitude": 32.0, "longitude": 116.0, "timezone": "Asia/Shanghai"
  },
  "chart": {
    "planets": {
      "sun":    { "sign": "\u264c", "sign_name": "狮子座", "sign_index": 4, "degree": 23.11, "ecliptic_lon": 143.1129, "ecliptic_lat": 0.0 },
      "moon":   { "sign": "\u2650", "sign_name": "射手座", "sign_index": 8, "degree": 2.32,  "ecliptic_lon": 242.3159, "ecliptic_lat": 1.157 },
      "mercury":{ "sign": "\u264d", "sign_name": "处女座", "sign_index": 5, "degree": 15.68, "ecliptic_lon": 165.6754, "ecliptic_lat": 0.132 },
      "venus":  { "sign": "\u264e", "sign_name": "天秤座", "sign_index": 6, "degree": 8.97,  "ecliptic_lon": 188.9685, "ecliptic_lat": -1.151 },
      "mars":   { "sign": "\u264c", "sign_name": "狮子座", "sign_index": 4, "degree": 21.43, "ecliptic_lon": 141.4286, "ecliptic_lat": 1.149 }
    },
    "ascendant": { "lon": 216.5561, "sign": "\u264f", "sign_name": "天蝎座", "sign_index": 7, "degree": 6.56, "house": 1 },
    "midheaven":{ "lon": 130.5414, "sign": "\u264c", "sign_name": "狮子座", "sign_index": 4, "degree": 10.54 },
    "aspects": [],
    "patterns": { "identified": [], "notes": "非完整格局分析" }
  }
}
```

### low（precision=approximate，仅太阳）

```json
{
  "meta": {
    "data_source": "swe_local",
    "calculator_engine": "Swiss Ephemeris 2.10.03",
    "calculator_version": "0.2.0",
    "generated_at": "ISO8601",
    "confidence": {
      "overall": "low", "sun": "low", "moon": "unavailable",
      "mercury": "unavailable", "venus": "unavailable", "mars": "unavailable",
      "ascendant": "unavailable", "midheaven": "unavailable",
      "houses": "unavailable",
      "aspects_fast": "unavailable", "aspects_slow": "unavailable"
    },
    "warnings": [
      { "code": "BIRTH_TIME_APPROXIMATE", "field": "birth_time",
        "message": "出生时间仅有模糊区间，仅太阳星座可用",
        "affected": ["moon", "mercury", "venus", "mars", "ascendant", "midheaven", "houses", "aspects"] }
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
      "sun": { "sign": "\u264c", "sign_name": "狮子座", "sign_index": 4, "degree": 23.11, "ecliptic_lon": 143.1129, "ecliptic_lat": 0.0 }
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
    "calculator_engine": "Swiss Ephemeris 2.10.03",
    "calculator_version": "0.2.0",
    "generated_at": "ISO8601",
    "confidence": {
      "overall": "unavailable", "sun": "low", "moon": "unavailable",
      "mercury": "unavailable", "venus": "unavailable", "mars": "unavailable",
      "ascendant": "unavailable", "midheaven": "unavailable",
      "houses": "unavailable",
      "aspects_fast": "unavailable", "aspects_slow": "unavailable"
    },
    "warnings": [
      { "code": "BIRTH_TIME_UNKNOWN", "field": "birth_time",
        "message": "出生时间完全未知，或计算器不可用。太阳星座置信度降为 low，不得声称精确。",
        "affected": ["moon", "mercury", "venus", "mars", "ascendant", "midheaven", "houses", "aspects"] }
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
      "sun": { "sign": "\u264c", "sign_name": "狮子座", "sign_index": 4, "degree": 23.11, "ecliptic_lon": 143.1129, "ecliptic_lat": 0.0 }
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
数据来源：[swe_local / unavailable]
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
| `OK:swe_local` | 主路径激活 |
| `DEGRADED:missing_dependencies` | 进入 unavailable |
| `UNAVAILABLE:calculator_not_found` | 进入 unavailable |

---

## 十二、适用限制

**适用：** 有出生信息的本命盘分析；无精确盘面时的咨询式对话分析

**不适用：** 娱乐星座配对；精确每日/每周运势；天文精度盘面计算

---

## 十三、对照测试

```bash
python3 scripts/chart.py --reference-test
```

输出固定测试用例（2002-08-16 11:30 北京时间，霍邱）的结构化基准数据，用于与成熟排盘软件（Astro.com、Solar Fire 等）逐项核对。此模式与正常运行路径完全隔离，不受精度参数影响。

---

## 附录一：完整输出示例

以下为才谷本命盘（2002-08-16 11:30 北京时间，安徽省霍邱县）的完整咨询式输出示例。实际输出应紧随 JSON 计算结果之后自动生成，不得以表格或 JSON 形式中断叙事流。

---

**出生信息确认**
- 出生日期：2002-08-16
- 出生时间：11:30（精度：exact）
- 出生地点：安徽省六安市霍邱县
- 置信度等级：**high**
- 数据来源：swe_local（Swiss Ephemeris 2.10.03）

---

**本命核心主题**

**☀️ 太阳星座 — 狮子座 23°**

你骨子里有一股很强的存在感需求——希望被看见、被认可、希望自己的创造和付出有意义。这种驱动力既是你最大的力量来源，也是你最容易失衡的地方。

太阳落在第十宫（事业宫），意味着你的自我价值感高度绑定于「我能创造出什么、留下什么印记」。你渴望在某个领域成为不可忽视的存在，而不是默默待在人群里。

依据：太阳狮子座 23°，落在第 10 宫，Confidence: **high**

---

**🌙 月亮星座 — 射手座 2°**

你的情感内核是自由的、向外探索的。你对被限制、被困住的感觉非常敏感，情绪上的安全感来自「世界是广阔的、值得探索的」。你容易乐观，也容易在承诺和落地感上产生落差。

月亮落在第一宫（自我宫），说明你的情绪表达和自我认同高度一致——你不会假装自己不是那样的人，你不喜欢虚伪的社交。

依据：月亮射手座 2°，落在第 1 宫，Confidence: **high**

---

**⭐ 水星 — 处女座 15°**

你的思维是精细的、分析型的。你习惯在开口前先把逻辑整理清楚，但处女座的水星容易陷入过度思考——尤其是在关系里，会反复分析对方的动机，而忘了去感受。

水星落在第十一宫（愿景宫），说明你的思维强项在系统、长线愿景、未来的可能性。

依据：水星处女座 15°，落在第 11 宫，Confidence: **medium**

---

**⭐ 金星 — 天秤座 8°**

金星天秤对关系有很强的敏感性——你喜欢和谐、被理解、审美的共鸣。关系中的不平衡会特别触动你，但天秤的倾向是宁愿让步也不愿直接冲突，长期积累会转化为隐忍或事后复盘。

金星落在第十一宫，你对友谊和社群中的平等感看得很重，也容易通过团体、圈子找到情感归属。

依据：金星期 8°，落在第 11 宫，Confidence: **medium**

---

**⭐ 火星 — 狮子座 21°**

火星和太阳同在狮子座，而且形成紧密合相（orb 1.68°）——这是你盘里最核心的动力结构。你的行动力是直接、强烈的，想要什么就去争取，不会绕弯子。但这种能量如果受挫，容易变成固执或控制欲。

火星落在第十宫（事业宫），你的竞争心和野心明显，会认真对待自己的社会成就，也会用成就来定义自我价值。

依据：火星狮子座 21°，落在第 10 宫，Confidence: **medium**

---

**主要相位解读**

**太阳合相火星（合相，orb 1.68°）**

这是你盘里最核心的动力引擎。太阳和火星在同一位置，意味着你的意志力和行动力高度合一——你要什么，就会直接去争取，不会犹豫。但这个配置需要学会将能量导向建设性方向，否则容易变成「我就是对的」的惯性模式。

Confidence: **high**

---

**事业方向**

驱动力强，尤其是和创造、表现、领导力相关的领域。第十宫有狮子座能量介入，你在事业上天生有主角意识，不甘于当配角。但需要学会将「被看见」的需求转化为真正可持续的成就，而不是靠短暂的爆发力。

依据：太阳/火星狮子座在第 10 宫，Confidence: **high**

---

**感情方向**

太阳狮子和火星狮子合相，让你对感情有很高的期待——你渴望被欣赏、被崇拜，而不仅仅是喜欢。这种标准在关系中容易造成压力，尤其是对方如果感到被你的气场压制。学会在关系里真正「倾听」，而不只是等待被认可，是这个配置最重要的成长课题。

依据：金星天秤在第 11 宫，月亮射手在第 1 宫，Confidence: **medium**

---

**财务方向**

财务能量和事业成就感强绑定——你倾向于通过创造价值、建立事业来获取财务回报，而不是节省或存钱。但狮子座/火星能量也有过度消费的倾向，需要注意把能量导向积累而非消耗。

Confidence: **medium**

---

**建议与行动方向（基于真实盘面，非通用话术）**

1. **把「大」变成「持久」**：你擅长爆发力，但真正让你脱颖而出的是把一个方向坚持做下去，而不是每件事都要立刻看到回报。建议选择一个核心领域持续深耕，用长期主义替代多方向爆发。

2. **在关系里主动问「你要什么」**：你本能地关注自己是否被认可，但天秤座能量的伴侣（或你欣赏的关系模式）更在乎平等与感受。学会在关系里先确认对方的立场，再表达自己的需求。

3. **用系统代替蛮干**：火星+太阳的组合让你习惯直接行动，这是优势也是盲点。建议在重要决策前建立一个「至少等一天」的缓冲机制，给分析型水星一个介入的机会。

---

**后续追问入口**

基于以上分析，你目前最想深入了解哪个方向？

1. 【感情/亲密关系】— 尤其我们盘里金星+火星的张力
2. 【事业/学业与人生方向】— 太阳/火星/10宫的狮子座能量如何导向
3. 【内在驱动力与自我认同】— 太阳/火星合相在日常生活中的具体表现

请选择一个，或直接告诉我你目前最想聊的事。

---

> 本 skill 基于荣格原型心理学与现代心理占星，不构成命运预测或专业医疗/法律/投资建议。
