# Trading API Contracts

**Feature**: 005-trading-model-execution
**Date**: 2026-05-15

## Endpoints

### 模型实例管理

#### GET /api/trading/models

获取所有可用模型及其运行状态。

**Response** (JSON):
```json
[
  {
    "model_name": "ma_cross",
    "display_name": "双均线模型",
    "description": "基于快慢均线交叉信号...",
    "default_params": {"short": 5, "long": 20, "position_pct": 100},
    "is_running": false,
    "capital": 100000,
    "config": {
      "id": 1,
      "params": {"short": 5, "long": 20},
      "position_pct": 100,
      "time_range": "1y"
    }
  }
]
```

#### POST /api/trading/models/{model_name}/start

启动模型。

**Request** (JSON):
```json
{
  "params": {"short": 5, "long": 20},
  "position_pct": 100,
  "time_range": "1y",
  "stock_list": ["000001.SZ", "000002.SZ"]
}
```

**Response** (JSON):
```json
{"status": "running", "model_name": "ma_cross"}
```

#### POST /api/trading/models/{model_name}/stop

停止模型。

**Response** (JSON):
```json
{"status": "stopped", "model_name": "ma_cross"}
```

#### PUT /api/trading/models/{model_name}/config

更新模型配置（不启动）。

**Request** (JSON):
```json
{
  "params": {"short": 10, "long": 30},
  "position_pct": 50,
  "time_range": "6m"
}
```

**Response** (JSON):
```json
{"status": "ok", "model_name": "ma_cross"}
```

---

### 信号扫描

#### POST /api/trading/models/{model_name}/scan

扫描交易信号。

**Request** (JSON):
```json
{
  "signal_type": "BUY",
  "scope": "watchlist",
  "industry": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| signal_type | string | "BUY" 扫描买入信号 / "SELL" 扫描卖出信号 |
| scope | string | "all" 全量 / "watchlist" 自选股 / "industry" 指定行业 |
| industry | string\|null | scope="industry" 时必填 |

**Response** (HTML): `components/scan_results.html` 渲染的 HTML 片段

**Response** (JSON, `Accept: application/json`):
```json
{
  "model_name": "ma_cross",
  "signal_type": "BUY",
  "results": [
    {
      "stock_code": "000001.SZ",
      "stock_name": "平安银行",
      "signal_price": 12.35,
      "signal_reason": "MA5上穿MA20",
      "trade_date": "2026-05-15"
    }
  ],
  "count": 1
}
```

---

### 信号决策与下单

#### POST /api/trading/signals/{signal_id}/confirm

确认信号并创建订单。

**Request** (JSON, optional — 不传则使用信号默认值):
```json
{
  "quantity": 800
}
```

**Response** (JSON):
```json
{
  "signal_id": 42,
  "order_id": 15,
  "status": "submitted",
  "stock_code": "000001.SZ",
  "order_type": "BUY",
  "price": 12.35,
  "quantity": 800
}
```

下单逻辑：
- **买入**: `quantity = floor(available_cash * position_pct / 100 / signal_price / 100) * 100`（A 股 100 股整数倍）
- **卖出**: `quantity = 该模型该股票的全部持仓数量`
- `price = signal_price`

#### POST /api/trading/signals/{signal_id}/ignore

忽略信号。

**Response** (JSON):
```json
{"status": "ignored", "signal_id": 42}
```

---

### 订单监控

#### GET /api/trading/models/{model_name}/orders

获取某模型的订单列表。

**Response** (HTML): `components/orders.html` 渲染的 HTML 片段

#### POST /api/trading/orders/{order_id}/retry

手动触发撤单重试。

**Response** (JSON):
```json
{
  "order_id": 15,
  "new_order_id": 16,
  "status": "submitted",
  "retry_count": 1
}
```

#### GET /api/trading/orders/monitor

检查所有需监控的订单状态（HTMX 轮询用）。

**Response** (HTML): 更新后的订单状态 HTML 片段

---

### 收益展示

#### GET /api/trading/models/{model_name}/performance

获取模型收益概况。

**Response** (HTML): `components/model_performance.html` 渲染的 HTML 片段

**Response** (JSON):
```json
{
  "model_name": "ma_cross",
  "initial_capital": 100000,
  "available_cash": 85600,
  "market_value": 18900,
  "total_asset": 104500,
  "total_return": 0.045,
  "total_return_pct": 4.5,
  "positions": [
    {
      "stock_code": "000001.SZ",
      "stock_name": "平安银行",
      "quantity": 1500,
      "avg_cost": 12.10,
      "current_price": 12.60,
      "market_value": 18900,
      "profit_loss": 750,
      "profit_loss_pct": 4.13
    }
  ]
}
```
