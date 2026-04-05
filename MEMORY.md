# MEMORY.md

## chopper-astrology 项目

### 定位
开源 AI Agent 占星 Skill，GitHub 一键安装后 Agent 直接具备占星能力。聚焦 7 颗核心行星（太阳/月亮/上升/金星/火星/水星/婚神），心理占星叙事。

### 项目路径
`~/openclaw-projects/chopper-astrology/`

### 技术栈
- Python 3.9+, `ephem`, `pytz`
- 星盘计算：`ephem` 计算 RA/Dec → 热带黄道经度（含岁差修正 +23.44°）
- 婚神星：VSOP87 近似轨道 + Kepler 方程
- LLM 调用：留给 Agent 自身配置，Skill 不含 API key

### 核心文件
- `SKILL.md` — Skill 元信息
- `src/chart.py` — 计算核心
- `prompts/*.md` — 7 颗行星解读模板

### 已知限制
- 婚神星精度 ±2°（简化轨道）
- 上升点简化 Placidus 公式，精度 ±1°
- 岁差用固定值 23.44°，2000年后误差 <0.1°

### GitHub 发布待完成
需要才谷确认：GitHub repo 地址、是否需要初始化 git 等。

### 关键调试记录
- ephem.Body.ra/dec 是 Angle 对象，必须除 ephem.degree 才能得十进制度数
- 黄道经度须加岁差修正（+23.44° for 1990s）才能得到热带坐标
- 经纬度解析顺序：LOCATION_CACHE 存为 (lat, lon)
