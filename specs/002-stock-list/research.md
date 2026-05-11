# Research: 个股列表与详情模块

**Date**: 2026-05-11
**Related**: [plan.md](plan.md)

## 1. 周K/月K线数据来源

### Decision

不创建独立的 `weekly_kline` / `monthly_kline` 表，通过 DuckDB 聚合查询从 `daily_kline` 实时派生。

### Rationale

DuckDB 的列式引擎对聚合查询具有天然优势，`GROUP BY` + 窗口函数可在毫秒级完成周/月K线计算。预先创建独立表会引入数据冗余和同步维护负担，违反 Simplicity First 原则。

周K聚合方式：按 ISO week (`extract('isoyear' FROM trade_date) || '-W' || extract('week' FROM trade_date)`) 分组。
月K聚合方式：按年-月 (`strftime(trade_date, '%Y-%m')`) 分组。

```sql
-- 周K示例：从日K聚合
SELECT
    date_trunc('week', trade_date)::DATE AS trade_date,
    stock_code,
    FIRST(open ORDER BY trade_date) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close ORDER BY trade_date) AS close,
    SUM(volume) AS volume,
    SUM(amount) AS amount
FROM daily_kline
WHERE stock_code = ? AND trade_date BETWEEN ? AND ?
GROUP BY date_trunc('week', trade_date), stock_code
ORDER BY trade_date
```

注意：`date_trunc('week', ...)` 在 DuckDB 中以周一为周起始（ISO 标准），与中国A股习惯一致。

### Alternatives Considered

- **预建周K/月K表**: 冗余、需维护同步逻辑、浪费存储空间
- **Python 端 pandas resample**: 需传输全部日K数据到应用层，内存开销大

## 2. 行情快照数据获取

### Decision

个股列表使用 DuckDB `daily_kline` 最新一行 + SQLite `stocks` 表 JOIN 获取最新价和涨跌幅。详情页行情数据优先使用 xtdata `get_market_data()` 获取当日实时快照，降级到最新日K线收盘数据。

### Rationale

- **列表场景**：5000只股票无法逐个调用 xtdata 实时行情（QMT限频），用最新日K收盘价作为列表行情数据即可满足"浏览"场景。
- **详情页场景**：单只股票可调用 xtdata 获取准实时数据，用户手动刷新时触发。
- **涨跌幅计算**：`(最新价 - 昨收) / 昨收 * 100`，昨收为前一日 `close`。

列表查询 SQL：
```sql
WITH latest AS (
    SELECT stock_code, close, trade_date,
           ROW_NUMBER() OVER (PARTITION BY stock_code ORDER BY trade_date DESC) AS rn
    FROM daily_kline
)
SELECT s.stock_code, s.stock_name, l.close,
       LAG(l.close) OVER (PARTITION BY s.stock_code ORDER BY l.trade_date) AS prev_close
FROM stocks s
LEFT JOIN latest l ON s.stock_code = l.stock_code AND l.rn = 1
WHERE s.is_active = 1
```

xtdata 实时行情获取（详情页）：
```python
# xtdata.get_market_data() 获取最新 tick 快照
data = xtdata.get_market_data(
    field_list=['open', 'high', 'low', 'lastClose', 'lastPrice',
                'volume', 'amount', 'pvolume'],
    stock_list=[code],
    period='1d',
    start_time='',
    count=2
)
```

### Alternatives Considered

- **akshare 实时行情**: 需网络请求，延迟高，xtdata 本地接口更快
- **全量 xtdata 轮询列表**: QMT 接口限频严重，5000只逐个查询不可行

## 3. 列表分页与排序策略

### Decision

服务端分页 + 数据库层排序。使用 SQLite `LIMIT/OFFSET` + `ORDER BY`，支持按代码、最新价、涨跌幅排序。

### Rationale

5000只股票全量返回前端再排序分页会浪费带宽和内存。服务端分页每次仅传输当前页约50条数据，HTMX 通过 `hx-get` + `hx-trigger` 实现无刷新翻页和排序切换。

排序字段映射：
- 代码 → `stock_code`
- 最新价 → `latest_price`（需要子查询JOIN）
- 涨跌幅 → `change_pct`（计算字段，需子查询）

性能考量：5000行数据在 SQLite 中带 JOIN 和 ORDER BY 的查询应在 100ms 内完成。最新价和涨跌幅排序需在 DuckDB 侧计算后回填 SQLite，或直接全部用 DuckDB 做列表查询。

**选择方案**：列表数据全部从 DuckDB 查询（因行情数据在 DuckDB），SQLite 仅提供股票基础信息。DuckDB 可以通过 `ATTACH` 语句关联 SQLite 表进行跨库 JOIN。

### Alternatives Considered

- **前端排序**: 5000条全量传输不可接受
- **ElasticSearch/Meilisearch**: 引入外部服务，过度设计

## 4. 批量更新基础信息机制

### Decision

复用现有 `init_data.py` 中的 `download_stock_list()` 逻辑（xtdata `get_stock_list_in_sector("沪深A股")` + 行业信息），封装为可被 API 调用的 service 函数。采用后台线程执行 + 状态查询模式。

### Rationale

- 现有 `init_data.py` 已验证 xtdata 股票列表下载路径可用
- 5000只股票更新约需 30-60 秒（主要耗时在 xtdata 逐个查行业信息）
- 个人工具无需消息队列，APScheduler 或 `threading.Thread` 即可

实现方案：
1. API 端点 `POST /api/data/update-stocks` 触发后台任务
2. 后台线程执行更新，写入进度到 SQLite `system_logs` 表（或内存状态变量）
3. 前端 HTMX polling 显示进度状态条
4. 完成后返回成功/失败统计

```python
import threading

_update_status = {"running": False, "total": 0, "success": 0, "fail": 0}

def run_stock_update():
    _update_status["running"] = True
    stocks = xtdata.get_stock_list_in_sector("沪深A股")
    _update_status["total"] = len(stocks)
    for code, name in stocks:
        try:
            industry = xtdata.get_instrument_detail(code).get("Industry", "")
            Stock.upsert(code, name, industry=industry, ...)
            _update_status["success"] += 1
        except Exception:
            _update_status["fail"] += 1
    _update_status["running"] = False
```

### Alternatives Considered

- **Celery/RQ 任务队列**: 个人单机工具不需要消息队列
- **同步阻塞执行**: 60秒的HTTP请求会超时，用户无法看到进度

## 5. K线图渲染方案

### Decision

使用 ECharts (已在 `base.html` 中通过 CDN 引入) 渲染 K 线图。服务端返回 JSON 数据，前端 Alpine.js 初始化 ECharts 实例并绑定数据。

### Rationale

- ECharts 原生支持 `candlestick` 类型（K线图），自带缩放、十字光标、tooltip 等交互
- 已在项目 `base.html` 中引入，零额外依赖
- 周K/月K切换通过 Alpine.js 事件触发 API 请求，获取对应周期的 JSON 数据后更新图表

交互流程：
1. 详情页加载 → 默认获取近一年日K JSON → ECharts 渲染
2. 用户点击"周K"/"月K"→ 请求对应周期聚合数据 → 图表 `setOption()` 更新
3. 用户点击"刷新行情"→ 请求最新行情 JSON → 更新行情面板 DOM

### Alternatives Considered

- **Chart.js + financial plugin**: K线支持不如 ECharts 成熟
- **Lightweight Charts (TradingView)**: 更专业的金融图表，但需额外引入库
- **服务端渲染静态图片 (matplotlib)**: 无交互，不符合预期
