# Data Model: 量化交易平台

**Date**: 2026-05-03
**Related**: [spec.md](spec.md), [research.md](research.md)

## Storage Architecture

| 存储 | 用途 | 数据特征 |
|------|------|----------|
| DuckDB (`market.duckdb`) | 行情K线、因子、回测结果 | 大规模时序，列式查询 |
| SQLite (`app.db`) | 元数据、交易记录、策略、日志 | 事务型，频繁小写入 |

---

## DuckDB Tables

### daily_kline — 日线行情

```sql
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
    adj_factor  DOUBLE DEFAULT 1.0,   -- 复权因子
    PRIMARY KEY (trade_date, stock_code)
);
```

索引：`CREATE INDEX idx_kline_code ON daily_kline(stock_code);`

### minute_kline — 分钟线行情（可选，后续扩展）

```sql
CREATE TABLE minute_kline (
    trade_time  TIMESTAMP NOT NULL,
    stock_code  VARCHAR(10) NOT NULL,
    open        DOUBLE,
    high        DOUBLE,
    low         DOUBLE,
    close       DOUBLE,
    volume      BIGINT,
    amount      BIGINT,
    PRIMARY KEY (trade_time, stock_code)
);
```

### model_factors — 模型计算结果缓存

```sql
CREATE TABLE model_factors (
    trade_date   DATE NOT NULL,
    stock_code   VARCHAR(10) NOT NULL,
    model_name   VARCHAR(30) NOT NULL,   -- e.g. 'ma_cross', 'macd', 'rsi'
    factor_name  VARCHAR(30) NOT NULL,   -- e.g. 'ma5', 'ma20', 'signal'
    factor_value DOUBLE,
    PRIMARY KEY (trade_date, stock_code, model_name, factor_name)
);
```

### backtest_results — 回测结果摘要

```sql
CREATE TABLE backtest_results (
    run_id         VARCHAR(36) PRIMARY KEY,   -- UUID
    model_name     VARCHAR(30) NOT NULL,
    model_params   VARCHAR(200),              -- JSON: {"short":5,"long":20}
    stock_code     VARCHAR(10) NOT NULL,
    start_date     DATE NOT NULL,
    end_date       DATE NOT NULL,
    initial_capital DOUBLE NOT NULL,
    final_capital  DOUBLE,
    total_return   DOUBLE,       -- 总收益率
    annual_return  DOUBLE,       -- 年化收益率
    max_drawdown   DOUBLE,       -- 最大回撤
    sharpe_ratio   DOUBLE,       -- 夏普比率
    trade_count    INTEGER,      -- 交易次数
    win_rate       DOUBLE,       -- 胜率
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### backtest_trades — 回测交易明细

```sql
CREATE TABLE backtest_trades (
    id           INTEGER PRIMARY KEY,
    run_id       VARCHAR(36) NOT NULL,       -- FK → backtest_results
    trade_date   DATE NOT NULL,
    trade_type   VARCHAR(4) NOT NULL,        -- 'BUY' | 'SELL'
    price        DOUBLE NOT NULL,
    quantity     INTEGER NOT NULL,
    profit       DOUBLE,                     -- 单笔盈亏
    FOREIGN KEY (run_id) REFERENCES backtest_results(run_id)
);
```

---

## SQLite Tables

### stocks — 股票基础信息

```sql
CREATE TABLE stocks (
    stock_code    VARCHAR(10) PRIMARY KEY,
    stock_name    VARCHAR(50) NOT NULL,
    industry      VARCHAR(50),           -- 申万一级行业
    sub_industry  VARCHAR(50),           -- 申万二级行业
    exchange      VARCHAR(10),           -- 'SH' | 'SZ'
    list_date     DATE,
    is_active     BOOLEAN DEFAULT 1      -- 是否正常上市
);
```

### stock_fundamentals — 基本面快照

```sql
CREATE TABLE stock_fundamentals (
    stock_code     VARCHAR(10) NOT NULL,
    snap_date      DATE NOT NULL,         -- 快照日期
    market_cap     DOUBLE,                -- 总市值(亿)
    pe_ratio       DOUBLE,                -- 市盈率
    pb_ratio       DOUBLE,                -- 市净率
    eps            DOUBLE,                -- 每股收益
    high_52w       DOUBLE,                -- 52周最高
    low_52w        DOUBLE,                -- 52周最低
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (stock_code, snap_date),
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code)
);
```

### financial_reports — 财务报告

```sql
CREATE TABLE financial_reports (
    stock_code        VARCHAR(10) NOT NULL,
    report_period     VARCHAR(7) NOT NULL,   -- '2025Q4', '2025Q3' ...
    revenue           DOUBLE,                -- 营业收入(亿)
    net_profit        DOUBLE,                -- 净利润(亿)
    roe               DOUBLE,                -- ROE(%)
    debt_ratio        DOUBLE,                -- 资产负债率(%)
    eps               DOUBLE,                -- 每股收益
    report_type       VARCHAR(10),           -- '年报', '季报', '半年报'
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (stock_code, report_period),
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code)
);
```

### sentiment_news — 舆情资讯

```sql
CREATE TABLE sentiment_news (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code    VARCHAR(10) NOT NULL,
    title         VARCHAR(500) NOT NULL,
    summary       TEXT,
    source        VARCHAR(100),             -- 来源
    url           VARCHAR(500),
    pub_time      TIMESTAMP NOT NULL,
    sentiment     VARCHAR(10),              -- 'positive' | 'negative' | 'neutral'
    fetched_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code)
);
```

### watchlist — 自选股

```sql
CREATE TABLE watchlist (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code    VARCHAR(10) NOT NULL UNIQUE,
    added_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes         TEXT,
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code)
);
```

### quant_models — 量化模型注册

```sql
CREATE TABLE quant_models (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name      VARCHAR(50) NOT NULL UNIQUE,  -- 'ma_cross', 'macd', 'rsi'
    display_name    VARCHAR(100),                  -- '双均线模型'
    description     TEXT,
    default_params  TEXT,                          -- JSON: {"short":5,"long":20}
    is_active       BOOLEAN DEFAULT 1,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### strategy_configs — 策略配置（用户参数）

```sql
CREATE TABLE strategy_configs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name    VARCHAR(50) NOT NULL,
    config_name   VARCHAR(100),                    -- 用户自定义名称
    params        TEXT NOT NULL,                   -- JSON: {"short":5,"long":20}
    stock_list    TEXT,                            -- JSON: 股票列表
    is_active     BOOLEAN DEFAULT 0,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_name) REFERENCES quant_models(model_name)
);
```

### trade_signals — 交易信号

```sql
CREATE TABLE trade_signals (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code    VARCHAR(10) NOT NULL,
    model_name    VARCHAR(50) NOT NULL,
    signal_type   VARCHAR(4) NOT NULL,             -- 'BUY' | 'SELL'
    signal_price  DOUBLE,
    signal_reason TEXT,
    is_confirmed  BOOLEAN DEFAULT 0,               -- 用户是否确认
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code)
);
```

### orders — 订单记录

```sql
CREATE TABLE orders (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id      VARCHAR(50) UNIQUE,              -- QMT返回的订单编号
    stock_code    VARCHAR(10) NOT NULL,
    order_type    VARCHAR(4) NOT NULL,             -- 'BUY' | 'SELL'
    price         DOUBLE NOT NULL,
    quantity      INTEGER NOT NULL,
    status        VARCHAR(20) DEFAULT 'submitted', -- submitted/partial/filled/cancelled
    signal_id     INTEGER,                         -- FK → trade_signals (NULL if manual)
    submitted_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    filled_at     TIMESTAMP,
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code),
    FOREIGN KEY (signal_id) REFERENCES trade_signals(id)
);
```

### positions — 当前持仓快照

```sql
CREATE TABLE positions (
    stock_code    VARCHAR(10) PRIMARY KEY,
    quantity      INTEGER NOT NULL,
    cost_price    DOUBLE NOT NULL,                 -- 成本价
    current_price DOUBLE,                          -- 现价
    market_value  DOUBLE,                          -- 市值
    profit_loss   DOUBLE,                          -- 浮动盈亏
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code)
);
```

### account_snapshot — 账户快照

```sql
CREATE TABLE account_snapshot (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    snap_time     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_asset   DOUBLE NOT NULL,                 -- 总资产
    market_value  DOUBLE NOT NULL,                 -- 持仓市值
    available_cash DOUBLE NOT NULL,                -- 可用资金
    total_return  DOUBLE                           -- 累计收益率
);
```

### system_logs — 系统日志

```sql
CREATE TABLE system_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    level       VARCHAR(10) NOT NULL,               -- INFO/WARNING/ERROR
    module      VARCHAR(50),                        -- 模块名
    message     TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Entity Relationships

```
stocks ──1:N── daily_kline        (DuckDB)
stocks ──1:N── stock_fundamentals
stocks ──1:N── financial_reports
stocks ──1:N── sentiment_news
stocks ──1:N── watchlist
stocks ──1:N── trade_signals
stocks ──1:N── orders
stocks ──1:1── positions

quant_models ──1:N── strategy_configs
quant_models ──1:N── trade_signals
quant_models ──1:N── backtest_results  (DuckDB)

trade_signals ──1:1── orders (NULLable, manual orders)

backtest_results ──1:N── backtest_trades  (DuckDB)
```

## Data Flow

```
QMT xtdata (主数据源)
  │
  ├──→ DuckDB: daily_kline
  │     (历史行情，首次全量下载+每日增量更新)
  │
  └──→ SQLite: stocks, financial_reports
        (股票列表、行业板块、财务报告)

akshare (补充数据源)
  │
  ├──→ SQLite: stock_fundamentals (PE/PB/市值快照)
  │
  └──→ SQLite: sentiment_news (新闻、公告、舆情)

QMT xttrader (交易)
  │
  ├──→ SQLite: positions, orders, account_snapshot
  │     (持仓、订单、账户)
  │
  └──→ DuckDB: model_factors (可选，实时因子缓存)

FastAPI 后端处理:
  DuckDB daily_kline → 窗口函数计算 MA → model_factors
  model_factors → 双均线交叉信号 → SQLite trade_signals
  trade_signals → 用户确认 → xttrader → orders → positions

回测流程:
  DuckDB daily_kline → pandas 逐日模拟 → backtest_results + backtest_trades
```
