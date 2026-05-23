# 更新日志

本文件记录 **OpenMobius-skill** 的版本变更。
格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

English: [CHANGELOG.md](./CHANGELOG.md)

---

## [0.2.0] — 2026-05-23

### ✨ 功能更新

1. **SMC 结构指标作为默认行情分析源。** 发起行情查询时，自动获取完整
   结构信号（BOS/CHoCH 事件、Order Block、Fair Value Gap、Equal H/L
   流动性、Premium/Discount 区域、Strong/Weak Pivot 标签），不再调用
   通用技术指标。

2. **行情图全自动绘制。** 结构层（Order Block、Fair Value Gap、
   BOS/CHoCH、关键水平等）全部由系统自动叠加到图上，模型不再手画
   坐标，速度更快、不会画错。

3. **新增成交量子面板。** 行情图底部增加成交量柱状图，K 线红绿配色。

4. **TradingView 风格图表。** 浅色主题为默认；bear Order Block 浅粉、
   bull Order Block 浅蓝；BOS/CHoCH 标签彩色显示，视觉风格对齐主流
   交易平台。

5. **数据新鲜度强制声明。** 每次行情回复必须包含"数据时点 + 拉取时刻
   + K 线年龄"，数据延迟时自动加 ⚠️ 提醒。

6. **数据源问题标准化回答。** 用户问"数据从哪来 / 是不是实时"时，
   统一走固定模板（Mobius Quant API），杜绝编造来源。

7. **知识库扩容。** 从 380 概念 + 584 案例 → **665 概念 + 1,246
   案例**。CHoCH、Strong/Weak Pivot、Protected High-Low 等 SMC 核心
   概念现在都有专门卡片支撑。

### 🎨 体验优化

1. **不再凭记忆答行情。** 用户问"BTC 怎么样"（不说"现在"也算），
   系统强制实时拉数据，避免回复过期价或训练知识里的旧数字。

2. **不再列具体指标名诱导。** 描述与示例中出现的通用技术指标名全部
   移除，让模型不会"主动想到"去拉这些。

3. **K 线默认数量：200 → 300。** 给 SMC 长周期计算留更充分的数据
   窗口，结构判读更稳定。

4. **图表标签更克制。** 右轴只保留关键价位（Strong High / Weak
   Low / 入场 / 止损 / 止盈）；Order Block 与 Fair Value Gap 直接
   画矩形不挤标签，整体更清爽。

5. **`--trade-setup` 简化用户级标注。** 模型只需写 entry/SL/target
   三条线的 JSON 文件，结构叠加层自动合并。

### 🐛 BUG 处理

1. **平台描述超长被截断。** claude-code yaml 描述超过 1,024 字符
   上限，导致 Codex 等平台拒绝加载或截断 skill，已精简到合规长度。

2. **图表标记互相覆盖。** 之前画多组 marker（BOS、CHoCH、EQH 等）
   时只显示最后一组，已修复为全部累积显示。

3. **图表偶发渲染崩溃。** 某些场景下传入空时间戳会导致图表整个
   挂掉，已加防御。

4. **K 线被压缩成一小段。** 当历史结构事件超出可见 K 线范围时，
   时间轴自动拉飞导致 K 线挤在角落，已修复时间裁剪逻辑。

5. **成交量柱无法区分红绿。** 之前成交量是单一颜色，已支持按 K 线
   涨跌染色。

6. **图表元素被错误截断。** 默认上限太低导致部分 Order Block /
   Fair Value Gap 不显示，已调高到合理上限。

7. **SMC 区域数据缺失。** 调指标时漏传参数导致 Premium / Discount /
   Equilibrium 区域不返回，已自动补齐。

---

## [0.1.0] — 2026-05-13

- 首发版本：从 130 个 ICT/SMC 教学视频萃取 380 概念 + 584 案例；
  四种交互模式（概念问答、图表分析、图表标注、K 线分析）；通过
  Playwright + lightweight-charts 生成行情图。
