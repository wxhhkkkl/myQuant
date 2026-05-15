# Implementation Plan: 交易模块模型化执行与监控

**Branch**: `005-trading-model-execution` | **Date**: 2026-05-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/005-trading-model-execution/spec.md`

## Summary

重构交易页面，从当前的"信号列表+手动下单"模式转变为模型驱动的交易执行与监控系统。核心变更：新增模型实例管理（启动/停止/配置）、手动信号扫描（按范围筛选买入/卖出信号）、从信号一键下单（自动填价填量）、订单执行监控与撤单重试、以及按模型隔离的收益实时展示。

技术方案：复用现有 `MaCrossModel`、`strategy_configs`、`orders`、`positions` 表结构并扩展；数据库迁移添加模型隔离字段；交易 API 扩展扫描、监控、收益端点；前端交易页面全面重写为 Alpine.js 驱动的单页交互。

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI, Jinja2, HTMX 1.9.12, Alpine.js v3, Tailwind CSS, ECharts
**Storage**: SQLite (metadata/config/orders/positions), DuckDB (market data daily_kline)
**Testing**: pytest
**Target Platform**: Windows/Linux server, localhost web app
**Project Type**: web-service (FastAPI backend + server-rendered HTML frontend)
**Performance Goals**: 扫描 500 只标的 ≤5 秒；订单状态刷新 ≤5 秒；收益数据更新 ≤10 秒
**Constraints**: 模拟交易环境（无真实交易所接口）；非交易时段暂停监控；单用户本地运行
**Scale/Scope**: 少量模型（当前 1 个，未来 <10 个）；每模型独立资金池（默认 10 万）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Think Before Coding | PASS | Plan documents architecture decisions, data model, and API contracts before any code |
| II. Simplicity First | PASS | Reuses existing tables (ALTER not recreate), reuses MaCrossModel as-is, no new abstraction layers |
| III. Test-Driven Development | PASS | Phase 2 tasks will include test-first steps for each module |
| IV. Focused Changes | PASS | Each migration/API/template change is scoped to one responsibility |
| V. Goal-Driven & Verifiable Results | PASS | Success criteria from spec are measurable: scan time, click count, order status latency |

**Gate Result**: PASS — all principles satisfied. No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/005-trading-model-execution/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── trading-api.md   # API contracts
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   └── trading.py          # EXPAND: scan, order-from-signal, monitoring, P&L endpoints
│   ├── db/
│   │   └── migrate.py          # MODIFY: add model_name cols, new tables
│   ├── models/
│   │   ├── strategy_config.py  # MODIFY: add is_running, capital columns
│   │   ├── order.py            # MODIFY: add model_name, retry_count, original_price
│   │   ├── position.py         # MODIFY: add model_name to PK/unique
│   │   └── trade_signal.py     # MODIFY: add status, stock_name columns
│   ├── services/
│   │   ├── trade_service.py    # REWRITE: model instance mgmt, scan, monitoring, P&L
│   │   └── account_service.py  # MODIFY: per-model aggregation helpers
│   └── templates/
│       ├── pages/
│       │   └── trading.html    # REWRITE: model-driven full-page layout
│       └── components/
│           ├── model_config_panel.html  # NEW: inline expandable config
│           ├── scan_results.html        # NEW: signal scan result list
│           ├── model_performance.html   # NEW: per-model P&L summary
│           └── signals.html             # MODIFY: add status badges
tests/
└── test_trading.py                   # NEW: trading module tests
```

**Structure Decision**: Web application pattern (Option 2). Backend serves HTML via Jinja2 + HTMX, with Alpine.js for client-side interactivity. No separate frontend SPA — the existing pattern of server-rendered pages with embedded JS components is maintained.

## Complexity Tracking

> No violations — this section is intentionally empty.
