# Research: 量化交易平台技术决策

**Date**: 2026-05-03
**Related**: [plan.md](plan.md)

## 1. 数据存储：DuckDB + SQLite 双库架构

### Decision

- **DuckDB**：所有大规模时序数据（K线、因子计算结果、回测结果）
- **SQLite**：元数据与事务数据（自选股列表、策略参数、交易记录、系统日志）

### Rationale

DuckDB 列式存储引擎专为 OLAP 设计，对时序聚合查询（MA计算、因子扫描）速度比 SQLite 快 10-50 倍。
SQLite 更适合频繁的小事务写入（交易记录、日志追加），且 Python 标准库自带，零依赖。

两者均为进程内嵌入式数据库，无需独立服务进程——契合 Constitution II（Simplicity First）原则，避免为个人工具引入数据库运维复杂度。

### Key Design Decisions

| 决策 | 选择 | 原因 |
|------|------|------|
| K线表结构 | 单表 `daily_kline`，按 `(trade_date, stock_code)` 索引 | 列式引擎适合单表；分表需 UNION 且元数据管理复杂 |
| MA指标计算 | DuckDB 原生窗口函数 | `AVG() OVER (ROWS BETWEEN N PRECEDING)` 一次 SQL 完成，无需 Python 循环 |
| 回测计算 | DuckDB 加载+筛选 → pandas 逐日模拟 | DuckDB 擅长向量化聚合，pandas 擅长逐行状态机（回测） |
| 文件管理 | `market.duckdb`（行情）+ `app.db`（SQLite） | 按用途分离，行情数据可独立重建 |
| FastAPI 并发 | DuckDB 只读连接（`read_only=True`），独立写入进程 | DuckDB 支持多读单写，读操作间无锁竞争 |

### Alternatives Considered

- **纯 pandas**: 5000只股票×10年数据内存不足，且每次重启需重新加载
- **PostgreSQL/TimescaleDB**: 需要独立服务进程，违反简单原则
- **全用 SQLite**: 时序聚合性能不足，回测5秒目标无法保证

## 2. A股数据源：QMT xtdata 为主 + akshare 补充

### Decision

**主力数据源**: QMT xtdata（历史K线、财务报表、板块分类、股票列表）
**补充数据源**: akshare（估值指标 PE/PB/市值快照、新闻舆情）

### Rationale

用户要求数据源优先使用 QMT 自带数据。实测 xtdata 覆盖能力如下：

| 数据维度 | xtdata 覆盖 | 说明 |
|----------|------------|------|
| K线（日/周/月） | ✅ 完整 | `get_market_data()` + `download_history_data()` |
| 财务报表 | ✅ 完整 | `get_financial_data()` 覆盖利润表/资产负债表/现金流等8类 |
| 板块分类 | ✅ 完整 | `get_sector_list()` 申万SW1/SW2/SW3 + 概念 + 地域 |
| 股票列表 | ✅ 完整 | `get_stock_list_in_sector("沪深A股")` |
| 估值指标（PE/PB/PS） | ❌ 缺失 | 无现成接口，需自行用行情价÷财务数据推算 |
| 新闻舆情 | ❌ 缺失 | 无原生新闻API |

akshare 精准填补两个缺口：`stock_zh_a_spot_em()` 获取实时 PE/PB/市值，`stock_news_em()` 获取个股新闻舆情。

### Data Source Routing

```python
# 各数据模块使用不同来源
K线 & 财务 & 板块 → xtdata (QMT)
PE/PB/市值快照     → akshare (每日刷新缓存)
新闻舆情           → akshare (按需拉取)
```

### Mitigation

- xtdata 历史数据首次下载耗时较长（全市场~30min），需在初始化脚本中批量执行
- akshare 基于网络抓取，对估值和舆情调用添加重试机制（3次，指数退避）
- 所有数据采集后立即存入 DuckDB/SQLite 本地缓存

### Alternatives Considered

| 方案 | 拒绝原因 |
|------|----------|
| 全用 akshare | 用户要求优先使用 QMT 数据，且 xtdata 财务/板块数据质量更高 |
| 全用 xtdata | PE/PB/舆情无法覆盖，spec 明确要求这些数据 |
| tushare/baostock 补充 | 增加依赖，akshare 一个库即可补齐缺口 |

## 3. 实盘交易：国金证券 QMT + xtquant

### Decision

通过 **xtquant SDK** 连接国金证券 QMT 客户端执行实盘交易。FastAPI 中封装 `run_in_executor()` 线程池调用同步 API。

### Rationale

xtquant 是 QMT 官方 Python SDK，提供完整的行情订阅和交易执行 API。项目 spec 已确定国金证券为交易券商。

### Key Design Decisions

| 决策 | 选择 | 原因 |
|------|------|------|
| 行情数据 | 回测+实盘统一用 xtdata（历史K线）+ DuckDB 缓存；实时行情用 xtdata 订阅 | 数据源统一，减少不一致性 |
| 交易 API 封装 | 全部 xttrader 调用放入 `ThreadPoolExecutor` | xtquant 同步阻塞，直接调用会阻塞 FastAPI 事件循环 |
| 连接管理 | 连接管理器（ConnectionManager）单例，带心跳+自动重连 | QMT TCP 长连接可能超时断开 |
| 部署要求 | QMT 客户端必须保持运行，FastAPI 同机部署 | xtquant 通过 localhost TCP 通信，不可远程 |

### Known Limitations

- 实时订阅上限（建议≤20只，与 spec SC-008 一致）
- 非交易时段不可下单/撤单
- xtquant 版本需与 QMT 客户端版本匹配
- 历史数据需预先下载到本地缓存

### Alternatives Considered

- **其他券商 SDK**: 已在 spec 阶段确定国金证券
- **直接调用交易所 API**: 个人不可用
- **模拟交易替代**: 作为 Phase 1 实现，先通过模拟盘验证策略再切实盘

## 4. 前端架构：FastAPI + Jinja2 + HTMX + Alpine.js + Tailwind CSS

### Decision

采用服务端渲染（SSR）为主、Alpine.js 轻量客户端增强的混合架构。

### Rationale

量化平台的核心交互（数据查询、图表展示、表单操作）天然适合服务端驱动的架构：
- HTMX 通过 HTML 属性实现 AJAX 局部更新，无手写 JS
- Alpine.js 处理极少量客户端交互（下拉菜单、模态框、图表切换），代码量<100行
- Tailwind CSS 消除手写 CSS 文件
- 无 Node.js 构建步骤，无 SPA 框架

完全契合 Constitution II（Simplicity First）。

### Key Design Decisions

| 决策 | 选择 | 原因 |
|------|------|------|
| 图表渲染 | ECharts（CDN引入） | K线图、收益曲线等金融图表支持完善 |
| 实时数据更新 | HTMX polling + Alpine.js 定时器 | SSE/WebSocket 对个人工具过度设计 |
| 页面组织 | Jinja2 模板继承（base.html → pages/components） | 复用布局，HTMX 返回组件片段 |
| 静态资源 | Tailwind standalone CLI，无 Node 依赖 | CDN 引入，本地编译一次即可 |

## 5. AI 选股方案

### Decision

采用**规则引擎 + LLM 分析**的组合方案。规则引擎做初筛（PE/PB 范围、ROE 阈值、均线趋势），LLM API 做多维度综合评分和推荐理由生成。

### Rationale

- 纯 LLM 选股准确性和可解释性不足
- 纯规则引擎缺乏灵活性
- 组合方案：规则确保底线（定量），LLM 提供洞察（定性）

### Implementation

- 规则引擎定义可配置的筛选条件（估值、成长、技术指标）
- LLM 调用 **DeepSeek API** 对筛选结果的财务、舆情、板块数据做综合分析
- 每只推荐股票附带具体的推荐理由（来自 LLM 分析）

## 6. 其他技术决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 技术指标计算 | TA-Lib | C 扩展，成熟稳定，覆盖全部常见指标 |
| HTTP 客户端 | httpx | 异步支持，用于 akshare 补充数据拉取和外部 API |
| 任务调度 | APScheduler | 定时数据采集、信号扫描，无 Celery 复杂度 |
| 日志 | Python logging → SQLite | 结构化存储，便于查询和审计 |
