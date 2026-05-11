# Implementation Plan: 个股列表与详情模块

**Branch**: `002-stock-list` | **Date**: 2026-05-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/002-stock-list/spec.md`

## Summary

为量化交易平台新增个股列表模块，包含完整的分页浏览、排序、搜索筛选、自选股管理，以及个股详情页（K线图+行情信息）和批量更新基础信息功能。该模块是对现有 `/stocks` 页面和 `/stocks/{code}` 详情页的重大增强——现有页面仅有基础搜索和AI选股，缺少列表浏览、K线图表和行情数据展示。

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI, uvicorn, xtquant (QMT SDK), DuckDB, SQLite (sqlite3), pandas, APScheduler
**Storage**: DuckDB (`market.duckdb`) 存储K线时序数据；SQLite (`app.db`) 存储股票基础信息、自选股关系
**Testing**: pytest + pytest-asyncio
**Target Platform**: Windows 11 (本地Web应用，单用户)
**Project Type**: web-service (backend + frontend)
**Performance Goals**: 个股列表首屏 <3s，详情页K线+行情 <3s，5000只股票批量更新 <60s
**Constraints**: 单用户本地运行，内存 <512MB，K线图手动刷新（无自动轮询），仅A股沪深两市
**Scale/Scope**: ~5000只A股股票，列表分页浏览（约50条/页），K线默认近一年（~250个交易日）

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Think Before Coding | ✅ PASS | 本 plan 为思考过程，所有设计决策有明确理由 |
| II. Simplicity First | ✅ PASS | 沿用现有技术栈（HTMX + Alpine.js + ECharts + FastAPI），无新增依赖；周K/月K从日K聚合而非新建表 |
| III. TDD (NON-NEGOTIABLE) | ✅ PASS | 每个 User Story 对应独立测试；pytest 测试列表 API、行情数据、自选股 CRUD |
| IV. Focused Changes | ✅ PASS | 按 User Story 优先级分阶段交付（P1: 列表+详情 → P2: 自选股+更新） |
| V. Goal-Driven & Verifiable | ✅ PASS | Spec 中定义了7条可量化的 Success Criteria |

## Project Structure

### Documentation (this feature)

```text
specs/002-stock-list/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API contracts)
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   ├── stocks.py            # [MODIFY] 新增列表分页/排序API + 详情页行情API
│   │   ├── watchlist.py         # [MODIFY] 新增批量状态查询接口
│   │   └── data.py              # [NEW] 数据更新触发API
│   ├── services/
│   │   ├── data_service.py      # [MODIFY] 新增分页查询、周K/月K聚合、行情快照函数
│   │   └── qmt_connector.py     # [MODIFY] 新增行情快照获取方法
│   ├── models/
│   │   ├── stock.py             # [MODIFY] 新增分页/排序查询方法
│   │   └── watchlist.py         # [NO CHANGE] 已满足需求
│   ├── db/
│   │   ├── sqlite.py            # [NO CHANGE]
│   │   ├── duckdb.py            # [NO CHANGE]
│   │   └── duckdb_schema.py     # [NO CHANGE] 从日K聚合周K/月K，无需新表
│   ├── templates/
│   │   ├── pages/
│   │   │   ├── stocks.html          # [REWRITE] 个股列表（表格+分页+搜索+排序+自选筛选）
│   │   │   └── stock_detail.html    # [REWRITE] 详情页（K线图+行情面板+刷新按钮）
│   │   └── components/
│   │       ├── stock_table.html     # [NEW] 列表表格片段（HTMX局部刷新）
│   │       ├── stock_kline.html     # [NEW] K线图容器（ECharts渲染）
│   │       └── stock_quote.html     # [NEW] 行情数据面板
│   └── scripts/
│       └── init_data.py             # [MODIFY] 已有的下载脚本，前端触发调用
└── tests/
    ├── unit/
    │   ├── test_stock_list.py       # [NEW] 列表查询/排序/分页测试
    │   └── test_watchlist.py        # [NEW] 自选股CRUD测试
    └── integration/
        ├── test_stocks_api.py       # [NEW] 股票API集成测试
        └── test_data_update.py      # [NEW] 数据更新集成测试
```

**Structure Decision**: 沿用现有 backend 单项目结构（Option 2: Web application）。新增文件最小化——优先修改现有文件，仅新增必要的模板组件和测试文件。周K/月K通过 DuckDB 聚合查询实现，不创建新数据表。

## Complexity Tracking

> 无违规项，无需记录。
