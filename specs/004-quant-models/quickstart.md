# Quickstart: 量化模型模块

## Prerequisites

- App running (`python -m backend.src.main` or similar)
- K-line data available in DuckDB (`daily_kline` table populated)
- Stock list populated in SQLite (`stocks` table)

## Verification Steps

### 1. Model Library Page

1. Navigate to `/models`
2. Verify: See model cards grid, at minimum the "双均线模型" card
3. Verify: Card shows model name, description, parameter preview

### 2. MA Cross Model Configuration

1. Click "双均线模型" card
2. Verify: Navigate to `/models/ma_cross`
3. Verify: See model logic explanation section
4. Select a stock (e.g., 000001.SZ 平安银行)
5. Set Short MA = 5, Long MA = 20, Position = 100%
6. Select time range = 1年
7. Click "生成信号"

### 3. Signal & Chart Verification

1. Verify: K-line candlestick chart renders
2. Verify: Two MA lines overlaid (short in blue, long in orange)
3. Verify: Buy markers (up arrows) at golden cross points
4. Verify: Sell markers (down arrows) at death cross points
5. Verify: Performance stats show signal count, win rate, cumulative return

### 4. Signal Persistence

1. After generating signals, check trade_signals table:
   ```sql
   SELECT * FROM trade_signals WHERE model_name = 'ma_cross' ORDER BY trade_date;
   ```
2. Verify: Signals stored with correct trade_date, signal_type, signal_price

### 5. API Smoke Test

```bash
# List models
curl http://localhost:8000/api/models

# Generate signals
curl -X POST http://localhost:8000/api/models/ma_cross/signals \
  -H "Content-Type: application/json" \
  -d '{"stock_code":"000001.SZ","short":5,"long":20,"position_pct":100,"time_range":"1y"}'
```
