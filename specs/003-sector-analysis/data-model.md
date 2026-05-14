# Data Model: 板块分析模块

**Feature**: 003-sector-analysis | **Date**: 2026-05-14

## Entity-Relationship

```
┌─────────────────┐     ┌──────────────────────┐
│   stocks (现有)   │     │  sector_trend (NEW)   │
│   SQLite         │     │  DuckDB              │
├─────────────────┤     ├──────────────────────┤
│ stock_code PK    │────▶│ sector_name      PK   │
│ stock_name       │     │ trade_date       PK   │
│ industry         │     │ open                  │
│ ...              │     │ high                  │
└─────────────────┘     │ low                   │
                        │ close                 │
                        │ stock_count           │
                        └──────────────────────┘

┌──────────────────────────┐
│ sector_snapshot (NEW)     │
│ SQLite                    │
├──────────────────────────┤
│ sector_name          PK   │
│ snap_date                 │
│ pe_median                 │
│ valuation_level           │
│ movement_count_1y         │
│ heat_score                │
│ heat_rank                 │
│ change_pct_1w             │
│ vol_change_pct            │
│ up_ratio                  │
│ constituent_count         │
│ trend_available           │
└──────────────────────────┘
```

**Relationship**: `stocks.industry` → `sector_snapshot.sector_name` (logical FK). Stock classification follows Shenwan first-level industry stored in existing `stocks.industry` column.

## Tables

### 1. sector_trend (DuckDB — 新建)

板块趋势K线，日线级别。周线/月线从日线动态聚合。

| Column | Type | Description |
|--------|------|-------------|
| sector_name | VARCHAR | 申万一级行业名称 (PK) |
| trade_date | DATE | 交易日 (PK) |
| open | DOUBLE | 板块合成开盘价（成分股等权均值） |
| high | DOUBLE | 板块合成最高价 |
| low | DOUBLE | 板块合成最低价 |
| close | DOUBLE | 板块合成收盘价 |
| stock_count | INTEGER | 当日有K线数据的成分股数量 |

**Primary Key**: `(sector_name, trade_date)`
**Index**: `trade_date` (for range queries)

**DDL**:
```sql
CREATE TABLE IF NOT EXISTS sector_trend (
    sector_name VARCHAR NOT NULL,
    trade_date DATE NOT NULL,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    stock_count INTEGER,
    PRIMARY KEY (sector_name, trade_date)
);
```

### 2. sector_snapshot (SQLite — 新建)

板块当前快照，存储最近一次计算的估值、热度、行情统计。

| Column | Type | Description |
|--------|------|-------------|
| sector_name | VARCHAR | 申万一级行业名称 (PK) |
| snap_date | DATE | 计算日期 |
| pe_median | DOUBLE | 成分股PE中位数 |
| valuation_level | VARCHAR | 估值分位：高估/适中/低估（三等分法） |
| movement_count_1y | INTEGER | 近一年行情次数（≥10%涨幅 + ≥5天） |
| heat_score | DOUBLE | 热度综合评分 |
| heat_rank | INTEGER | 热度排名（1=最热） |
| change_pct_1w | DOUBLE | 近一周涨跌幅（%） |
| vol_change_pct | DOUBLE | 成交量环比变化率（%） |
| up_ratio | DOUBLE | 近一周成分股上涨比例（0-1） |
| constituent_count | INTEGER | 成分股数量 |
| trend_available | INTEGER | 趋势数据是否可用（0/1） |

**Primary Key**: `sector_name`

**DDL**:
```sql
CREATE TABLE IF NOT EXISTS sector_snapshot (
    sector_name VARCHAR PRIMARY KEY,
    snap_date DATE,
    pe_median DOUBLE,
    valuation_level VARCHAR(10),
    movement_count_1y INTEGER DEFAULT 0,
    heat_score DOUBLE DEFAULT 0,
    heat_rank INTEGER,
    change_pct_1w DOUBLE,
    vol_change_pct DOUBLE,
    up_ratio DOUBLE,
    constituent_count INTEGER DEFAULT 0,
    trend_available INTEGER DEFAULT 0
);
```

## State Transitions

`sector_snapshot` 无复杂状态机，生命周期简单：

```
[不存在] → 首次 compute_sectors → [trend_available=1, snap_date=今日]
                                           ↓
                              再次 compute_sectors → [snap_date=更新]
                                           ↓
                              成分股全部退市/无数据 → [trend_available=0, constituent_count=0]
```

## Validation Rules

1. `sector_name` 必须是 `stocks.industry` 中存在的申万一级行业名称（31个预定义值）
2. `valuation_level` 仅允许三个值：`高估`、`适中`、`低估`
3. `movement_count_1y` ≥ 0
4. `heat_score` ≥ 0
5. `up_ratio` ∈ [0, 1]
6. `sector_trend.stock_count` ≥ 1（至少需要一只成分股才能合成）

## Data Sources

- `sector_trend`: 聚合自 DuckDB `daily_kline`（日线OHLC等权均值）
- `sector_snapshot.pe_median`: 聚合自 SQLite `stock_fundamentals.pe_ratio`
- `sector_snapshot.heat_score` 各分量: 聚合自 `daily_kline` 近一周 OHLC/volume
- `sector_snapshot.movement_count_1y`: 扫描 `sector_trend` 日线识别行情
