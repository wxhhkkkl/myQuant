# Quickstart: 交易模块模型化执行与监控

**Feature**: 005-trading-model-execution
**Date**: 2026-05-15

## 开发环境

```bash
# 激活虚拟环境
source .venv/Scripts/activate  # Windows
# 或 source .venv/bin/activate  # Linux

# 启动开发服务器
cd backend && python -m uvicorn backend.src.main:app --reload --port 8000
```

## 数据库迁移

启动时自动运行（`main.py` lifespan → `run_migrations()`）。新增字段通过 `ALTER TABLE ADD COLUMN` 在已有表上增量添加，不影响已有数据。

关键迁移：
- `strategy_configs`: +is_running, +capital
- `positions`: +model_name
- `orders`: +model_name, +retry_count, +original_price
- `trade_signals`: +status, +stock_name

## 验证步骤

### 1. 验证模型列表加载

访问 `http://localhost:8000/trading`，应看到：
- 双均线模型卡片，显示名称、描述、状态（未启动）
- 点击卡片展开配置面板（短周期/长周期/仓位比例/时间范围）
- "启动"按钮可点击

### 2. 验证信号扫描

1. 启动双均线模型
2. 选择扫描范围（自选股），点击"扫描买入信号"
3. 验证返回结果包含股票代码、名称、信号价格、信号原因
4. 点击"扫描卖出信号"（需有持仓）

### 3. 验证下单流程

1. 在扫描结果中点击某条买入信号的"确认买入"
2. 验证订单自动创建，显示在订单列表中
3. 验证订单状态变化（submitted → filled）

### 4. 验证收益展示

1. 查看模型收益面板
2. 验证显示累计收益率、持仓市值、可用资金、总资产
3. 验证持仓浮盈随行情更新

### 5. API 测试

```bash
# 列出模型
curl http://localhost:8000/api/trading/models

# 启动模型
curl -X POST http://localhost:8000/api/trading/models/ma_cross/start \
  -H 'Content-Type: application/json' \
  -d '{"params":{"short":5,"long":20},"position_pct":100,"time_range":"1y"}'

# 扫描买入信号（自选股范围）
curl -X POST http://localhost:8000/api/trading/models/ma_cross/scan \
  -H 'Content-Type: application/json' \
  -d '{"signal_type":"BUY","scope":"watchlist"}'

# 查看收益
curl http://localhost:8000/api/trading/models/ma_cross/performance
```

## 关键文件路径

| 文件 | 用途 |
|------|------|
| `backend/src/api/trading.py` | 交易 API 路由 |
| `backend/src/services/trade_service.py` | 交易业务逻辑 |
| `backend/src/models/strategy_config.py` | 模型配置/实例模型 |
| `backend/src/models/order.py` | 订单模型 |
| `backend/src/models/position.py` | 持仓模型 |
| `backend/src/templates/pages/trading.html` | 交易页面模板 |
| `backend/src/templates/components/model_config_panel.html` | 模型配置面板组件 |
| `backend/src/templates/components/scan_results.html` | 扫描结果组件 |
| `backend/src/templates/components/model_performance.html` | 模型收益组件 |
