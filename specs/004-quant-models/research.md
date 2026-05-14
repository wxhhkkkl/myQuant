# Research: 量化模型模块

## 1. MA Calculation & Signal Detection

**Decision**: Reuse existing `calc_ma()` and `detect_crossover()` in `model_service.py`.

**Rationale**: Functions already implement correct simple moving average (SMA) and golden/death cross detection. Only need to extend from "latest signal only" to "full time range" mode.

**Alternatives considered**:
- Pandas rolling mean: Overkill — existing pure-Python SMA is fast enough for single-stock analysis
- EMA instead of SMA: Spec explicitly says 双均线 (MA), not EMA

## 2. Chart Rendering

**Decision**: Use Alpine.js x-data + ECharts pattern from `sector_trend.html`.

**Rationale**: Same requirements (time range selector, period selector, candlestick + overlay lines, interactive controls). Reuse identical control button styling and state management pattern.

**Chart elements**:
- Candlestick series (OHLC from daily_kline)
- Two line series (MA short, MA long) overlaid
- Scatter series for buy/sell markers (triangles at signal dates)

## 3. Stock Picker

**Decision**: Simple text input with autocomplete or select from existing stock list.

**Rationale**: Existing stock list API (`/api/stocks`) returns all active stocks. Use a `<select>` dropdown or search input. Keep it simple — a `<select>` with stock_code + stock_name is sufficient for v1.

## 4. Performance Statistics

**Decision**: Compute simple long-only performance metrics from signal sequence.

**Rationale**: Spec says "做多胜率（按金叉到死叉区间计算）、累计收益率". Simple metric:
- For each BUY→SELL pair: return = (sell_price - buy_price) / buy_price
- Win rate = pairs with positive return / total pairs
- Cumulative return = sum of all pair returns (not compounded)

**Metrics computed**:
- Total signal count (buy + sell)
- Number of complete trade pairs
- Win rate (%)
- Cumulative return (%)

## 5. Data Persistence

**Decision**: Extend existing `trade_signals` table with `trade_date` column. Store generated signals for backtest/trading use.

**Rationale**: Existing table already supports stock_code, model_name, signal_type, signal_price. Adding trade_date makes signals queryable by date. Use `INSERT OR REPLACE` to avoid duplicate signals on re-generation.

## 6. Model Registration

**Decision**: Auto-register MA Cross model on app startup via `lifespan` event.

**Rationale**: Models are built-in, not user-created. Seed the `quant_models` table on first run with MA Cross defaults: short=5, long=20, position=100%.
