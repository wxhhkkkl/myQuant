# Implementation Plan: 量化模型模块

**Branch**: `004-quant-models` | **Date**: 2026-05-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-quant-models/spec.md`

## Summary

Enhance the existing quant model module from a bare list page into a full-featured model library with model detail pages, interactive MA Cross signal generation with stock/time-range/position controls, K-line chart with MA overlay and buy/sell markers, performance statistics, and signal persistence for downstream backtest/trading modules.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.115+, Jinja2, HTMX 2.0+, Alpine.js 3.x, ECharts 5.5, SQLite, DuckDB, TailwindCSS
**Storage**: SQLite (model metadata, configs, signals), DuckDB (daily_kline for MA computation)
**Testing**: pytest
**Target Platform**: Windows desktop (local single-user web app)
**Project Type**: Web application (SSR + HTMX + Alpine.js SPA-like interactions)
**Performance Goals**: MA signal calculation for 1yr data under 3 seconds
**Constraints**: Single-user, localhost only, no auth required
**Scale/Scope**: <10 built-in models, 1 model implemented now (MA Cross)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Think Before Coding | ✓ PASS | Full spec + plan written before implementation |
| II. Simplicity First | ✓ PASS | Reuses existing QuantModel/StrategyConfig/TradeSignal tables; extends existing MaCrossModel class; no new abstractions |
| III. TDD (NON-NEGOTIABLE) | ✓ PASS | Tests for MA calculation, crossover detection, performance stats before UI implementation |
| IV. Focused Changes | ✓ PASS | Only touches models/ api, services/, templates/ for quant model domain; no unrelated changes |
| V. Goal-Driven & Verifiable | ✓ PASS | Each user story has independent test criteria; signal accuracy verifiable against manual calculation |

## Project Structure

### Documentation (this feature)

```text
specs/004-quant-models/
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
│   ├── models/
│   │   ├── quant_model.py        # EXTEND: add register_defaults(), seed DATA
│   │   ├── strategy_config.py    # EXTEND: add stock_code, position_pct fields
│   │   └── trade_signal.py       # EXTEND: add trade_date, config_id columns
│   ├── services/
│   │   └── model_service.py      # EXTEND: full-range signal gen, perf stats
│   ├── api/
│   │   └── models.py             # EXTEND: detail page, signal gen, MA data endpoints
│   └── templates/
│       ├── pages/
│       │   └── models.html              # REWRITE: model cards grid
│       │   └── model_detail.html        # NEW: model intro + config form + chart + stats
│       └── components/
│           ├── model_signals.html        # NEW: signals table HTMX fragment
│           └── model_performance.html    # NEW: performance stats HTMX fragment
└── tests/
    ├── unit/
    │   └── test_ma_cross.py      # NEW: MA calc, crossover detection, stats
    └── integration/
        └── test_model_api.py     # NEW: API endpoint tests
```

**Structure Decision**: Existing `backend/` single project structure. Extend existing files rather than creating new module directories. Follows the exact pattern of the sector analysis module (api/sectors.py → templates/pages/sector_analysis.html + components/sector_*.html).

## Complexity Tracking

> No violations. All changes follow existing patterns and extend existing tables/classes.
