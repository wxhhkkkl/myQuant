# API Contracts: 板块分析模块

**Feature**: 003-sector-analysis | **Date**: 2026-05-14

## Page Routes (返回 HTML)

### GET /sector-analysis
板块分析主页面（三Tab：概览 / 轮动 / 详情）。

**Response**: `pages/sector_analysis.html`
**Context**: `{sectors: [...], last_updated: "2026-05-14 15:30"}`

### GET /sector-analysis/{sector_name}
单个板块详情页。

**Response**: `pages/sector_detail.html`
**Context**: `{sector: {...}, trend_data: {...}, constituents: [...]}`

## API Routes (返回 JSON 或 HTML 片段)

### GET /api/sectors/list
板块概览列表（支持排序）。

**Query Params**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| sort_by | string | heat_rank | 排序字段：heat_rank / valuation_level / change_pct_1w / movement_count_1y |
| sort_order | string | asc | asc / desc |
| time_range | string | 1y | 时间范围：1m / 3m / 6m / 1y |

**Response**: HTML fragment `components/sector_table.html`

### GET /api/sectors/rotation
板块轮动数据。

**Query Params**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| time_range | string | 1y | 时间范围 |
| granularity | string | monthly | monthly / weekly |

**Response**: JSON
```json
{
  "periods": ["2025-06", "2025-07", ...],
  "leaders": [
    {"period": "2025-06", "top3": [{"sector": "电子", "change_pct": 12.5}, ...]},
    ...
  ]
}
```

### GET /api/sectors/{sector_name}/trend
板块趋势K线数据。

**Query Params**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| period | string | daily | daily / weekly / monthly |
| time_range | string | 1y | 时间范围 |

**Response**: JSON (ECharts candlestick format)
```json
{
  "sector_name": "食品饮料",
  "data": [["2026-05-14", 1234.5, 1240.0, 1230.0, 1238.0], ...],
  "stock_count": 120
}
```

### GET /api/sectors/{sector_name}/constituents
板块成分股列表。

**Response**: HTML fragment `components/sector_constituents.html`

### POST /api/sectors/refresh
手动触发板块数据更新。

**Response**: HTML fragment `components/sector_update_status.html`
**Headers**: `HX-Trigger: poll-sector-update`

### GET /api/sectors/refresh/status
查询更新进度。

**Response**: JSON
```json
{
  "running": true,
  "message": "正在计算板块趋势... 15/31",
  "last_updated": null
}
```
完成后返回 `{"running": false, "last_updated": "2026-05-14 15:30:00"}`，并发送 `HX-Trigger: sector-update-done`。
