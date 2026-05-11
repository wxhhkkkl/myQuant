# API Contracts: 个股列表与详情模块

**Date**: 2026-05-11

## Convention

- All endpoints return JSON unless `response_class=HTMLResponse` noted.
- Base path prefix: (none, FastAPI router mounted at root)
- Existing endpoints not listed here remain unchanged.

---

## 1. Stock List

### `GET /api/stocks/list`

Returns paginated stock list with sorting.

**Query Parameters**:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | int | 1 | Page number (1-indexed) |
| per_page | int | 50 | Items per page (max 200) |
| sort_by | string | `stock_code` | Sort field: `stock_code`, `latest_price`, `change_pct` |
| sort_order | string | `asc` | `asc` or `desc` |
| keyword | string | (empty) | Search keyword for code/name (optional) |
| watchlist_only | bool | false | Filter to watchlist stocks only |

**Response** (JSON):

```json
{
  "stocks": [
    {
      "stock_code": "000001.SZ",
      "stock_name": "平安银行",
      "latest_price": 11.25,
      "change_pct": 2.35,
      "in_watchlist": true
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 5234,
    "total_pages": 105
  }
}
```

### `GET /api/stocks/search`

(Existed previously, behavior unchanged — returns top 20 matches, no pagination.)

---

## 2. Stock Detail

### `GET /stocks/{code}`

HTML page response. Returns full detail page with stock info header.

### `GET /api/stocks/{code}/kline`

Returns K-line data for chart rendering.

**Query Parameters**:

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| period | string | `daily` | `daily`, `weekly`, `monthly` |
| start | string | 1 year ago | ISO date (YYYY-MM-DD) |
| end | string | today | ISO date (YYYY-MM-DD) |

**Response** (JSON):

```json
{
  "stock_code": "000001.SZ",
  "stock_name": "平安银行",
  "period": "daily",
  "data": [
    {
      "trade_date": "2026-05-11",
      "open": 11.00,
      "high": 11.40,
      "low": 10.90,
      "close": 11.25,
      "volume": 52345678,
      "amount": 589012345
    }
  ]
}
```

### `GET /api/stocks/{code}/quote`

Returns latest market quote snapshot for the detail page.

**Response** (JSON):

```json
{
  "stock_code": "000001.SZ",
  "stock_name": "平安银行",
  "latest_price": 11.25,
  "change_pct": 2.35,
  "change_amount": 0.26,
  "open": 11.00,
  "high": 11.40,
  "low": 10.90,
  "pre_close": 10.99,
  "volume": 52345678,
  "amount": 589012345,
  "snapshot_time": "2026-05-11 14:35:00"
}
```

---

## 3. Watchlist

### `GET /api/watchlist`

(Existing, unchanged — returns full watchlist with stock names.)

### `POST /api/watchlist/add`

(Existing, unchanged — `{"stock_code": "...", "notes": "..."}`)

### `DELETE /api/watchlist/{code}`

(Existing, unchanged)

### `GET /api/watchlist/contains` [NEW]

Batch check watchlist status for multiple codes.

**Query Parameters**:

| Param | Type | Description |
|-------|------|-------------|
| codes | string | Comma-separated stock codes |

**Response** (JSON):

```json
{
  "000001.SZ": true,
  "000002.SZ": false,
  "600000.SH": true
}
```

---

## 4. Data Update

### `POST /api/data/update-stocks`

Triggers background batch update of all stock basic info.

**Response** (JSON):

```json
{
  "status": "started"
}
```

### `GET /api/data/update-stocks/status`

Polls the current update progress.

**Response** (JSON):

```json
{
  "running": true,
  "total": 5234,
  "success": 3210,
  "fail": 2,
  "failed_codes": ["000999.SZ", "002999.SZ"]
}
```

When `running` is `false`, the update has completed (or failed to start).

---

## 5. HTML Component Endpoints (HTMX)

These endpoints return HTML fragments for HTMX partial updates.

### `GET /stocks` (Page)

Returns the full stock list page (rewritten from existing AI选股 page).

### `GET /stocks/table` (Component)

Returns `<table>` fragment for HTMX pagination/sort refresh.

**Query Parameters**: Same as `/api/stocks/list` (page, sort_by, sort_order, keyword, watchlist_only).

### `GET /stocks/{code}/kline-view` (Component)

Returns `<div>` fragment containing ECharts K-line chart container and period selector.

**Query Parameters**: `period` (default: `daily`)

### `GET /stocks/{code}/quote-view` (Component)

Returns `<div>` fragment containing market quote data panel with refresh button.

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Invalid parameters (invalid sort field, bad date range) |
| 404 | Stock not found |
| 503 | Data source unavailable (xtdata offline) |
