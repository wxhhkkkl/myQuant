# Implementation Plan: 板块分析模块

**Branch**: `003-sector-analysis` | **Date**: 2026-05-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/003-sector-analysis/spec.md`

## Summary

新增板块分析模块，提供三大功能：(1) 板块概览看板——展示申万一级行业板块的估值分位、行情次数、热度排名；(2) 板块轮动时间线——按月/周展示领涨板块切换轨迹；(3) 板块详情页——板块趋势K线图 + 成分股列表。所有板块指标通过手动触发的预计算任务生成并持久化，页面直接读取缓存结果。

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI, uvicorn, xtquant, DuckDB, SQLite (sqlite3), pandas, HTMX, Alpine.js, ECharts, Tailwind CSS
**Storage**: DuckDB (`market_sim.duckdb`) 存储板块趋势K线（时序）；SQLite (`app.db`) 存储板块快照、热度排名等元数据
**Testing**: pytest + pytest-asyncio
**Target Platform**: Windows 11 (本地Web应用，单用户)
**Project Type**: web-service (backend + frontend)
**Performance Goals**: 概览页首屏 <3s，板块详情页趋势图+成分股 <2s，板块数据全量计算 <30s
**Constraints**: 单用户本地运行，内存 <512MB，手动触发更新（非定时），仅A股沪深两市，仅申万一级行业（31个板块）
**Scale/Scope**: ~5200只A股股票归属31个板块，板块趋势K线日/周/月三个周期，成分股列表按市值排序

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Think Before Coding | ✅ PASS | 本 plan 为完整设计，所有决策点已在 clarify 阶段解决 |
| II. Simplicity First | ✅ PASS | 复用现有技术栈（HTMX + Alpine.js + ECharts + FastAPI），无新增依赖；板块趋势K线预计算存储而非实时聚合 |
| III. TDD (NON-NEGOTIABLE) | ✅ PASS | 核心计算逻辑（行情识别、热度公式、估值分档、趋势合成）均有单元测试覆盖 |
| IV. Focused Changes | ✅ PASS | 按 User Story 优先级分三阶段交付（P1: 概览 → P2: 轮动 → P3: 详情） |
| V. Goal-Driven & Verifiable | ✅ PASS | Spec 定义了 5 条可量化 Success Criteria，每条有明确验收场景 |

## Project Structure

### Documentation (this feature)

```text
specs/003-sector-analysis/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   └── sectors.py              # [NEW] 板块分析所有API端点
│   ├── models/
│   │   └── sector.py               # [NEW] SectorSnapshot 模型（SQLite DDL + upsert）
│   ├── services/
│   │   ├── data_service.py         # [MODIFY] 新增 get_sector_list() 等板块查询
│   │   └── sector_service.py       # [NEW] 板块计算逻辑（行情识别、热度、趋势、估值分档）
│   ├── db/
│   │   └── duckdb_schema.py        # [MODIFY] 新增 sector_trend 表DDL
│   ├── templates/
│   │   ├── base.html               # [MODIFY] 导航栏新增"板块分析"入口
│   │   ├── pages/
│   │   │   ├── sector_analysis.html # [NEW] 板块分析主页面（三Tab：概览/轮动/详情）
│   │   │   └── sector_detail.html  # [NEW] 单个板块详情页（趋势图+成分股）
│   │   └── components/
│   │       ├── sector_table.html   # [NEW] 板块概览表格（HTMX排序刷新）
│   │       ├── sector_rotation.html # [NEW] 板块轮动时间线视图
│   │       ├── sector_trend.html   # [NEW] 板块趋势K线图（ECharts）
│   │       ├── sector_constituents.html # [NEW] 板块成分股表格
│   │       └── sector_update_status.html # [NEW] 板块数据更新状态（进度轮询）
│   ├── scripts/
│   │   └── compute_sectors.py      # [NEW] 板块数据预计算脚本
│   └── main.py                     # [MODIFY] 注册 sectors_router
└── tests/
    ├── unit/
    │   ├── test_sector_service.py  # [NEW] 板块计算逻辑单元测试
    │   └── test_sector_model.py    # [NEW] 模型upsert测试
    └── integration/
        └── test_sectors_api.py     # [NEW] 板块API集成测试
```

**Structure Decision**: 沿用现有 backend 单项目结构。新增文件集中在 3 个领域：API 路由（1个文件）、服务层（1个新文件 + data_service 扩展）、模板（5个组件 + 2个页面）。计算脚本独立为 `compute_sectors.py`，由 API 端点通过后台线程触发，复用已有的 `threading.Thread` + `HX-Trigger` 轮询模式。

## Complexity Tracking

> 无违规项，无需记录。
