# Implementation Plan: 量化交易平台 (Quant Trading Platform)

**Branch**: `001-quant-trading-platform` | **Date**: 2026-05-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-quant-trading-platform/spec.md`

## Summary

构建一个个人量化交易平台，覆盖股票研究→策略回测→实盘交易→持仓监控的完整流程。
技术方案：FastAPI 后端 + DuckDB 时序数据存储 + SQLite 元数据存储 + Jinja2/HTMX/Alpine.js/Tailwind CSS 前端。
数据源以 QMT xtdata 为主（K线、财务、板块），akshare 补充估值指标和舆情。

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI, uvicorn, DuckDB, SQLite (sqlite3), xtquant (国金证券QMT SDK), akshare (补充估值+舆情), pandas, numpy, TA-Lib (技术指标), httpx, APScheduler
**Storage**: DuckDB (大规模时序: K线、因子、回测结果), SQLite (元数据与事务: 交易记录、策略参数、日志、自选股列表)
**Testing**: pytest + pytest-asyncio
**Target Platform**: Windows 11 (本地Web应用)
**Project Type**: web-service (backend + frontend)
**Performance Goals**: 回测近一年数据<5秒, 同时监控20只股票信号, 行情数据刷新延迟<5秒
**Constraints**: 单用户本地运行, 内存<512MB, 回测收益偏差<1%, 信号推送延迟<30秒
**Scale/Scope**: A股沪深两市 ~5000只股票, 单用户, 首个版本1个量化模型(双均线)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Think Before Coding | ✅ PASS | 本次 plan 即为思考过程，所有技术选择有明确理由 |
| II. Simplicity First | ✅ PASS | FastAPI + HTMX 无 SPA 复杂度；DuckDB/SQLite 无外部服务依赖 |
| III. TDD (NON-NEGOTIABLE) | ✅ PASS | 技术栈原生支持 pytest；回测精度可通过对比手动计算验证 |
| IV. Focused Changes | ✅ PASS | 按 User Story 分阶段交付，每阶段独立可测 |
| V. Goal-Driven & Verifiable | ✅ PASS | Spec 中定义了9条可量化的 Success Criteria |

## Project Structure

### Documentation (this feature)

```text
specs/001-quant-trading-platform/
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
│   ├── main.py              # FastAPI 入口
│   ├── api/                 # 路由 (pages + api endpoints)
│   ├── services/            # 业务逻辑
│   │   ├── data_service.py          # 数据采集 (xtdata主 + akshare补充)
│   │   ├── model_service.py         # 量化模型引擎
│   │   ├── backtest_service.py      # 回测引擎
│   │   ├── trade_service.py         # 交易执行 (QMT xttrader)
│   │   └── account_service.py       # 账户/持仓管理
│   ├── db/
│   │   ├── sqlite.py        # SQLite 连接
│   │   └── duckdb.py        # DuckDB 连接
│   ├── models/              # ORM models (SQLite)
│   ├── templates/           # Jinja2
│   │   ├── base.html
│   │   ├── pages/           # 页面级模板
│   │   └── components/      # HTMX 局部模板
│   └── scripts/             # 数据初始化
│       ├── init_data.py             # 下载股票列表+行业分类 (xtdata)
│       ├── download_kline.py        # 全量历史K线 (xtdata)
│       ├── download_financials.py   # 财务报表 (xtdata)
│       └── sync_supplement.py       # PE/PB/舆情补充 (akshare)
└── tests/
    ├── unit/
    ├── integration/
    └── contract/

frontend/
└── static/
    ├── css/                 # Tailwind output
    └── js/                  # Alpine.js + ECharts (minimal)
```

**Structure Decision**: Web application (Option 2)。后端计算密集型，前端展示型。Templates 放 backend/ 由 FastAPI 渲染，static 单独挂载。DuckDB/SQLite 进程内运行无外部依赖。

## Complexity Tracking

> No violations. All technology choices align with Constitution principles.
