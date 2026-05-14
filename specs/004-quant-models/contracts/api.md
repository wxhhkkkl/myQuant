# API Contracts: 量化模型模块

## Page Routes

### GET /models
Existing. Renders model library page with card grid.

**Response**: HTML (pages/models.html)

### GET /models/{model_name}
**New**. Renders model detail page with intro, config form, chart area, stats.

**Response**: HTML (pages/model_detail.html)
**Context**: `{model_name, model, config_saved}`

---

## Data API Routes

### GET /api/models
Existing. Returns list of active models.

**Response**: JSON `[{id, model_name, display_name, description, default_params, ...}]`

### GET /api/models/{model_name}/detail
**New**. Returns model metadata + current config if exists.

**Response**: JSON
```json
{
  "model": {"model_name": "ma_cross", "display_name": "双均线模型", "description": "...", "default_params": {...}},
  "config": {"stock_code": "...", "params": {...}, "position_pct": 100, "time_range": "1y"} | null
}
```

### POST /api/models/{model_name}/signals
**New**. Generate MA cross signals for configured stock and time range.

**Request Body**: JSON
```json
{
  "stock_code": "000001.SZ",
  "short": 5,
  "long": 20,
  "position_pct": 50,
  "time_range": "1y"
}
```

**Validation**:
- `short` < `long`, both positive integers
- `position_pct` 1–100
- `stock_code` exists in stocks table

**Response**: JSON
```json
{
  "kline": [[date, open, close, low, high], ...],
  "ma_short": [[date, value], ...],
  "ma_long": [[date, value], ...],
  "signals": [{"trade_date": "...", "signal_type": "BUY", "signal_price": 12.34}, ...],
  "performance": {
    "total_signals": 15,
    "trade_pairs": 7,
    "win_rate": 57.1,
    "cumulative_return": 12.5
  }
}
```

### PUT /api/models/{model_name}/config
**New**. Save user configuration.

**Request Body**: JSON
```json
{
  "stock_code": "000001.SZ",
  "params": {"short": 5, "long": 20},
  "position_pct": 50,
  "time_range": "1y"
}
```

**Response**: JSON `{"status": "ok"}`

### GET /api/stocks/search?q=xxx
Existing (from stocks router). Used for stock picker autocomplete.

**Response**: JSON `[{stock_code, stock_name}, ...]`
