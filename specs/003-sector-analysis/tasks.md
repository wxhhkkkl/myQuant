# Tasks: 板块分析模块

**Input**: Design documents from `specs/003-sector-analysis/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Tests are MANDATORY per project constitution (TDD principle). Every user story must include test tasks written BEFORE implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Minimal scaffolding — project already exists, just ensure feature directory structure is ready

- [x] T001 Verify DuckDB lock is released (no running app holding `market_sim.duckdb`) before starting implementation
- [x] T002 [P] Create empty `backend/src/api/sectors.py` with router skeleton and placeholder `/sector-analysis` page route
- [x] T003 [P] Register sectors router in `backend/src/main.py` via `app.include_router(sectors_router)`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data models, computation engine, and core API infrastructure — ALL user stories depend on this phase

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational

- [x] T004 [P] Unit tests for sector movement detection algorithm in `backend/tests/unit/test_sector_service.py` (test: identify ≥10%/≥5day runs, reject sub-threshold, handle missing data)
- [x] T005 [P] Unit tests for sector valuation level calculation (tertile method) in `backend/tests/unit/test_sector_service.py` (test: 31 sectors split 10/10/11, edge case with equal PE)
- [x] T006 [P] Unit tests for sector heat score formula (0.4×ΔP + 0.3×ΔV + 0.3×up_ratio) in `backend/tests/unit/test_sector_service.py`

### Implementation for Foundational

- [x] T007 [P] Create `backend/src/models/sector.py` — SectorSnapshot model with `create_table()` (sector_name PK, snap_date, pe_median, valuation_level, movement_count_1y, heat_score, heat_rank, change_pct_1w, vol_change_pct, up_ratio, constituent_count, trend_available) and `upsert()` method following existing model patterns
- [x] T008 [P] Add `sector_trend` table DDL to `backend/src/db/duckdb_schema.py` (sector_name VARCHAR, trade_date DATE, open/high/low/close DOUBLE, stock_count INTEGER; PK on sector_name+trade_date)
- [x] T009 Create `backend/src/services/sector_service.py` with core functions:
  - `compute_sector_trend(sector_name)` — equal-weight OHLC aggregation from `daily_kline` JOIN `stocks.industry`
  - `detect_movements(sector_name, days=252)` — scan sector_trend for ≥10%/≥5day runs
  - `calc_valuation_level(pe_median, all_sectors_pe)` — tertile split (前1/3=高估, 中1/3=适中, 后1/3=低估)
  - `calc_heat_score(change_pct_1w, vol_change_pct, up_ratio)` — weighted formula 0.4/0.3/0.3
  - `compute_all_sectors()` — orchestrate full computation: iterate 31 sectors, compute trend → movement → heat → snapshot → upsert
- [x] T010 Create `backend/src/scripts/compute_sectors.py` — CLI script (pattern: `download_all()` + `main()` → `python -m backend.src.scripts.compute_sectors`), calls `sector_service.compute_all_sectors()`, logs progress per sector
- [x] T011 Wire up manual refresh endpoint in `backend/src/api/sectors.py`:
  - `POST /api/sectors/refresh` — spawn `threading.Thread(target=compute_all_sectors, daemon=True)`, return `components/sector_update_status.html` with `HX-Trigger: poll-sector-update`
  - `GET /api/sectors/refresh/status` — return JSON `{running, message, last_updated}`, send `HX-Trigger: sector-update-done` on completion
  - Follow existing `_kline_update_status` pattern in `data_service.py`

**Checkpoint**: Foundation ready — `compute_sectors` script can be run (app stopped) to populate tables; API refresh endpoint works (app running). User story implementation can now begin.

---

## Phase 3: User Story 1 - 板块概览看板 (Priority: P1) 🎯 MVP

**Goal**: 用户打开板块分析页面，看到31个申万一级行业板块列表，包含估值分位、行情次数、热度排名、近一周涨跌幅，支持排序

**Independent Test**: 访问 `/sector-analysis`，页面展示板块列表，每行包含板块名称、估值分位（高估/适中/低估）、近一年行情次数、近一周涨跌幅、当前热度排名。可点击列头切换排序。

### Tests for User Story 1

- [x] T012 [P] [US1] Unit test for `get_sector_list()` query with sort/filter in `backend/tests/unit/test_sector_service.py`
- [x] T013 [P] [US1] Integration test for `GET /api/sectors/list` with sort params in `backend/tests/integration/test_sectors_api.py`

### Implementation for User Story 1

- [x] T014 [US1] Add `get_sector_list(sort_by, sort_order)` to `backend/src/services/data_service.py` — queries `sector_snapshot` JOINed with sort support, returns list of dicts. Falls back gracefully when no snapshot data exists (empty list, not error)
- [x] T015 [US1] Implement `GET /api/sectors/list` endpoint in `backend/src/api/sectors.py` — accepts `sort_by`/`sort_order` query params, returns `components/sector_table.html` HTML fragment (HTMX-compatible)
- [x] T016 [US1] Create `backend/src/templates/components/sector_table.html` — reusable table component with:
  - Column headers with sort links (hx-get on each header toggling sort_by/sort_order)
  - Rows showing: sector_name, valuation_level (color-coded: red=高估, green=低估, gray=适中), movement_count_1y, change_pct_1w (red/green formatting), heat_rank
  - Empty state: "暂无板块数据，请先点击更新板块信息" when no data
  - "数据不足" badge for sectors with trend_available=0
- [x] T017 [US1] Create `backend/src/templates/pages/sector_analysis.html` — main page extending `base.html`:
  - Alpine.js x-data with `activeTab` state (概览/轮动/详情, default 概览)
  - Tab bar with three tabs
  - 概览 tab: includes `sector_table.html`, "更新板块信息" button, last-updated display
  - Placeholder divs for 轮动 and 详情 tabs (filled in US2/US3)
  - "更新板块信息" button: triggers `POST /api/sectors/refresh`, shows progress indicator
- [x] T018 [US1] Add "板块分析" nav link to `backend/src/templates/base.html` — `<a href="/sector-analysis">板块分析</a>` in the `<nav>` bar, between "个股列表" and "量化模型"

**Checkpoint**: 板块概览看板完全可用 — 用户可打开页面看到板块列表，切换排序。若无数据则显示引导提示。

---

## Phase 4: User Story 2 - 板块轮动时间线 (Priority: P2)

**Goal**: 用户在轮动分析视图中选择时间范围和粒度（月/周），看到各时段领涨板块（涨幅前3）及切换轨迹

**Independent Test**: 切换到"轮动分析"Tab，选择"近6个月"+"月视图"，显示每月领涨前3板块。切换为"周视图"可看到周度领涨板块。

### Tests for User Story 2

- [x] T019 [P] [US2] Unit test for `get_rotation_data()` with monthly/weekly granularity in `backend/tests/unit/test_sector_service.py`
- [x] T020 [P] [US2] Integration test for `GET /api/sectors/rotation` with time_range and granularity params in `backend/tests/integration/test_sectors_api.py`

### Implementation for User Story 2

- [x] T021 [US2] Add `get_rotation_data(time_range, granularity)` to `backend/src/services/sector_service.py` — from `sector_trend`, compute each period's top-3 sector by change_pct, return `[{period, top3: [{sector, change_pct}]}]`
- [x] T022 [US2] Implement `GET /api/sectors/rotation` endpoint in `backend/src/api/sectors.py` — returns JSON with periods + leaders array (see contracts/api.md)
- [x] T023 [US2] Create `backend/src/templates/components/sector_rotation.html` — rotation view component:
  - Time range selector (1m/3m/6m/1y) and granularity toggle (月/周)
  - ECharts-based rotation visualization: each period as a column, top-3 sectors as colored blocks with sector name + change_pct. Color intensity reflects change_pct magnitude
  - Click on a period block: HTMX loads period detail below (all sectors ranked for that period)
  - Loading state during data fetch
- [x] T024 [US2] Update `backend/src/templates/pages/sector_analysis.html` — fill 轮动 tab placeholder with `sector_rotation.html` include, add Alpine.js handlers for time range / granularity changes that trigger HTMX data reloads

**Checkpoint**: 轮动时间线可用 — 用户可在概览和轮动之间切换，查看板块轮动历史轨迹。

---

## Phase 5: User Story 3 - 板块详情与成分股 (Priority: P3)

**Goal**: 用户点击板块名称进入详情页，看到板块趋势K线图（支持日/周/月切换）和成分股列表（含代码、名称、最新价、涨跌幅、市盈率、市值），点击成分股跳转个股详情页

**Independent Test**: 在板块概览点击"食品饮料"→ 跳转板块详情页 → 看到趋势K线图 + 成分股表格。切换K线周期图表重新渲染。点击成分股跳转到 `/stocks/{code}`。

### Tests for User Story 3

- [x] T025 [P] [US3] Unit test for `get_sector_trend(sector_name, period, time_range)` in `backend/tests/unit/test_sector_service.py`
- [x] T026 [P] [US3] Unit test for `get_sector_constituents(sector_name)` in `backend/tests/unit/test_sector_service.py`
- [x] T027 [P] [US3] Integration test for `GET /api/sectors/{name}/trend` in `backend/tests/integration/test_sectors_api.py`

### Implementation for User Story 3

- [x] T028 [US3] Add functions to `backend/src/services/sector_service.py`:
  - `get_sector_trend(sector_name, period, time_range)` — query `sector_trend`, aggregate weekly/monthly from daily if needed
  - `get_sector_constituents(sector_name)` — query `stocks` JOIN `stock_fundamentals` (latest snap_date) for sector constituents with latest_price, change_pct, pe_ratio, market_cap. Order by market_cap DESC
- [x] T029 [US3] Implement `GET /api/sectors/{sector_name}/trend` in `backend/src/api/sectors.py` — returns ECharts candlestick format JSON `{sector_name, data: [[date, open, high, low, close], ...], stock_count}`
- [x] T030 [US3] Implement `GET /api/sectors/{sector_name}/constituents` in `backend/src/api/sectors.py` — returns `components/sector_constituents.html` HTML fragment
- [x] T031 [US3] Create `backend/src/templates/components/sector_trend.html` — ECharts candlestick chart component:
  - Fetches data from `/api/sectors/{name}/trend`
  - Period switcher (日线/周线/月线) with hx-get reloading chart data
  - Time range inherits from page-level selector (FR-009)
  - Shows stock_count in chart subtitle
  - Empty state when trend_available=0: "暂无趋势数据"
- [x] T032 [US3] Create `backend/src/templates/components/sector_constituents.html` — constituent stocks table:
  - Columns: 代码 (link to `/stocks/{code}`), 名称, 最新价, 涨跌幅 (red/green), 市盈率, 市值(亿)
  - Reuses styling from existing `stock_table.html` pattern
  - "暂无成分股" empty state
- [x] T033 [US3] Create `backend/src/templates/pages/sector_detail.html` — sector detail page extending `base.html`:
  - Page header: sector_name + constituent_count + valuation_level badge
  - Sector trend K-line chart (include `sector_trend.html`)
  - Constituent stocks table (include `sector_constituents.html`)
  - Back link to `/sector-analysis`
  - Time range selector at top (1m/3m/6m/1y) — applies to both chart and any period-dependent data
- [x] T034 [US3] Update `backend/src/templates/components/sector_table.html` — make each sector name a clickable link to `/sector-analysis/{sector_name}` (URL-encoded)
- [x] T035 [US3] Add page route `GET /sector-analysis/{sector_name}` to `backend/src/api/sectors.py` — returns `pages/sector_detail.html` with context

**Checkpoint**: 完整分析流程 "概览 → 轮动 → 详情 → 个股" 可走通。

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, UX polish, and validation

- [x] T036 [P] Create `backend/src/templates/components/sector_update_status.html` — progress polling component (reuses pattern from `kline_update_status.html`): blue pulsing bar while running, green success message on done with last_updated time, error state for failures. Triggers `sector-update-done` custom event to refresh sector table
- [x] T037 Handle edge cases across all endpoints:
  - Sector with zero constituents → "暂无成分股", trend_available=0
  - Missing PE data → valuation_level shows "--" not "低估"  
  - All sectors bearish (全跌) → heat scores still computed, just all low
  - URL-encoded sector names in routes (e.g., `/sector-analysis/%E9%A3%9F%E5%93%81%E9%A5%AE%E6%96%99`)
- [x] T038 Validate end-to-end flow per quickstart.md: start app → open page → click refresh → see data → sort → view rotation → click sector → see detail → click constituent → go to stock detail
- [x] T039 Run all tests with `pytest backend/tests/ -v` and ensure full pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1 - P1)**: Depends on Phase 2 — No dependencies on US2/US3
- **Phase 4 (US2 - P2)**: Depends on Phase 2 — Uses sector_trend data from Phase 2; may integrate with US1 page but is independently testable via API
- **Phase 5 (US3 - P3)**: Depends on Phase 2 — Uses sector_trend + snapshot data from Phase 2; independently testable
- **Phase 6 (Polish)**: Depends on US1+US2+US3 completion

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — self-contained. Provides the page shell that US2 and US3 extend
- **US2 (P2)**: Can start after Foundational — independently testable via API. Requires US1's page shell to render the tab (T024 depends on T017)
- **US3 (P3)**: Can start after Foundational — independently testable via API. Requires US1's sector_table to link to detail page (T034 depends on T016)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models/Services before endpoints
- Endpoints before templates (templates consume API data)
- Core implementation before integration

### Parallel Opportunities

- **Phase 2**: T004, T005, T006 (all tests) can run in parallel; T007 and T008 (model + DDL) can run in parallel
- **Phase 3**: T012 and T013 (tests) can run in parallel; T014 (service) and T016 (template) can start after T015 (endpoint) since template needs the API
- **Phase 4**: T019 and T020 (tests) in parallel; T023 (rotation component) in parallel with T021 (service logic)
- **Phase 5**: T025, T026, T027 (all tests) in parallel; T031 and T032 (both templates) in parallel
- **Phase 6**: T036 in parallel with T037 edge case handling

---

## Parallel Example: Phase 2 Foundational

```bash
# Launch all 3 test tasks together:
Task: "Unit tests for sector movement detection in backend/tests/unit/test_sector_service.py"
Task: "Unit tests for sector valuation level calculation in backend/tests/unit/test_sector_service.py"
Task: "Unit tests for sector heat score formula in backend/tests/unit/test_sector_service.py"

# Launch model + DDL tasks together (different files):
Task: "Create SectorSnapshot model in backend/src/models/sector.py"
Task: "Add sector_trend table DDL to backend/src/db/duckdb_schema.py"
```

## Parallel Example: Phase 5 User Story 3

```bash
# Launch all 3 test tasks together:
Task: "Unit test for get_sector_trend() in backend/tests/unit/test_sector_service.py"
Task: "Unit test for get_sector_constituents() in backend/tests/unit/test_sector_service.py"
Task: "Integration test for GET /api/sectors/{name}/trend in backend/tests/integration/test_sectors_api.py"

# Launch both template tasks together (different files):
Task: "Create sector_trend.html component"
Task: "Create sector_constituents.html component"
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T011) — **CRITICAL**
3. Complete Phase 3: User Story 1 (T012-T018)
4. **STOP and VALIDATE**: Run `compute_sectors` script, open `/sector-analysis`, verify sector table renders with all columns, test sort
5. Demo MVP

### Incremental Delivery

1. Setup + Foundational → tables created, computation engine ready
2. US1 → 板块概览看板 workable (MVP!)
3. US2 → add rotation tab, verify independently
4. US3 → add detail pages, verify full flow "概览 → 轮动 → 详情 → 个股"
5. Polish → edge cases handled, tests green

### Parallel Team Strategy

With multiple developers:

1. All complete Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 (page shell + sector table)
   - Developer B: US2 (rotation) — starts after US1 page shell exists (T017)
   - Developer C: US3 (detail) — independently testable via API, no page dependency to start
3. Integrate at checkpoints: T024 (US2 tab into page), T034 (US1 links to US3 detail)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests MUST fail before implementation (TDD per constitution)
- Run `python -m backend.src.scripts.compute_sectors` with app stopped to avoid DuckDB lock
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Sector names in URLs must be URL-encoded (Chinese characters)
