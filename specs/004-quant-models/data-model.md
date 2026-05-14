# Data Model: 量化模型模块

## Existing Entities (Extended)

### quant_models (SQLite)

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| model_name | VARCHAR(50) UNIQUE | Internal identifier, e.g. "ma_cross" |
| display_name | VARCHAR(100) | Display name, e.g. "双均线模型" |
| description | TEXT | Model logic explanation |
| default_params | TEXT (JSON) | Default parameters: `{"short": 5, "long": 20, "position_pct": 100}` |
| is_active | BOOLEAN | 1 = active |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

**Seed data**: Register `ma_cross` model on startup if not exists.

### strategy_configs (SQLite) — EXTENDED

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| model_name | VARCHAR(50) FK | References quant_models.model_name |
| config_name | VARCHAR(100) | Optional user-given name |
| stock_code | VARCHAR(10) | **NEW**: Single stock code for analysis |
| params | TEXT (JSON) | User-configured params: `{"short": 5, "long": 20}` |
| position_pct | INTEGER | **NEW**: Position size 1-100 (default 100) |
| time_range | VARCHAR(5) | **NEW**: "1m"/"3m"/"6m"/"1y" (default "1y") |
| is_active | BOOLEAN | 1 = active config |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

**Validation rules**:
- `short` < `long` (both positive integers)
- `position_pct` between 1 and 100
- `stock_code` must exist in stocks table

### trade_signals (SQLite) — EXTENDED

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| stock_code | VARCHAR(10) | Stock symbol |
| model_name | VARCHAR(50) | Model identifier |
| config_id | INTEGER | **NEW**: FK to strategy_configs.id |
| trade_date | VARCHAR(10) | **NEW**: Signal date YYYY-MM-DD |
| signal_type | VARCHAR(10) | "BUY" or "SELL" |
| signal_price | REAL | Close price at signal date |
| signal_reason | TEXT | e.g. "MA5上穿MA20" / "MA5下穿MA20" |
| is_confirmed | INTEGER | 0 = pending, 1 = confirmed |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

## Read-Only Data Sources

### daily_kline (DuckDB)

Used for MA computation. Columns: stock_code, trade_date, open, high, low, close, volume.

### stocks (SQLite)

Used for stock picker. Columns: stock_code, stock_name, industry, is_active.

## Entity Relationships

```
quant_models (1) ──< (N) strategy_configs ──< (N) trade_signals
     │                       │
     │                  stock_code ────> stocks.stock_code
     │
     └── model_name is the join key
```

## State Transitions

- **trade_signals**: `is_confirmed = 0` (pending) → `is_confirmed = 1` (confirmed via backtest/trading module)
- **strategy_configs**: `is_active = 1` (active) → `is_active = 0` (inactive when user changes config)
