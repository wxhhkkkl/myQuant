# Research: 板块分析模块

**Feature**: 003-sector-analysis | **Date**: 2026-05-14

## 1. 板块行情识别算法

**Decision**: 扫描板块趋势日K线，识别所有满足"连续涨幅≥10%且持续≥5个交易日"的上涨区间。

**Rationale**: 直接扫描已预计算的板块趋势K线（等权合成），用滑动窗口检测：从每个局部低点开始，累计涨幅直到出现回调>3%或连续2日下跌，记录满足阈值条件的区间。与个股技术分析中的趋势识别方法一致。

**Alternatives considered**:
- 基于成分股分别识别后汇总 → 成分股行情时间不一致，汇总逻辑复杂，且不能反映板块整体趋势
- 基于周K线识别 → 粒度太粗，可能遗漏短期行情

## 2. 板块趋势K线合成

**Decision**: 等权方式——每日取板块内所有成分股的 OHLC 各自求算术平均，生成板块合成K线。日线直接存储，周线/月线从日线聚合。

**Rationale**: 与 spec Assumptions 中的等权方式一致。等权避免了市值加权方式下大市值股票主导板块走势的问题，更能反映板块整体的涨跌情况。周线/月线从日线聚合（与个股K线处理方式一致，见 002-stock-list plan），减少存储冗余。

**Alternatives considered**:
- 市值加权 → 大票主导，掩盖小票动向，与 spec 要求"所有股票价格集合"不符
- 实时计算 → 性能不可接受（5200只股票 × 250个交易日），必须预计算

## 3. 热度排名公式

**Decision**: `热度 = 近一周涨跌幅 × 0.4 + 成交量环比变化率 × 0.3 + 成分股上涨比例 × 0.3`

**Rationale**: 与 spec Assumptions 中的权重一致。涨跌幅权重最高（0.4）反映价格趋势，成交量变化和上涨广度各占 0.3 确保综合考量。成交量环比 = (本周日均量 - 上周日均量) / 上周日均量。成分股上涨比例 = 板块内本周收涨的股票数 / 总股票数。

**Alternatives considered**: 无——权重已在 spec 中明确定义。

## 4. 估值分位计算

**Decision**: 三等分法——将所有板块按 PE 中位数排名，前 1/3 为"高估"，中 1/3 为"适中"，后 1/3 为"低估"。PE 中位数 = 板块内所有成分股 PE 的中位数（排除无 PE 数据的股票）。

**Rationale**: 与 clarify Q5 的答案一致。三等分法简单透明，不依赖历史分位数据，用户容易理解。31 个板块三等分约每档 10 个板块。

**Alternatives considered**: 历史分位法（每个板块与自身历史 PE 比较）→ 需要长期历史 PE 数据，且新上市板块无法计算；绝对值法（PE<15/15-30/>30）→ 不适用于 A 股市场行业间 PE 差异大的特点。

## 5. 数据存储策略

**Decision**: 板块趋势K线存入 DuckDB `sector_trend` 表（与 `daily_kline` 同级）；板块快照（热度、估值分位、行情次数、更新时间）存入 SQLite `sector_snapshot` 表。

**Rationale**: DuckDB 天然适合时序数据（date-based 查询、聚合），`sector_trend` 与 `daily_kline` 同为日线级别数据，放同一存储引擎减少跨库查询。SQLite 的 `sector_snapshot` 是元数据/快照，与 `stock_fundamentals` 等元数据表同级，单行查询性能足够。

**Alternatives considered**: 全部放 SQLite → 板块趋势K线数据量大（31板块 × 250天 × N年），SQLite 时序聚合性能不如 DuckDB；全部放 DuckDB → DuckDB 单进程锁问题在更新时需要停止应用，快照数据放 SQLite 可避免此问题。

## 6. 轮动时间线前端实现

**Decision**: 使用 ECharts 热力图或自定义时间线组件，每月/周显示涨幅前 3 的板块名称和涨幅。

**Rationale**: 项目已使用 ECharts 渲染K线图（见 `stock_kline.html`），轮动图同样适合用 ECharts 渲染。热力图模式色块表示涨幅高低，直观展示板块轮动节奏。用户点击某时间节点时，HTMX 加载该节点详情。

**Alternatives considered**: 纯 HTML 表格 → 交互性差，不直观；Plotly → 新增依赖，与现有 ECharts 栈不一致。

## 7. 后台计算任务模式

**Decision**: 复用已有的 `threading.Thread` + 模块级状态 dict + HTMX 轮询模式。

**Rationale**: 与 `data_service.py` 中的 `run_stock_update()` 和 `run_kline_update()` 模式完全一致。API 端点 POST `/api/sectors/refresh` 启动线程执行 `compute_sectors.download_all()`，前端每 2 秒轮询 `GET /api/sectors/refresh/status`，完成后触发 HTMX 局部刷新。

**Alternatives considered**: APScheduler 定时任务 → spec clarify Q3 明确手动触发，不需要定时；Celery/Redis → 过度设计，单用户本地应用不需要消息队列。
