# Research: 交易模块模型化执行与监控

**Feature**: 005-trading-model-execution
**Date**: 2026-05-15

## 1. 模型实例隔离方案

**Decision**: 在现有 `strategy_configs` 表添加 `is_running` 和 `capital` 列；在 `positions` 表添加 `model_name` 列并修改 UNIQUE 约束为 `(stock_code, model_name)`。

**Rationale**: 最小化新增表数量。`strategy_configs` 已有 `model_name` 和参数配置，只需添加运行状态和资金字段即可充当模型实例。`positions` 当前是全局表，添加 `model_name` 即可实现模型间持仓隔离，同时保留 UNIQUE 约束防止同模型重复持仓。

**Alternatives considered**:
- 新建 `model_instances` 表：增加 JOIN 复杂度，且与 `strategy_configs` 高度重叠
- JSON 字段存储 per-model 数据：查询和更新不便

## 2. 订单状态与监控

**Decision**: 在 `orders` 表添加 `model_name`、`retry_count`、`original_price` 列。订单监控通过前端定时轮询（HTMX 30s 间隔）配合后端状态检查实现。撤单重试逻辑在后端 API 中实现，前端通过按钮手动触发或定时自动检查。

**Rationale**: 模拟交易环境下没有来自交易所的异步回调，订单状态由内部模拟。HTMX 轮询是最简单的状态同步方案，不引入 WebSocket 复杂度。撤单和重试是同一个 API 调用内的原子操作，保证一致性。

**Alternatives considered**:
- WebSocket 推送：对本地单用户应用过度
- 后台线程持续监控：增加调度复杂度，且非交易时段需暂停

## 3. 信号扫描范围选择

**Decision**: 扫描买入信号时，用户通过下拉选择范围（全量市场/自选股/指定行业）。API 接受 `scope` 参数：
- `all`: 从 DuckDB + SQLite 查询所有有 K 线数据的标的
- `watchlist`: 查询自选股表
- `industry`: 查询指定行业

**Rationale**: Spec 已明确要求三种范围。复用现有的行业分类（`stocks.industry`）和自选股表（`watchlist`），无需新增数据。

**Alternatives considered**: 硬编码范围 → 已由 spec 的 clarification 排除

## 4. 模拟交易环境下的订单执行模拟

**Decision**: 订单提交后直接设为"全部成交"状态（模拟环境假设流动性充足），但提供"模拟延迟"选项：提交后状态为 `submitted`，5 秒后自动变为 `filled`。如果订单在 `submitted` 状态超过 60 秒未成交（手动暂停情况），触发监控逻辑。

**Rationale**: 模拟环境无真实撮合，直接成交是合理简化。但为了验证撤单重试流程（FR-013、FR-014），需要保留状态机路径。

**Alternatives considered**: 完全跳过状态变化 → 无法测试监控和重试逻辑

## 5. 前端架构：Alpine.js vs 纯 HTMX

**Decision**: 交易页面使用 Alpine.js 管理模型列表展开/折叠、扫描范围选择、信号确认/忽略等交互状态。HTMX 负责服务端渲染的信号列表刷新、订单状态轮询、收益面板更新。

**Rationale**: 交易页面需要丰富的客户端交互（同时展开多个面板、下拉选择、即时 UI 反馈），纯 HTMX 难以处理这些。Alpine.js 是项目已使用的技术栈（回测页面已有使用），不引入新学习成本。

**Alternatives considered**:
- 纯 HTMX + 服务端渲染每个状态：网络请求过多，用户体验差
- React/Vue SPA：与项目架构不一致，过度设计

## 6. 非交易时段处理

**Decision**: 前端允许随时操作（查看模型、配置参数、扫描信号），但下单和订单监控在非交易时段自动禁用并提示用户。后端 API 不强制拦截（方便测试），但前端显示提示。

**Rationale**: Spec 的非交易时段约束针对自动监控，手动操作不应受限。信号扫描和查看可以在任何时段进行，只有实际"执行交易"需要在交易时段内。

**Alternatives considered**: 后端完全拦截 → 不便开发测试
