# Data Model: 个股列表与详情模块

**Date**: 2026-05-11
**Related**: [spec.md](spec.md), [research.md](research.md)

## Overview

本模块**不新增数据表**。所有数据模型已在 `001-quant-trading-platform` 中定义。以下文档说明各实体在本模块中的使用方式及查询扩展。

## Existing Entities Used

### Stock (SQLite `stocks`)

已有表结构完整覆盖需求，无需变更。

```sql
-- 已存在
CREATE TABLE stocks (
    stock_code    VARCHAR(10) PRIMARY KEY,
    stock_name    VARCHAR(50) NOT NULL,
    industry      VARCHAR(50),
    sub_industry  VARCHAR(50),
    exchange      VARCHAR(10),
    list_date     DATE,
    is_active     BOOLEAN DEFAULT 1
);
```

**本模块新增查询方法**：
- `Stock.list_paginated(page, per_page, sort_by, sort_order)` — 分页+排序查询
- `Stock.count_all()` — 总数统计（分页用）
- `Stock.count_search(keyword)` — 搜索结果计数（分页用）

### Watchlist (SQLite `watchlist`)

```sql
-- 已存在
CREATE TABLE watchlist (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code    VARCHAR(10) NOT NULL UNIQUE,
    added_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes         TEXT,
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code)
);
```

**本模块新增查询方法**：
- `Watchlist.contains_batch(codes)` — 批量查询自选状态（用于列表页标记"已自选"按钮）

### DailyKline (DuckDB `daily_kline`)

```sql
-- 已存在
CREATE TABLE daily_kline (
    trade_date  DATE NOT NULL,
    stock_code  VARCHAR(10) NOT NULL,
    stock_name  VARCHAR(20),
    open        DOUBLE,
    high        DOUBLE,
    low         DOUBLE,
    close       DOUBLE,
    volume      BIGINT,
    amount      BIGINT,
    adj_factor  DOUBLE DEFAULT 1.0,
    PRIMARY KEY (trade_date, stock_code)
);
```

**本模块新增查询视图（非物化，实时聚合）**：

- `get_weekly_kline(code, start, end)` — DuckDB SQL 聚合周K
- `get_monthly_kline(code, start, end)` — DuckDB SQL 聚合月K
- `get_latest_quotes(codes, limit)` — 批量获取最新行情快照（用于列表页价格显示）

## Entity Relationships

```
stocks ──1:N── daily_kline    (DuckDB, 行情&K线)
stocks ──1:1── watchlist      (自选股关系)
```

## Data Flow (本模块新增)

```
QMT xtdata (行情快照)
  │
  └──→ API /api/stocks/{code}/quote
        (单只股票手动刷新获取最新行情)

DuckDB daily_kline
  │
  ├──→ API /api/stocks/{code}/kline?period=daily
  │     (日K线 JSON → ECharts 渲染)
  │
  ├──→ 聚合查询 → 周K/月K JSON
  │     (/api/stocks/{code}/kline?period=weekly|monthly)
  │
  └──→ 列表行情查询
        (最新收盘价 + 涨跌幅 → 个股列表表格)

QMT xtdata (股票列表)
  │
  └──→ API POST /api/data/update-stocks
        (批量更新 stocks 表基础信息，后台线程执行)
```

## State Transitions

### Stock 交易状态

```
正常上市 (is_active=1) → 暂停上市 → 退市 (is_active=0)
                              ↓
                         恢复上市 (is_active=1)
```

退市股票在列表中标记为"已退市"状态，不直接隐藏。

### 批量更新状态

```
IDLE → RUNNING (显示进度条) → COMPLETED (显示结果摘要)
                              ↘ FAILED (显示错误信息)
```
