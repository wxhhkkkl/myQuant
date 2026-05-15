# Data Model: 交易模块模型化执行与监控

**Feature**: 005-trading-model-execution
**Date**: 2026-05-15

## Entity Changes

### strategy_configs (MODIFIED)

新增列：

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| is_running | INTEGER | 0 | 模型是否正在运行（0=停止, 1=运行中） |
| capital | REAL | 100000 | 该模型实例的独立资金池 |

ALTER TABLE 迁移 SQL（`migrate.py` 或 `strategy_config.py` `create_table` 中添加）：
```sql
ALTER TABLE strategy_configs ADD COLUMN is_running INTEGER DEFAULT 0;
ALTER TABLE strategy_configs ADD COLUMN capital REAL DEFAULT 100000;
```

已有字段不变：`id`, `model_name`, `config_name`, `stock_code`, `params` (JSON), `position_pct`, `time_range`, `stock_list` (JSON), `is_active`, `created_at`

### positions (MODIFIED)

新增列 + 唯一约束修改：

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| model_name | VARCHAR(50) | 'default' | 所属模型名称 |

操作步骤（SQLite 不支持直接修改约束，需重建）：
1. 添加 `model_name` 列（DEFAULT 'default'）
2. 后续迁移将所有现有持仓的 model_name 设为 'default'
3. 对于未来写入，UNIQUE 约束改为 `(stock_code, model_name)` 组合

注意：因为 SQLite ALTER TABLE 限制，实际通过 CREATE TABLE IF NOT EXISTS 中调整定义 + ALTER TABLE ADD COLUMN 兼容已有表。

```sql
ALTER TABLE positions ADD COLUMN model_name VARCHAR(50) DEFAULT 'default';
```

### orders (MODIFIED)

新增列：

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| model_name | VARCHAR(50) | '' | 所属模型名称 |
| retry_count | INTEGER | 0 | 撤单重试次数 |
| original_price | REAL | NULL | 原始下单价格（重试时保留） |

```sql
ALTER TABLE orders ADD COLUMN model_name VARCHAR(50) DEFAULT '';
ALTER TABLE orders ADD COLUMN retry_count INTEGER DEFAULT 0;
ALTER TABLE orders ADD COLUMN original_price REAL;
```

### trade_signals (MODIFIED)

新增列：

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| status | VARCHAR(20) | 'pending' | 信号状态: pending/confirmed/ignored/executed |
| stock_name | VARCHAR(50) | '' | 股票名称（扫描时填充，减少展示时 JOIN） |

```sql
ALTER TABLE trade_signals ADD COLUMN status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE trade_signals ADD COLUMN stock_name VARCHAR(50) DEFAULT '';
```

### 已有表（无需变更）

- `quant_models`: 模型注册表保持不变，模型发现通过 `all_active()` 方法
- `watchlist`: 自选股表保持不变
- `stocks`: 股票元数据保持不变
- `daily_kline` (DuckDB): 行情数据保持不变

## 状态机

### 模型实例状态

```
stopped ──[启动]──> running ──[停止]──> stopped
```

启动时：`is_running = 1`，保留已有 `capital` 和持仓
停止时：`is_running = 0`，资金和持仓保留不重置

### 信号状态

```
pending ──[确认交易]──> confirmed ──[下单成功]──> executed
   │
   └──[忽略]──> ignored (从列表移除)
```

### 订单状态

```
submitted ──[超时未成交]──> cancelled ──[重试]──> submitted (新订单, retry_count+1)
    │                          │
    └──[成交]──> filled        └──[超次]──> failed
```

重试规则：
- 超时阈值：60 秒
- 最大重试次数：3
- 价格偏差超过 ±3%：暂停，提示用户手动确认
- `retry_count` 达到 3 后状态变为 `failed`
