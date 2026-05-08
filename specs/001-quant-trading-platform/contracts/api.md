# API Contracts: 量化交易平台

**Base URL**: `http://localhost:8000`
**Content-Type**: `application/json` (data endpoints), `text/html` (page/component endpoints)

## Page Endpoints (HTML via Jinja2)

| Method | Path | Return | Description |
|--------|------|--------|-------------|
| GET | `/` | HTML | 首页/仪表盘 |
| GET | `/stocks` | HTML | AI选股 & 股票列表页 |
| GET | `/stocks/{code}` | HTML | 单只股票详情（基本面+财务+舆情+板块） |
| GET | `/models` | HTML | 量化模型列表（模型选择+参数配置） |
| GET | `/backtest` | HTML | 回测页面（参数设置+结果展示） |
| GET | `/trading` | HTML | 交易页面（信号列表+下单） |
| GET | `/account` | HTML | 账户概览（持仓+收益） |

## Data Endpoints (JSON & HTMX partials)

### 股票数据

| Method | Path | Return | Description |
|--------|------|--------|-------------|
| GET | `/api/stocks/search?q={keyword}` | JSON | 股票代码/名称搜索 |
| GET | `/api/stocks/{code}/kline?start={date}&end={date}` | JSON | 日K线数据 |
| GET | `/api/stocks/{code}/fundamentals` | HTML | 基本面组件 (HTMX) |
| GET | `/api/stocks/{code}/financials` | HTML | 财务报表组件 (HTMX) |
| GET | `/api/stocks/{code}/sentiment` | HTML | 舆情分析组件 (HTMX) |
| GET | `/api/stocks/{code}/sector` | HTML | 板块信息组件 (HTMX) |
| POST | `/api/stocks/ai-picks` | HTML | AI选股推荐列表 (HTMX) |
| POST | `/api/watchlist/add` | JSON | 添加自选股 |
| DELETE | `/api/watchlist/{code}` | JSON | 移除自选股 |
| GET | `/api/watchlist` | JSON | 自选股列表 |

### 量化模型

| Method | Path | Return | Description |
|--------|------|--------|-------------|
| GET | `/api/models` | JSON | 可用模型列表 |
| GET | `/api/models/{name}/params` | JSON | 模型参数配置 |
| PUT | `/api/models/{name}/params` | JSON | 更新模型参数 |
| POST | `/api/models/{name}/run` | JSON | 执行模型计算（实时信号扫描） |

### 回测

| Method | Path | Return | Description |
|--------|------|--------|-------------|
| POST | `/api/backtest/run` | JSON | 执行回测 |
| GET | `/api/backtest/{run_id}` | HTML | 回测结果详情 (HTMX) |
| GET | `/api/backtest/{run_id}/trades` | HTML | 回测交易明细 (HTMX) |
| GET | `/api/backtest/history` | JSON | 历史回测记录列表 |

### 交易

| Method | Path | Return | Description |
|--------|------|--------|-------------|
| GET | `/api/signals` | HTML | 当前交易信号列表 (HTMX) |
| POST | `/api/signals/{id}/confirm` | JSON | 确认执行信号 |
| POST | `/api/signals/{id}/dismiss` | JSON | 忽略信号 |
| POST | `/api/orders` | JSON | 手动下单 |
| GET | `/api/orders` | HTML | 订单列表 (HTMX) |
| DELETE | `/api/orders/{id}` | JSON | 撤单 |

### 账户

| Method | Path | Return | Description |
|--------|------|--------|-------------|
| GET | `/api/account/overview` | HTML | 账户总览组件 (HTMX) |
| GET | `/api/account/positions` | HTML | 持仓列表组件 (HTMX) |
| GET | `/api/account/curve` | JSON | 资产曲线数据 |

---

## Key Request/Response Examples

### POST /api/backtest/run

**Request**:
```json
{
  "model_name": "ma_cross",
  "params": {"short": 5, "long": 20},
  "stock_code": "000001.SZ",
  "start_date": "2025-01-01",
  "end_date": "2025-12-31",
  "initial_capital": 100000
}
```

**Response**:
```json
{
  "run_id": "uuid-xxx",
  "total_return": 0.152,
  "annual_return": 0.148,
  "max_drawdown": -0.082,
  "sharpe_ratio": 1.65,
  "trade_count": 14,
  "win_rate": 0.571
}
```

### POST /api/orders (手动下单)

**Request**:
```json
{
  "stock_code": "000001.SZ",
  "order_type": "BUY",
  "price": 12.50,
  "quantity": 100
}
```

**Response**:
```json
{
  "id": 42,
  "order_id": "QMT-20260503-0001",
  "status": "submitted"
}
```

### GET /api/stocks/{code}/kline

**Response**:
```json
{
  "stock_code": "000001.SZ",
  "stock_name": "平安银行",
  "data": [
    {"date": "2025-01-02", "open": 11.2, "high": 11.5, "low": 11.1, "close": 11.4, "volume": 50000000},
    ...
  ]
}
```
